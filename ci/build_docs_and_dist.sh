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

# Create sdist and wheel
pip install --upgrade pip setuptools wheel build
rm -rf dist
python -m build .

# Install imas and documentation dependencies from the just-built wheel
pip install "`readlink -f dist/*.whl`[docs,netcdf]"

# Debugging:
pip freeze

# Enable sphinx options:
# - `-W`: turn warnings into errors
# - `-n`: nit-picky mode, warn about all missing references
# - `--keep-going`: with -W, keep going when getting warnings
export SPHINXOPTS='-W -n --keep-going'

# Run sphinx to create the documentation
make -C docs clean html
