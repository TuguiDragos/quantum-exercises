"""Project metadata that is easy to update in one place and forget in another."""

from __future__ import annotations

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


def test_version_agrees_across_every_file(pyproject: dict, root: Path) -> None:
    """Three files carry the version. They drift the moment one is forgotten."""
    declared = pyproject["project"]["version"]

    assert quantum_exercises.__version__ == declared, (
        "src/quantum_exercises/__init__.py disagrees with pyproject.toml"
    )

    citation = (root / "CITATION.cff").read_text(encoding="utf-8")
    match = re.search(r"^version:\s*(\S+)\s*$", citation, re.MULTILINE)
    assert match is not None, "CITATION.cff has no version field"
    assert match.group(1) == declared, "CITATION.cff disagrees with pyproject.toml"


def test_changelog_documents_the_current_version(pyproject: dict, root: Path) -> None:
    declared = pyproject["project"]["version"]
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{declared}]" in changelog, f"CHANGELOG.md has no entry for {declared}"


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


@pytest.fixture(scope="module")
def badges(root: Path) -> dict[str, str]:
    """Every badge in the README: label -> URL."""
    readme = (root / "README.md").read_text(encoding="utf-8")
    return dict(re.findall(r"^\[!\[([a-z-]+)\]\((https://[^)]+)\)\]", readme, re.M))


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

    def test_locked_package_count_is_accurate(self, root: Path, inventory: str) -> None:
        with (root / "uv.lock").open("rb") as handle:
            locked = tomllib.load(handle)
        claimed = int(re.search(r"is (\d+) packages", inventory).group(1))
        assert claimed == len(locked["package"])

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
            "weekly-verify",
            "verified against qiskit".replace(" ", "-"),
            "python",
            "qiskit",
            "qiskit-ibm-runtime",
            "qiskit-aer",
            "uv",
            "ruff",
            "license",
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
            text = path.read_text(encoding="utf-8", errors="replace").lower()
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
            if path.name in {"CHANGELOG.md", "__init__.py"}:
                continue  # the changelog records history; __init__ documents the helper
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if other in line and "still works as" not in line:
                    offenders.append(f"{path.relative_to(root)}:{number}")
        assert not offenders, f"the other spelling appears in: {offenders}"

    def test_the_helper_answers_with_something_runnable(self) -> None:
        from quantum_exercises import invocation

        assert invocation() in {"qx", "uv run qx"}
