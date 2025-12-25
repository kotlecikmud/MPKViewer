@echo off

REM Check python version
python --version

REM Pull latest updates from Git
git pull

REM Install/upgrade pip
python -m pip install --upgrade pip

REM Upgrade all packages listed in requirements.txt
pip install --upgrade -r requirements.txt

pause