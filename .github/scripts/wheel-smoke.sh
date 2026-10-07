#!/usr/bin/env bash
# Smoke-tests an installed wheel with no repository: init, pass an exercise,
# then check both upgrade paths keep the answer. Shared by ci.yml and verify.yml.
# Usage: wheel-smoke.sh <environment the wheel was installed into> <empty workdir>
set -euo pipefail

env_dir="$1"
work_dir="$2"

# Scripts/qx.exe on Windows.
bin_dir="$env_dir/bin"
[ -d "$bin_dir" ] || bin_dir="$env_dir/Scripts"
qx="$bin_dir/qx"
[ -x "$qx" ] || qx="$qx.exe"

mkdir -p "$work_dir"
cd "$work_dir"

# Before init there is no course, and the message must point at `qx init`.
if "$qx" list; then echo "expected qx list to fail before init"; exit 1; fi

# Captured, not piped: `qx list` exits 2 here and pipefail would fail the step.
said=$("$qx" list 2>&1 || true)
case "$said" in
  *init*) ;;
  *) echo "the pre-init message does not name init: $said"; exit 1 ;;
esac

"$qx" init course
cd course
"$qx" doctor
"$qx" list
cp exercises/01_environment/solution.py exercises/01_environment/exercise.py
"$qx" run 1
cd ..

# Re-running init must not touch an answer.
"$qx" init course
grep -q "__version__" course/exercises/01_environment/exercise.py

# --refresh replaces lesson files, keeps the answer, and backs up edited ones.
printf '\n<!-- edited by the smoke test -->\n' >> course/exercises/01_environment/hints.md
"$qx" init course --refresh
grep -q "__version__" course/exercises/01_environment/exercise.py
test -f course/exercises/01_environment/hints.md.bak
grep -q "edited by the smoke test" course/exercises/01_environment/hints.md.bak

echo "the wheel took a learner from nothing to a passing exercise"
