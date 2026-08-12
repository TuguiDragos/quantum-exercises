"""Project metadata that is easy to update in one place and forget in another."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote

import pytest

import quantum_exercises

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised only on 3.10
    import tomli as tomllib


@pytest.fixture(scope="module")
def pyproject(root: Path) -> dict:
    with (root / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


@pytest.fixture(scope="module")
def ignored(root: Path) -> set[str]:
    """Every pattern .gitignore carries, comments and blank lines dropped."""
    return {
        line.strip()
        for line in (root / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


def test_version_agrees_across_every_file(pyproject: dict, root: Path) -> None:
    """Four files carry the version. They drift the moment one is forgotten."""
    declared = pyproject["project"]["version"]

    assert quantum_exercises.__version__ == declared, (
        "src/quantum_exercises/__init__.py disagrees with pyproject.toml"
    )

    citation = (root / "CITATION.cff").read_text(encoding="utf-8")
    match = re.search(r"^version:\s*(\S+)\s*$", citation, re.MULTILINE)
    assert match is not None, "CITATION.cff has no version field"
    assert match.group(1) == declared, "CITATION.cff disagrees with pyproject.toml"


def test_the_lockfile_carries_the_current_version(pyproject: dict, root: Path) -> None:
    """The fourth place, and the one that fails in CI rather than in review.

    uv.lock records this project as a package like any other. Bump the version
    without running `uv lock` and every job that runs `uv sync --locked` refuses to
    start, which is a red build for a reason nothing in the diff points at.
    """
    declared = pyproject["project"]["version"]
    with (root / "uv.lock").open("rb") as handle:
        locked = tomllib.load(handle)

    entry = next(
        (package for package in locked["package"] if package["name"] == "quantum-exercises"), None
    )
    assert entry is not None, "uv.lock has no entry for quantum-exercises"
    assert entry["version"] == declared, (
        f"uv.lock says {entry['version']}, pyproject.toml says {declared}. Run `uv lock`."
    )


class TestTheWheelCarriesTheCourse:
    """`pip install` has to hand over something to run, or `qx init` has nothing.

    Checked against the build configuration rather than by building, which keeps
    it to milliseconds. The CI `wheel` job builds one for real and takes a learner
    through it.
    """

    @staticmethod
    def _force_include(pyproject: dict) -> dict:
        return pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]

    def test_the_exercises_and_the_notebooks_are_included(self, pyproject: dict) -> None:
        included = self._force_include(pyproject)
        assert "exercises" in included, "a wheel without the exercises is a tool with no course"
        assert "notebooks" in included

    def test_they_land_where_the_root_search_cannot_reach(self, pyproject: dict) -> None:
        """Under the package, not beside it.

        find_project_root walks up looking for `<ancestor>/exercises`, so a course
        nested this deep is invisible to it. Move it up one level and an installed
        copy becomes a candidate working directory, which means `qx run` checking
        answers inside site-packages and `qx reset` trying to write there.
        """
        from quantum_exercises.registry import BUNDLED_COURSE

        expected = f"quantum_exercises/{BUNDLED_COURSE.name}"
        for source, destination in self._force_include(pyproject).items():
            assert destination.startswith(f"{expected}/"), (
                f"{source} is packaged at {destination}, outside {expected}"
            )

    def test_the_screenshots_stay_out(self, pyproject: dict) -> None:
        """Seven megabytes of PNGs that no learner opens."""
        assert "readme-assets" not in self._force_include(pyproject)

    def test_bytecode_is_excluded(self, pyproject: dict) -> None:
        """Importing a check.py in process leaves __pycache__ in the source tree."""
        excluded = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["exclude"]
        assert any("__pycache__" in pattern for pattern in excluded)
        assert any(pattern.endswith("*.pyc") for pattern in excluded)


class TestNothingPrivateIsTracked:
    """A learner's own files sit in the repository and none of them belong in git.

    state.py opens with "never committed" and cli.py writes `.bak` copies beside
    lesson files. Both are true only for as long as .gitignore says so, and a
    missing line there would be noticed by nobody until a progress file, or a
    backup carrying someone's answer, arrived in a pull request.
    """

    def test_the_progress_file_and_its_neighbours_are_ignored(self, ignored: set[str]) -> None:
        from quantum_exercises.state import LOCK_FILENAME, STATE_FILENAME, UNREADABLE_SUFFIX

        assert STATE_FILENAME in ignored
        assert STATE_FILENAME + UNREADABLE_SUFFIX in ignored
        assert LOCK_FILENAME in ignored

    def test_the_backups_refresh_leaves_behind_are_ignored(self, ignored: set[str]) -> None:
        from quantum_exercises.cli import BACKUP_SUFFIX

        assert f"*{BACKUP_SUFFIX}" in ignored, (
            f"`qx init --refresh` writes *{BACKUP_SUFFIX} files into the course, "
            "and in a clone the course is the repository"
        )

    def test_none_of_them_are_tracked_right_now(self, root: Path) -> None:
        """The rule above, checked against what git is actually carrying."""
        import subprocess

        from quantum_exercises.cli import BACKUP_SUFFIX
        from quantum_exercises.state import STATE_FILENAME

        try:
            listed = subprocess.run(  # noqa: S603 - fixed argv, no shell
                ["git", "-C", str(root), "ls-files"],
                capture_output=True,
                text=True,
                check=False,
            )
        except (FileNotFoundError, OSError):  # pragma: no cover - git-less environment
            pytest.skip("git is not available")
        if listed.returncode != 0:  # pragma: no cover - only outside a checkout
            pytest.skip("not a git checkout")

        stray = [
            name
            for name in listed.stdout.splitlines()
            if name.endswith(BACKUP_SUFFIX) or Path(name).name.startswith(STATE_FILENAME)
        ]
        assert not stray, f"these belong to whoever is taking the course: {stray}"


class TestTheSdistCarriesTheRepository:
    """A source archive, minus the one part of the repository nothing reads from it."""

    @staticmethod
    def _excluded(pyproject: dict) -> list[str]:
        return pyproject["tool"]["hatch"]["build"]["targets"]["sdist"]["exclude"]

    def test_the_screenshots_stay_out(self, pyproject: dict) -> None:
        """Seven megabytes of the archive. No build step reads them, and the README
        PyPI renders loads them over https rather than out of the file."""
        assert "readme-assets" in self._excluded(pyproject)

    def test_nothing_a_build_needs_is_excluded(self, pyproject: dict) -> None:
        """The sdist has to still build a wheel, which is the whole point of one."""
        needed = {"src", "exercises", "notebooks", "pyproject.toml", "README.md", "LICENSE"}
        for pattern in self._excluded(pyproject):
            assert pattern not in needed, f"{pattern} is needed to build from the sdist"

    def test_bytecode_is_excluded(self, pyproject: dict) -> None:
        excluded = self._excluded(pyproject)
        assert any("__pycache__" in pattern for pattern in excluded)
        assert any(pattern.endswith("*.pyc") for pattern in excluded)


def test_entry_point_is_importable(pyproject: dict) -> None:
    """`qx` must resolve to something callable, or the console script is dead."""
    target = pyproject["project"]["scripts"]["qx"]
    module_name, _, attribute = target.partition(":")

    module = __import__(module_name, fromlist=[attribute])
    assert callable(getattr(module, attribute))


def test_python_floor_matches_the_pinned_interpreter(pyproject: dict, root: Path) -> None:
    """.python-version must satisfy requires-python, or `uv sync` picks a bad one."""
    requires = pyproject["project"]["requires-python"]
    pinned = (root / ".python-version").read_text(encoding="utf-8").strip()

    floor = tuple(int(part) for part in requires.removeprefix(">=").split("."))
    chosen = tuple(int(part) for part in pinned.split(".")[:2])
    assert chosen >= floor, f".python-version is {pinned}, below requires-python {requires}"


# The interpreter the dependency table is written against.
DOCUMENTED_INTERPRETER = "3.13"


def _inventory_rows(text: str) -> dict[str, tuple[str, str]]:
    """Parse the dependency tables: name -> (declared range, resolved version)."""
    rows = re.findall(r"^\| \[([a-z0-9-]+)\]\([^)]+\)[^|]*\| `([^`]+)` \| ([^|]+)\|", text, re.M)
    return {name: (rng.strip(), resolved.strip()) for name, rng, resolved in rows}


def _declared_dependencies(pyproject: dict) -> dict[str, str]:
    """Every declared dependency: name -> the version range, extras stripped."""
    declared: dict[str, str] = {}
    specs = pyproject["project"]["dependencies"] + pyproject["dependency-groups"]["dev"]
    for spec in specs:
        name = re.split(r"[\[><=;]", spec)[0].strip()
        tail = spec.split(name, 1)[1].split(";")[0]
        declared[name] = tail.replace("[visualization]", "").strip()
    return declared


@pytest.fixture(scope="module")
def inventory(root: Path) -> str:
    return (root / "CONTRIBUTING.md").read_text(encoding="utf-8")


def _is_badge(url: str) -> bool:
    """The two hosts badges come from: shields, and GitHub's own workflow badges."""
    return url.startswith("https://img.shields.io/") or url.endswith("/badge.svg")


