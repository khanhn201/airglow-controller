#!/usr/bin/env python3
import subprocess
from datetime import datetime, timedelta
from sshtunnel import SSHTunnelForwarder
import MySQLdb as mdb
from config import config
import utilities.time_helper
import os

# Define the processes to monitor with their time windows
# Dictionary with "process name": ("start time", "stop time")
processes_to_monitor = {
    "main_scheduler.py": ("16:00", "06:00", "/usr/bin/python3 /home/airglow/airglow/airglow-controller/main_scheduler.py", "/home/airglow/cron_log.txt"),
    "skyalert-logger.py": (None, None, "/usr/bin/python3 /home/airglow/airglow/skyalert-logger/skyalert-logger.py", "/home/airglow/skyalert_log.txt")
}

site_id = config['site'].lower()

def update_database(process_cmd, status, site_id):
    with SSHTunnelForwarder(
        ('airglowgroup.web.illinois.edu', 22),
        ssh_username='airglowgroup',
        ssh_private_key='/home/airglow/.ssh/id_rsa',
        remote_bind_address=('127.0.0.1', 3306)
    ) as server:
        try:
            con = mdb.connect(host='127.0.0.1', db='airglowgroup_sitestatus', port=server.local_bind_port, read_default_file="/home/airglow/.my2.cnf")
            cursor = con.cursor()
            current_time = datetime.utcnow()
            sql = """
            INSERT INTO process_status (process_name, site_id, status, last_checked) 
            VALUES (%s, %s, %s, %s) 
            ON DUPLICATE KEY UPDATE status = VALUES(status), last_checked = VALUES(last_checked)
            """
            cursor.execute(sql, (process_cmd, site_id, status, current_time))

#            if status == 1:
#                cursor.execute("""UPDATE process_status SET status = %s, last_checked = %s 
#                                  WHERE process_name = %s AND site_id = %s""",
#                               (status, current_time, process_cmd, site_id))
#            else:
#                # Update only status
#                cursor.execute("""UPDATE process_status SET status = %s 
#                                  WHERE process_name = %s AND site_id = %s""",
#                               (status, process_cmd, site_id))
            con.commit()
        except mdb.Error as e:
            print("Error while connecting to MySQL", e)
        finally:
            if con:
                cursor.close()
                con.close()

# Function to check if the current time is within a specific time window
def is_within_time_window(start, end):
    now = datetime.now().time()
    start_time = datetime.strptime(start, "%H:%M").time()
    end_time = datetime.strptime(end, "%H:%M").time()
    
    # If the end time is the next day
    if end_time < start_time:
        return now >= start_time or now <= end_time
    else:
        return start_time <= now <= end_time

# Function to check if a process is running
def is_process_running(process_cmd):
    try:
        subprocess.check_output(["pgrep", "-f", process_cmd])
        return True
    except subprocess.CalledProcessError:
        return False

# Function to start a process in the background.
def start_process(command, log_file):
    """
    Start a process with the given command in the background.

    Args:
        command (str): The command to start the process.
        log_file (str): The file to redirect stdout and stderr.

    Returns:
        None
    """
    try:
        with open(log_file, 'a') as log:
            # Start the process in the background, redirecting stdout and stderr
            subprocess.Popen(command, stdout=log, stderr=log, shell=True, preexec_fn=os.setpgrp)
        print(f"Started process: {command}")
    except Exception as e:
        # Log or print any exceptions that occur while starting the process
        print(f"Failed to start process: {e}")

# Main script logic
for process_cmd, (start_time, stop_time, full_process_cmd, log_file) in processes_to_monitor.items():
    # Check if the process is within its specified time window
    if start_time is None or is_within_time_window(start_time, stop_time):
        status = 1 if is_process_running(process_cmd) else 0
        print(process_cmd, status)
        update_database(process_cmd, status, site_id)

        if status == 0:
            # Try to restart the process
            if process_cmd == 'main_scheduler.py':
                # Check if we are before the sunrise time
                timeHelper = utilities.time_helper.TimeHelper()
                sunrise = timeHelper.getSunrise()
                if datetime.now() > sunrise:
                    # We are after sunrise, so no need to do anything
                    continue

            start_process(full_process_cmd, log_file)