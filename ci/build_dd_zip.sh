#!/bin/bash
# Bamboo CI script to build IDSDef.zip
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

# Build the DD zip
rm -rf venv  # Environment should be clean, but remove directory to be sure
python -m venv venv
source venv/bin/activate
pip install gitpython saxonche packaging
python imas/dd_helpers.py
deactivate
