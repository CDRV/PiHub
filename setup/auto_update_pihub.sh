echo "Pull from git"
cd /home/pi/Desktop/PiHub
git checkout create_conda_venv.sh;
if git pull | grep -q 'Already up to date.';
then
   echo "Up to date - do nothing";
else
   echo "Update to new version";
   echo "Stop Pihub Service";
   sudo systemctl stop pihub;
   echo "Re-generate venv via miniconda";
   chmod +x create_conda_venv.sh;
   ./create_conda_venv.sh;
   echo "Restart PiHub Service";
   sudo systemctl start pihub.service;
fi
