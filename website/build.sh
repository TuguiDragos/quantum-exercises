#!/usr/bin/env bash
# Builds the website into website/_site from the repository it sits in. It needs the project's environment
# (uv sync --locked --all-extras --dev) and the website's own packages (npm ci --prefix website), and stops at the first
# figure or quoted sentence that no longer holds, so a page that would say something untrue is never written.
set -euo pipefail
web="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(dirname "$web")"
cd "$root"
rm -rf "$web/_build" "$web/_site"
mkdir -p "$web/_build" "$web/_site"
export QX_OFFLINE=1 NO_COLOR=1 TERM=dumb COLUMNS=100

uv run --no-sync pytest --collect-only -q -p no:cacheprovider > "$web/_build/collect.txt"

# What qx prints in a fresh course, as a learner meets it: exercise 11 before the fix (NOT YET exits 1) and after it,
# then an exercise that does not exist, which is what the 404 page shows. qx init will not copy the course into a
# folder inside it, so the copy goes to a temporary directory.
qx() { uv run --project "$root" --no-sync qx "$@"; }
course="$(mktemp -d)"
trap 'rm -rf "$course"' EXIT
qx init "$course/quantum-exercises" > /dev/null
cd "$course/quantum-exercises"
status=0
qx run 11 > "$web/_build/bell-fail.txt" || status=$?
[ "$status" -eq 1 ] || { echo "qx run 11 on the starting file exited $status, not 1" >&2; exit 1; }
cp exercises/11_bell_entanglement/solution.py exercises/11_bell_entanglement/exercise.py
qx run 11 > "$web/_build/bell-pass.txt"
status=0
qx run 404 > "$web/_build/missing.txt" || status=$?
echo "exit $status" >> "$web/_build/missing.txt"
cd "$root"

cp -R "$web/static/." "$web/_site/"
uv run --no-sync python "$web/scripts/build_site.py"
uv run --no-sync python "$web/scripts/make_404.py"
uv run --no-sync python "$web/scripts/make_extras.py"
echo "built $web/_site"
