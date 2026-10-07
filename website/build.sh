#!/usr/bin/env bash
# Builds website/_site. Needs `uv sync --locked --all-extras --dev` and `npm ci --prefix website`.
# Fails if any figure or quote the page uses no longer holds.
set -euo pipefail
web="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(dirname "$web")"
cd "$root"
rm -rf "$web/_build" "$web/_site"
mkdir -p "$web/_build" "$web/_site"
export QX_OFFLINE=1 NO_COLOR=1 TERM=dumb COLUMNS=100

uv run --no-sync pytest --collect-only -q -p no:cacheprovider > "$web/_build/collect.txt"

# Real qx output for the page: exercise 11 failing then passing, and a missing exercise for the 404 page.
# qx init refuses a target inside the course, hence the temporary directory.
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
