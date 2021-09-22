#!/bin/bash
# Boilerplate scripts and functions needed for other scripts
function get_bash_state () {
    if [ $# -eq 0 ]; then
        old_bash_state=""
    else
        local old_bash_state="${1}"
    fi
    if [ "$old_bash_state" == "" ]; then
      local bash_state="$(shopt -po; shopt -p)"; [[ -o errexit ]] && old_bash_state="$old_bash_state; set -e"  # Save bash state
      echo $bash_state
    else
      echo $old_bash_state
    fi
}

function finish {
  set +x
  [[ "${BASH_SOURCE[0]}" != "${0}" ]] && my_name=${BASH_SOURCE[0]} || my_name=$0
  if [[ "$my_name" == *.sh ]]; then
    echo '[DEBUG] Clearing set and shopt flags using eval "\$one_cmd"'
    # Wrap all set/shopt commands into a single big command
    one_cmd=${old_bash_state//$'\n'/'; '}$'\n'
    # Do not show the huge xtrace of this evail
    eval "$one_cmd"
  fi
}

trap finish EXIT RETURN
