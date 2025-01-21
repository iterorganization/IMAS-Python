#!/bin/bash
# Bamboo CI script to install imas and run all tests
# Note: this script should be run from the root of the git repository

# Debuggging:

echo "Loading modules:" $@
BENCHMARKS_DIR=$(realpath "$PWD/imas_benchmarks")
if [[ "$(uname -n)" == *"bamboo"* ]]; then
    set -e -o pipefail
    # create 
    BENCHMARKS_DIR=$(realpath "/mnt/bamboo_deploy/imas/benchmarks/")
fi

# Set up environment such that module files can be loaded
source /etc/profile.d/modules.sh
module purge
# Modules are supplied as arguments in the CI job:
# IMAS-AL-Python/5.2.1-intel-2023b-DD-3.41.0 Saxon-HE/12.4-Java-21
module load IMAS-AL-Core/5.4.3-intel-2023b Saxon-HE/12.4-Java-21


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
mkdir -p "$BENCHMARKS_DIR/results"
mkdir -p .asv
cp -rf "$BENCHMARKS_DIR/results" .asv/

# Ensure numpy won't do multi-threading
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OMP_NUM_THREADS=1

# Ensure there is a machine configuration
asv machine --yes

# Run ASV for the current commit, develop and main
asv run --skip-existing-successful HEAD^!
asv run --skip-existing-successful develop^!
# asv run --skip-existing-successful main^!

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
cp -rf .asv/{results,html} "$BENCHMARKS_DIR"

