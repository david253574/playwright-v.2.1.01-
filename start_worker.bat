@echo off
echo Starting background worker on Windows...
start /b python -u background_worker.py > worker.log 2>&1
echo Background worker is running. Log output is being written to worker.log.
