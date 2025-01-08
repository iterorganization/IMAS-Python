#!/bin/bash
# Bamboo CI script to build IDSDef.zip
# Note: this script should be run from the root of the git repository

# Debuggging:
set -e -o pipefail
echo "Loading modules..."

# Set up environment such that module files can be loaded
source /etc/profile.d/modules.sh
module purge
# Modules are supplied as arguments in the CI job:
module load $@

# Debuggging:
echo "Done loading modules"
set -x

# Build the DD zip
python imas/dd_helpers.py
