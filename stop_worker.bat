@echo off
echo Stopping background worker on Windows...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*background_worker.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo Background worker stopped.
