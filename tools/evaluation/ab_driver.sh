#!/usr/bin/env bash
# Run three interleaved control/skill pairs over explicitly prepared, frozen inputs.
set -uo pipefail

if [ "$#" -ne 5 ]; then
  echo "Usage: $0 <runs-dir> <source-repo> <control-case> <skill-case> <provider/model>" >&2
  exit 2
fi

runs=$1
source_repo=$2
control_case=$3
skill_case=$4
model=$5
runner="$(dirname "$0")/run_repository.py"
if [ ! -d "$runs" ] || [ ! -f "$source_repo/skills/bw/SKILL.md" ] || [ ! -d "$control_case" ] || [ ! -d "$skill_case" ]; then
  echo "Expected an existing runs directory, source repository with skills/bw, and both case directories" >&2
  exit 2
fi
for arm in control skill; do
  for i in 01 02 03; do
    if [ ! -f "$runs/ab-$arm-$i/seed.json" ]; then
      echo "Missing prepared run: $runs/ab-$arm-$i/seed.json" >&2
      exit 2
    fi
  done
done

failed=0
for i in 01 02 03; do
  for arm in control skill; do
    if [ "$arm" = control ]; then
      args=(--no-skill --case "$control_case")
    else
      args=(--source "$source_repo" --case "$skill_case")
    fi
    echo "Running ab-$arm-$i"
    if python3 "$runner" --run "$runs/ab-$arm-$i" "${args[@]}" \
      --model "$model" --thinking max --compact-at 400000 --timeout 14400; then
      :
    else
      status=$?
      echo "FAILED ab-$arm-$i (exit $status)" >&2
      failed=$((failed + 1))
    fi
  done
done
if [ "$failed" -gt 0 ]; then
  echo "$failed of six runs failed" >&2
  exit 1
fi
echo "All six runs passed"
