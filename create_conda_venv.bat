@echo off
echo Create or update conda venv
call conda install -m -c conda-forge -y --copy -p venv python=3.12
echo Activating venv
call conda activate .\venv
echo Installing requirements
call pip install -r requirements.txt
call conda deactivate
