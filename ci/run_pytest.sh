#!/bin/bash
# Bamboo CI script to install imas Python module and run all tests
# Note: this script should be run from the root of the git repository

# Debuggging:
if [[ "$(uname -n)" == *"bamboo"* ]]; then
    set -e -o pipefail
fi
echo "Loading modules:" $@

# Set up environment such that module files can be loaded
source /etc/profile.d/modules.sh
module purge
# Modules are supplied as arguments in the CI job:
if [ -z "$@" ]; then
    module load IMAS-AL-Core Java MDSplus 
else
    module load $@
fi

# Debuggging:
echo "Done loading modules"

# Set up the testing venv
rm -rf venv  # Environment should be clean, but remove directory to be sure
python -m venv venv
source venv/bin/activate

# Install imas and test dependencies
pip install --upgrade pip setuptools wheel
pip install .[h5py,netcdf,test]

# Debugging:
pip freeze

# Run pytest
# Clean artifacts created by pytest
rm -f junit.xml
rm -rf htmlcov

# setups local directory to not to full /tmp directory with pytest temporary files
# mkdir -p ~/tmp
# export PYTEST_DEBUG_TEMPROOT=~/tmp
python -m pytest -n=auto --cov=imas --cov-report=term-missing --cov-report=html --junit-xml=junit.xml