@pytest.fixture(scope="module")
def badges(root: Path) -> dict[str, str]:
    """Every badge in the README: label -> URL.

    Both spellings are read. The badge row is centred, and GitHub does not render
    markdown inside an HTML block, so centring it meant writing the badges as
    `<img>`. The markdown form is still matched, because nothing forces the whole
    row to convert at once and a half-converted row is exactly what would slip
    through. The row moving to HTML once already emptied this dict of all nine
    badges at a stroke.

    An HTML badge is labelled by the first word of its alt text, so the alt can
    stay useful to a screen reader, "qiskit 2.5.1", while the assertions below
    still look it up as "qiskit". Only the two badge hosts count. Being on https
    used to be enough to tell a badge from a screenshot, because the screenshots
    were relative paths. They became absolute so PyPI could render them, and the
    hero image immediately arrived here labelled "quantum-exercises:".
    """
    readme = (root / "README.md").read_text(encoding="utf-8")

    found = dict(re.findall(r"^\[!\[([a-z-]+)\]\((https://[^)]+)\)\]", readme, re.M))

    for tag in re.findall(r"<img\b[^>]*>", readme):
        alt = re.search(r'\balt="([^"]*)"', tag)
        src = re.search(r'\bsrc="(https://[^"]+)"', tag)
        if alt is None or src is None:
            continue
        if not _is_badge(src.group(1)):
            continue
        words = alt.group(1).split()
        if words:
            found.setdefault(words[0], src.group(1))

    return found


