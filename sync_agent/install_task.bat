@echo off
echo Installing Balar Sync as Scheduled Task...
schtasks /create /tn "BalarSync" /tr "python \"%~dp0sync.py\"" /sc minute /mo 15 /ru SYSTEM /f
if %errorlevel% == 0 (
    echo SUCCESS: Scheduled every 15 minutes.
    echo To run now: python sync.py
    echo To remove: schtasks /delete /tn "BalarSync" /f
) else (
    echo FAILED: Run as Administrator.
)
pause
