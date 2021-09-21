#!/bin/bash
# Set up ITER modules environment

# Script boilerplate
export old_bash_state="$(shopt -po; shopt -p)"; [[ -o errexit ]] && old_bash_state="$old_bash_state; set -e"  # Save bash state
[[ "${BASH_SOURCE[0]}" != "${0}" ]] && my_dir=$(dirname ${BASH_SOURCE[0]}) || my_dir=$(dirname $0)  # Determine script dir even when sourcing

common_dir=${my_dir}/../common
. $common_dir/00_common_bash.sh

set -xeuf -o pipefail # Set default script debugging flags

###############
# Script body #
###############

# Set up environment such that module files can be loaded
. /usr/share/Modules/init/sh
module use /work/imas/etc/modulefiles
module use /work/imas/etc/modules/all
module purge

# Load base "should be always there" modules
module load git
