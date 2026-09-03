@echo off
REM ============================================================================
REM eTala Automated Smart-Sync Backup Script for Windows Task Scheduler
REM Municipal Engineering Office of Carigara, Leyte
REM ============================================================================

cd /d "%~dp0\.."

REM Activate virtualenv if present, otherwise use system python
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

python manage.py auto_backup --days 14 >> "%~dp0..\backups\auto_backup.log" 2>&1