def _ci_matrix(root: Path) -> set[str]:
    workflow = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    block = re.search(r"python-version: \[([^\]]+)\]", workflow).group(1)
    return set(re.findall(r"\d+\.\d+", block))


class TestDependencyInventory:
    """CONTRIBUTING lists every dependency. Lists drift; this stops that silently."""

    def test_every_declared_dependency_is_documented(self, pyproject: dict, inventory: str) -> None:
        documented = _inventory_rows(inventory)
        for name in _declared_dependencies(pyproject):
            assert name in documented, f"{name} is declared but missing from CONTRIBUTING.md"

    def test_no_invented_dependencies(self, pyproject: dict, inventory: str) -> None:
        declared = _declared_dependencies(pyproject)
        for name in _inventory_rows(inventory):
            assert name in declared, f"CONTRIBUTING.md lists {name}, which is not a dependency"

    def test_documented_ranges_match_pyproject(self, pyproject: dict, inventory: str) -> None:
        declared = _declared_dependencies(pyproject)
        for name, (documented, _) in _inventory_rows(inventory).items():
            assert documented == declared[name], (
                f"{name}: CONTRIBUTING says {documented!r}, pyproject says {declared[name]!r}"
            )

    def test_documented_versions_are_the_installed_ones(self, inventory: str) -> None:
        """Resolution is per-interpreter, so this only holds on the documented one.

        numpy and scipy resolve lower on 3.10, because their newer releases have
        dropped it. Asserting a single universal version was wrong and broke CI.
        """
        from importlib.metadata import PackageNotFoundError
        from importlib.metadata import version as installed_version

        running = f"{sys.version_info.major}.{sys.version_info.minor}"
        if running != DOCUMENTED_INTERPRETER:
            pytest.skip(f"the table documents {DOCUMENTED_INTERPRETER}; this is {running}")

        for name, (_, claimed) in _inventory_rows(inventory).items():
            if not re.fullmatch(r"\d+\.\d+\.\d+", claimed):
                continue  # a note such as "only on 3.10" rather than a version
            try:
                actual = installed_version(name)
            except PackageNotFoundError:  # pragma: no cover - would mean a broken env
                pytest.fail(f"CONTRIBUTING claims {name} {claimed}, but it is not installed")
            assert actual == claimed, f"{name}: documented {claimed}, installed {actual}"

    def test_locked_package_counts_are_accurate(self, root: Path, inventory: str) -> None:
        """Three different numbers, and the prose used to give one of them a wrong name.

        uv.lock holds one entry per resolution, so entries outnumber packages, and
        both outnumber what any single environment installs.
        """
        from importlib.metadata import distributions

        with (root / "uv.lock").open("rb") as handle:
            locked = tomllib.load(handle)

        entries = int(re.search(r"records (\d+) package entries", inventory).group(1))
        distinct = int(re.search(r"names (\d+)\s+distinct packages", inventory).group(1))
        installed = int(re.search(r"ends up with (\d+) installed", inventory).group(1))

        assert entries == len(locked["package"])
        assert distinct == len({entry["name"] for entry in locked["package"]})

        running = f"{sys.version_info.major}.{sys.version_info.minor}"
        if running != DOCUMENTED_INTERPRETER:
            pytest.skip(f"the count is for {DOCUMENTED_INTERPRETER}; this is {running}")
        # Only the first two counts are properties of the lockfile. The third is a
        # property of a machine: ipykernel pulls appnope on macOS and nowhere else,
        # so a mac installs exactly one distribution more than Linux does. The
        # documented figure is the Linux one, because that is what CI can hold to,
        # and asserting it on a mac was checking a number the prose never claimed.
        # It passed for months only because it was written on the machine it
        # described.
        if sys.platform != "linux":
            pytest.skip(f"the count is for Linux; this is {sys.platform}")

        # Counted against the lock rather than against everything importable. The
        # coverage job runs the suite under `uv run --with coverage`, which puts a
        # package in the environment that `uv sync` never installs, and a bare
        # count read that as the documented figure being wrong. Anything not in
        # uv.lock was injected for the run, so it is not part of what is claimed.
        def canonical(name: str) -> str:
            return re.sub(r"[-_.]+", "-", name).lower()

        locked_names = {canonical(entry["name"]) for entry in locked["package"]}
        from_lock = [
            dist
            for dist in distributions()
            if canonical(dist.metadata["Name"] or "") in locked_names
        ]
        assert installed == len(from_lock)

    def test_ci_matrix_matches_the_prose(self, root: Path, inventory: str) -> None:
        stated = set(
            re.findall(
                r"\d+\.\d+", re.search(r"CI runs the suite on\s+([^;]+);", inventory).group(1)
            )
        )
        assert stated == _ci_matrix(root)

    def test_default_interpreter_matches_the_prose(self, root: Path, inventory: str) -> None:
        pinned = (root / ".python-version").read_text(encoding="utf-8").strip()
        assert f"installs {pinned} by default" in inventory


