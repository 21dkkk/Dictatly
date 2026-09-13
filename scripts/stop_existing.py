import os
import subprocess

current_pid = os.getpid()
ps_script = f"""
Get-CimInstance Win32_Process | Where-Object {{
    ($_.CommandLine -like '*main.py*' -or $_.CommandLine -like '*src.app*') -and $_.ProcessId -ne {current_pid}
}} | ForEach-Object {{
    Stop-Process -Id $_.ProcessId -Force
}}
"""
subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True)
