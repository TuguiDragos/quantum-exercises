"""Project metadata that is easy to update in one place and forget in another."""

from __future__ import annotations

import re
import sys
from pathlib import Path

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


def _readme_dependency_rows(readme: str) -> dict[str, tuple[str, str]]:
    """Parse the dependency tables: name -> (declared range, verified version)."""
    rows = re.findall(r"^\| \[([a-z0-9-]+)\]\([^)]+\)[^|]*\| `([^`]+)` \| ([^|]+)\|", readme, re.M)
    return {name: (rng.strip(), verified.strip()) for name, rng, verified in rows}


def _declared_dependencies(pyproject: dict) -> dict[str, str]:
    """Every declared dependency: name -> the version range, extras stripped."""
    declared: dict[str, str] = {}
    specs = pyproject["project"]["dependencies"] + pyproject["dependency-groups"]["dev"]
    for spec in specs:
        name = re.split(r"[\[><=;]", spec)[0].strip()
        tail = spec.split(name, 1)[1].split(";")[0]
        declared[name] = tail.replace("[visualization]", "").strip()
    return declared


class TestReadmeDependencyTables:
    """The README lists every dependency. Lists drift; this stops that silently."""

    def test_every_declared_dependency_is_documented(self, pyproject: dict, root: Path) -> None:
        readme = (root / "README.md").read_text(encoding="utf-8")
        documented = _readme_dependency_rows(readme)
        for name in _declared_dependencies(pyproject):
            assert name in documented, f"{name} is declared but missing from the README tables"

    def test_no_invented_dependencies(self, pyproject: dict, root: Path) -> None:
        readme = (root / "README.md").read_text(encoding="utf-8")
        declared = _declared_dependencies(pyproject)
        for name in _readme_dependency_rows(readme):
            assert name in declared, f"the README lists {name}, which is not a dependency"

    def test_documented_ranges_match_pyproject(self, pyproject: dict, root: Path) -> None:
        readme = (root / "README.md").read_text(encoding="utf-8")
        declared = _declared_dependencies(pyproject)
        for name, (documented_range, _) in _readme_dependency_rows(readme).items():
            assert documented_range == declared[name], (
                f"{name}: README says {documented_range!r}, pyproject says {declared[name]!r}"
            )

    def test_documented_versions_are_the_installed_ones(self, root: Path) -> None:
        from importlib.metadata import PackageNotFoundError
        from importlib.metadata import version as installed_version

        readme = (root / "README.md").read_text(encoding="utf-8")
        for name, (_, claimed) in _readme_dependency_rows(readme).items():
            if not re.fullmatch(r"\d+\.\d+\.\d+", claimed):
                continue  # a note such as "only on 3.10" rather than a version
            try:
                actual = installed_version(name)
            except PackageNotFoundError:  # pragma: no cover - would mean a broken env
                pytest.fail(f"the README claims {name} {claimed}, but it is not installed")
            assert actual == claimed, f"{name}: README says {claimed}, installed is {actual}"

    def test_locked_package_count_is_accurate(self, root: Path) -> None:
        readme = (root / "README.md").read_text(encoding="utf-8")
        with (root / "uv.lock").open("rb") as handle:
            locked = tomllib.load(handle)
        claimed = int(re.search(r"is (\d+) packages", readme).group(1))
        assert claimed == len(locked["package"])

    def test_ci_matrix_matches_the_prose(self, root: Path) -> None:
        readme = (root / "README.md").read_text(encoding="utf-8")
        workflow = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        in_workflow = set(
            re.findall(
                r'"(\d+\.\d+)"', re.search(r"python-version: \[([^\]]+)\]", workflow).group(1)
            )
        )
        in_readme = set(
            re.findall(r"\d+\.\d+", re.search(r"CI runs the suite on\s+([^;]+);", readme).group(1))
        )
        assert in_workflow == in_readme, (
            f"workflow {sorted(in_workflow)}, README {sorted(in_readme)}"
        )

    def test_default_interpreter_matches_the_prose(self, root: Path) -> None:
        readme = (root / "README.md").read_text(encoding="utf-8")
        pinned = (root / ".python-version").read_text(encoding="utf-8").strip()
        assert f"installs {pinned} by default" in readme


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
