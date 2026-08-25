#!/usr/bin/env bash
set -euo pipefail

tests_dir=$(readlink -f $(dirname ${0}))

export PYTHONPATH="${tests_dir}/../filter_plugins"
export MOSK_ANSIBLE_CORE="ansible-core>=2.16,<2.17"

exec uv run --python 3.10 --with pytest --with "${MOSK_ANSIBLE_CORE}" pytest "${tests_dir}/functional" "$@"
