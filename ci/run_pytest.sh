#!/bin/bash
# Bamboo CI script to install imas and run all tests
# Note: this script should be run from the root of the git repository

# Debuggging:
set -e -o pipefail
echo "Loading modules:" $@

# Set up environment such that module files can be loaded
source /etc/profile.d/modules.sh
module purge
# Modules are supplied as arguments in the CI job:
module load $@

# Debuggging:
echo "Done loading modules"
set -x


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

python -m pytest -n=auto --cov=imas --cov-report=term-missing --cov-report=html --junit-xml=junit.xml
