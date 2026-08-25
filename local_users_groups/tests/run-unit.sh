#!/usr/bin/env bash
set -euo pipefail

tests_dir=$(readlink -f $(dirname ${0}))

export PYTHONPATH="${tests_dir}/../filter_plugins" 

exec uv run --with pytest pytest "${tests_dir}/unit" "$@"