class TestReadmeBadges:
    """Static badges state versions. A badge that lies is worse than no badge."""

    def test_the_expected_badges_are_present(self, badges: dict[str, str]) -> None:
        expected = {
            "ci",
            "verify",
            "verified against qiskit".replace(" ", "-"),
            "python",
            "qiskit",
            "qiskit-ibm-runtime",
            "qiskit-aer",
            "uv",
            "ruff",
            "license",
            "downloads",
        } - {"verified-against-qiskit"}  # that one has spaces in its label
        missing = expected - set(badges)
        assert not missing, f"README is missing badges: {sorted(missing)}"

    def test_python_badge_matches_the_ci_matrix(self, root: Path, badges: dict[str, str]) -> None:
        # Decode first: the raw URL separates versions with %20%7C%20, and a naive
        # match reads the "20" of a separator as part of the next version.
        label = unquote(badges["python"]).split("badge/python-")[1].split("-")[0]
        shown = set(re.findall(r"\d+\.\d+", label))
        assert shown == _ci_matrix(root), f"badge {sorted(shown)}, CI {sorted(_ci_matrix(root))}"

    # Verified to resolve identically on 3.10 and 3.13, unlike numpy and scipy,
    # so these badges can state one number for the whole matrix.
    @pytest.mark.parametrize("package", ["qiskit", "qiskit-ibm-runtime", "qiskit-aer"])
    def test_version_badges_match_the_installed_version(
        self, package: str, badges: dict[str, str]
    ) -> None:
        from importlib.metadata import version as installed_version

        shown = re.search(r"-(\d+\.\d+\.\d+)-", badges[package]).group(1)
        assert shown == installed_version(package), (
            f"{package}: badge says {shown}, installed is {installed_version(package)}"
        )

    def test_every_badge_url_is_https_and_complete(self, badges: dict[str, str]) -> None:
        for label, url in badges.items():
            assert url.startswith("https://"), f"{label} badge is not https"
            assert " " not in url, f"{label} badge URL contains a raw space"


