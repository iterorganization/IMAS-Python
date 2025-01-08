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

# Export current PYTHONPATH so ASV benchmarks can import imas
export ASV_PYTHONPATH="$PYTHONPATH"

# Set up the testing venv
rm -rf venv  # Environment should be clean, but remove directory to be sure
python -m venv venv
source venv/bin/activate

# Install asv and imas
pip install --upgrade pip setuptools wheel
pip install virtualenv .[test]

# Generate MDS+ models cache
python -c 'import imas.backends.imas_core.mdsplus_model; print(imas.backends.imas_core.mdsplus_model.mdsplus_model_dir(imas.IDSFactory()))'

# Copy previous results (if any)
mkdir -p /mnt/bamboo_deploy/imas/benchmarks/results
mkdir -p .asv
cp -rf /mnt/bamboo_deploy/imas/benchmarks/results .asv/

# Ensure numpy won't do multi-threading
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OMP_NUM_THREADS=1

# Ensure there is a machine configuration
asv machine --yes

# Run ASV for the current commit, develop and main
asv run --skip-existing-successful HEAD^!
asv run --skip-existing-successful develop^!
asv run --skip-existing-successful main^!

# Compare results
if [ `git rev-parse --abbrev-ref HEAD` == develop ]
then
    asv compare main develop --machine $(hostname) || echo "asv compare failed"
else
    asv compare develop HEAD --machine $(hostname) || echo "asv compare failed"
fi

# Publish results
asv publish

# And persistently store them
cp -rf .asv/{results,html} /mnt/bamboo_deploy/imas/benchmarks/

