#!/bin/bash
# Bamboo CI script for linting
# Note: this script should be run from the root of the git repository

# Debuggging:
if [[ "$(uname -n)" == *"bamboo"* ]]; then
    set -e -o pipefail
fi
echo "Loading modules..."

# Set up environment such that module files can be loaded
source /etc/profile.d/modules.sh
module purge
# Modules are supplied as arguments in the CI job:
if [ -z "$@" ]; then
    module load Python
else
    module load $@
fi

# Debuggging:
echo "Done loading modules"

# Create a venv
rm -rf venv
python -m venv venv
. venv/bin/activate

# Install and run linters
pip install --upgrade 'black >=24,<25' flake8

black --check imas
flake8 imas

deactivate