# A key-shaped string: 44 generic characters, the shape IBM actually issues.
SAMPLE_KEY = "b3Kq9ZmX7pLwR2tYvN8cJ4hG6sD1fA5eQ0uIAAAAAAAA"


@pytest.fixture(scope="module")
def secret_rule(root: Path) -> dict:
    with (root / ".gitleaks.toml").open("rb") as handle:
        config = tomllib.load(handle)
    for entry in config["rules"]:
        if entry["id"] == "ibm-quantum-api-key":
            return entry
    pytest.fail("the ibm-quantum-api-key rule is gone from .gitleaks.toml")


def _caught(rule: dict, blob: str) -> bool:
    found = re.search(rule["regex"], blob)
    if found is None:
        return False
    return not any(re.search(pattern, found.group()) for pattern in rule["allowlist"]["regexes"])


class TestSecretScanning:
    """The custom gitleaks rule, exercised rather than assumed.

    gitleaks itself runs in CI and in pre-commit; this checks the pattern the
    config actually carries, so a well-meant edit cannot quietly stop it matching.
    Python's `re` and Go's RE2 agree on every construct used here, and each case
    below was confirmed against the pinned gitleaks 8.30.1 binary.
    """

    def test_a_key_in_a_python_file_is_caught(self, secret_rule: dict) -> None:
        assert _caught(secret_rule, f'QiskitRuntimeService(token="{SAMPLE_KEY}")')

    def test_a_key_in_a_notebook_cell_is_caught(self, secret_rule: dict) -> None:
        """A .ipynb stores cell source as JSON, so the quotes arrive backslashed.

        README sends readers to notebooks/playground.ipynb to experiment, which
        makes it the likeliest place in this repository for a key to be pasted.
        The rule was anchored to a bare quote and missed this case entirely.
        """
        source = f'QiskitRuntimeService(token="{SAMPLE_KEY}")\n'
        notebook = json.dumps({"cells": [{"cell_type": "code", "source": [source]}]})
        assert '\\"' in notebook, "fixture is wrong: the quotes should be escaped"
        assert _caught(secret_rule, notebook)

    @pytest.mark.parametrize("placeholder", ["x" * 44, "a" * 44, "<your-api-key-goes-right-here>"])
    def test_documentation_placeholders_do_not_trip_it(
        self, secret_rule: dict, placeholder: str
    ) -> None:
        assert not _caught(secret_rule, f'token="{placeholder}"')


# README.md carries a block of blog links that .github/workflows/rotate-notes.yml
# rewrites from an RSS feed twice a month. Those titles are not written here, they
# arrive from outside, and the two scanners below look for a bare string anywhere
# in a file. A post titled around `uv run qx` would fail both of them.
#
# That failure would also be invisible until it hurt someone else: the rotation
# commit is pushed with GITHUB_TOKEN, and a GITHUB_TOKEN push creates no workflow
# run, so CI never sees it. The README would sit poisoned until the next real pull
# request, which would then go red for a reason having nothing to do with it.
#
# Blanked rather than cut, so the line numbers in the failure messages still point
# at the right lines further down the file.
NOTES_BLOCK = re.compile(r"<!-- NOTES:START -->.*?<!-- NOTES:END -->", re.S)


def _authored(text: str) -> str:
    """Drop machine-written regions, leaving only prose this repository is responsible for."""
    return NOTES_BLOCK.sub(lambda m: "\n" * m.group(0).count("\n"), text)


