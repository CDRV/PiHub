echo "Create or update conda venv"
conda install -m -c conda-forge -y --copy -p $PWD/venv python=3.10
echo "Activating venv"
conda activate $PWD/venv
echo "Installing requirements (make sure git submodules are installed)..."
$PWD/venv/bin/pip install -r $PWD/requirements.txt
conda deactivate
