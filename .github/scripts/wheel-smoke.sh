#!/usr/bin/env bash
# Takes a learner through an installed wheel with no repository in sight: no
# course until `qx init` makes one, then a real exercise passing, then both
# upgrade paths leaving the answer alone.
#
# A file rather than an inline block, because two workflows run it. ci.yml runs
# it on Linux for every push and verify.yml runs it on all three operating
# systems on the 1st, and a copy in each would let the Windows one drift.
#
# Usage: wheel-smoke.sh <environment the wheel was installed into> <empty workdir>
set -euo pipefail

env_dir="$1"
work_dir="$2"

# uv puts console scripts in bin on POSIX and in Scripts on Windows, where they
# also carry an extension.
bin_dir="$env_dir/bin"
[ -d "$bin_dir" ] || bin_dir="$env_dir/Scripts"
qx="$bin_dir/qx"
[ -x "$qx" ] || qx="$qx.exe"

mkdir -p "$work_dir"
cd "$work_dir"

# Before anything is copied there is no course, and the message has to name the
# command that makes one rather than a repository to go and find.
if "$qx" list; then echo "expected qx list to fail before init"; exit 1; fi

# Captured, not piped into grep. `qx list` exits 2 here by design, and under
# pipefail that status is what the whole pipeline reports even though grep found
# what it was looking for. The check passed and the step failed anyway.
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

# Running it again is the upgrade path, and it may not touch an answer.
"$qx" init course
grep -q "__version__" course/exercises/01_environment/exercise.py

# --refresh replaces lesson files and must still leave the answer alone. The
# edited hints file is what gives it something to do, and the .bak beside it is
# the promise that nothing is replaced silently.
printf '\n<!-- edited by the smoke test -->\n' >> course/exercises/01_environment/hints.md
"$qx" init course --refresh
grep -q "__version__" course/exercises/01_environment/exercise.py
test -f course/exercises/01_environment/hints.md.bak
grep -q "edited by the smoke test" course/exercises/01_environment/hints.md.bak

echo "the wheel took a learner from nothing to a passing exercise"