class TestNoDerivativeFraming:
    """This project is described on its own terms, not as a version of another.

    The name searched for is assembled at run time rather than written out, so
    this file is scanned along with everything else instead of matching itself.
    """

    # Projects this was once described as a variant of.
    FORBIDDEN = ("rust" + "lings",)

    def test_nothing_describes_the_project_by_comparison(self, root: Path) -> None:
        offenders: list[str] = []
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix not in {".md", ".py", ".toml", ".cff", ".ipynb"}:
                continue
            if any(
                part in {".venv", ".git", ".ruff_cache", ".pytest_cache"} for part in path.parts
            ):
                continue
            text = _authored(path.read_text(encoding="utf-8", errors="replace")).lower()
            for term in self.FORBIDDEN:
                if term in text:
                    offenders.append(f"{path.relative_to(root)} mentions {term}")
        assert not offenders, f"derivative framing found: {offenders}"


class TestOneSpellingForTheCommand:
    """Written files and printed output must not disagree about how to run qx."""

    def test_no_written_file_uses_the_other_form(self, root: Path) -> None:
        """The quickstart installs `qx`, so every written file says plainly `qx`."""
        other = "uv" + " run qx"
        offenders: list[str] = []
        for path in sorted(root.rglob("*")):
            if path.suffix not in {".md", ".py"} or not path.is_file():
                continue
            if any(p in {".venv", ".git", ".ruff_cache", "tests"} for p in path.parts):
                continue
            if path.name == "__init__.py":
                continue  # __init__ documents the helper that chooses between the two
            source = _authored(path.read_text(encoding="utf-8"))
            for number, line in enumerate(source.splitlines(), 1):
                if other in line and "still works as" not in line:
                    offenders.append(f"{path.relative_to(root)}:{number}")
        assert not offenders, f"the other spelling appears in: {offenders}"

    def test_the_helper_answers_with_something_runnable(self) -> None:
        from quantum_exercises import invocation

        assert invocation() in {"qx", "uv run qx"}

    @staticmethod
    def _invocation_with(
        monkeypatch: pytest.MonkeyPatch, prefix: Path, path_entries: list[Path]
    ) -> str:
        """Answer invocation() against a real PATH holding real executables.

        Built on disk rather than by patching shutil.which, because the lookup
        walks PATH one directory at a time and a stubbed which() cannot model
        which entry a hit came from, which is the whole question being asked.
        """
        from quantum_exercises import invocation

        # shutil.which only matches a bare name on Windows if it ends in a PATHEXT
        # extension, and `uv tool install` writes qx.exe there anyway.
        name = "qx.exe" if os.name == "nt" else "qx"
        for directory in path_entries:
            directory.mkdir(parents=True, exist_ok=True)
            executable = directory / name
            executable.write_text("#!/bin/sh\n", encoding="utf-8")
            executable.chmod(0o755)

        monkeypatch.setattr(sys, "prefix", str(prefix))
        monkeypatch.setenv("PATH", os.pathsep.join(str(p) for p in path_entries))
        invocation.cache_clear()
        try:
            return invocation()
        finally:
            invocation.cache_clear()

    def test_only_a_qx_inside_this_environment_is_not_advertised(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """`uv run` puts the project's own bin on PATH for the length of one command.

        Answering "qx" on the strength of that tells the reader to type a command
        their next shell does not have, which is the case this helper exists for.
        """
        env = tmp_path / "project" / ".venv"
        assert self._invocation_with(monkeypatch, env, [env / "bin"]) == "uv run qx"

    def test_a_qx_outside_this_environment_is_advertised(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """What `uv tool install` leaves behind: a link in ~/.local/bin, really on PATH."""
        env = tmp_path / "tools" / "quantum-exercises"
        assert self._invocation_with(monkeypatch, env, [tmp_path / "local" / "bin"]) == "qx"

    def test_a_global_qx_wins_over_the_one_in_an_active_venv(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """An activated project venv shadows the global qx, but does not replace it.

        The venv's copy comes first on PATH, so stopping at the first hit answered
        "uv run qx" to someone who has qx installed and can simply type it. The
        search has to look past its own environment before giving up.
        """
        env = tmp_path / "project" / ".venv"
        entries = [env / "bin", tmp_path / "local" / "bin"]
        assert self._invocation_with(monkeypatch, env, entries) == "qx"

    def test_no_qx_anywhere_falls_back(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        monkeypatch.setattr(sys, "prefix", str(tmp_path))
        monkeypatch.setenv("PATH", str(empty))
        from quantum_exercises import invocation

        invocation.cache_clear()
        try:
            assert invocation() == "uv run qx"
        finally:
            invocation.cache_clear()
