"""Project-level checks: packaging metadata, test configuration, Makefile, CI and contributor docs.

The metadata tests read the installed distribution, so the project must be installed from this
checkout (`uv run pytest` does that).
"""

import fnmatch
import importlib.metadata
import importlib.util
import json
import re
import subprocess
import sys
import tomllib
import warnings
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
PROJECT = PYPROJECT["project"]
SETUPTOOLS = PYPROJECT["tool"]["setuptools"]
DISTRIBUTION = PROJECT["name"]


def python_floor() -> tuple[int, int]:
    """The oldest supported Python, read from `requires-python = ">=X.Y"`."""
    match = re.fullmatch(r">=\s*(\d+)\.(\d+)", PROJECT["requires-python"])
    assert match, f"requires-python must be a plain lower bound, got {PROJECT['requires-python']!r}"
    return int(match[1]), int(match[2])


def classifier_versions() -> list[tuple[int, int]]:
    """The `Programming Language :: Python :: X.Y` classifiers, in declaration order."""
    pattern = re.compile(r"Programming Language :: Python :: (\d+)\.(\d+)")
    return [(int(m[1]), int(m[2])) for c in PROJECT["classifiers"] if (m := pattern.fullmatch(c))]


def package_names() -> list[str]:
    """Dotted name of every directory under pyvalueobjects/ that holds Python modules."""
    return sorted({".".join(p.parent.relative_to(ROOT).parts) for p in (ROOT / "pyvalueobjects").rglob("*.py")})


@pytest.fixture(scope="module")
def metadata() -> importlib.metadata.PackageMetadata:
    """Core metadata of the distribution installed from this checkout.

    The lookup skips the `*.egg-info` that setuptools leaves in the checkout during editable builds:
    only an installed `.dist-info` records its origin in `direct_url.json`.
    """
    for distribution in importlib.metadata.distributions(name=DISTRIBUTION):
        origin = json.loads(distribution.read_text("direct_url.json") or "{}").get("url", "")
        if origin.rstrip("/") == ROOT.as_uri():
            return distribution.metadata
    pytest.fail(f"{DISTRIBUTION} is not installed from this checkout; run the suite with `uv run pytest`")


# ------------------------------------------------------------------------------------------- packaging metadata


@pytest.mark.parametrize("name", ["setup.cfg", "setup.py", "requirements.txt"])
def test_pyproject_is_the_only_source_of_packaging_metadata(name: str) -> None:
    assert not (ROOT / name).exists(), f"{name} duplicates pyproject.toml; PEP 621 metadata lives there alone"


def test_regression_C08_C44_requires_python_is_a_project_field() -> None:
    """C08/C44 (#32): setup.cfg hid python_requires under [options.packages.find], where setuptools ignores it."""
    assert PROJECT["requires-python"] == ">=3.11"
    assert python_floor() == (3, 11)


def test_regression_C08_C44_installed_metadata_declares_requires_python(
    metadata: importlib.metadata.PackageMetadata,
) -> None:
    """C08/C44 (#32): the 0.28.1 wheel had no Requires-Python, so pip installed it on any Python."""
    assert metadata["Requires-Python"] == ">=3.11"


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("Name", PROJECT["name"]),
        ("Version", PROJECT["version"]),
        ("Summary", PROJECT["description"]),
        ("Requires-Python", PROJECT.get("requires-python")),
        ("License-Expression", PROJECT["license"]),
        ("License-File", "LICENSE"),
        ("Description-Content-Type", "text/markdown"),
        ("Author-email", "Javier Parada <javierparada@pm.me>"),
        ("Keywords", ",".join(PROJECT["keywords"])),
    ],
)
def test_installed_metadata_matches_pyproject(
    metadata: importlib.metadata.PackageMetadata, field: str, expected: str
) -> None:
    assert metadata[field] == expected


def test_installed_metadata_lists_every_classifier_and_url(metadata: importlib.metadata.PackageMetadata) -> None:
    assert metadata.get_all("Classifier") == PROJECT["classifiers"]
    assert metadata.get_all("Project-URL") == [f"{label}, {url}" for label, url in PROJECT["urls"].items()]


def test_the_library_has_no_runtime_dependencies(metadata: importlib.metadata.PackageMetadata) -> None:
    assert PROJECT["dependencies"] == []
    assert "optional-dependencies" not in PROJECT
    assert metadata.get_all("Requires-Dist") is None


def test_the_version_lives_only_in_pyproject(metadata: importlib.metadata.PackageMetadata) -> None:
    import pyvalueobjects

    assert metadata["Version"] == PROJECT["version"]
    assert not hasattr(pyvalueobjects, "__version__"), "read the version with importlib.metadata.version()"


def test_python_classifiers_run_from_the_floor_without_gaps() -> None:
    versions = classifier_versions()
    assert versions, "declare one `Programming Language :: Python :: X.Y` classifier per supported version"
    assert versions[0] == python_floor()
    assert versions == [(3, minor) for minor in range(versions[0][1], versions[0][1] + len(versions))]
    assert "Programming Language :: Python :: 3 :: Only" in PROJECT["classifiers"]


def test_license_is_an_spdx_expression_not_a_classifier() -> None:
    assert PROJECT["license"] == "MIT"
    assert PROJECT["license-files"] == ["LICENSE"]
    assert (ROOT / "LICENSE").is_file()
    assert [c for c in PROJECT["classifiers"] if c.startswith("License ::")] == []


@pytest.mark.parametrize("label", ["Homepage", "Mirror", "Issues", "Changelog"])
def test_project_urls_use_https(label: str) -> None:
    assert PROJECT["urls"][label].startswith("https://")


# ------------------------------------------------------------------------------------------- build and wheel contents


def test_regression_C45_build_backend_is_declared() -> None:
    """C45 (#32): pyproject.toml named no build backend, so builds fell back to the legacy setuptools path."""
    assert PYPROJECT["build-system"]["build-backend"] == "setuptools.build_meta"


def test_regression_C45_build_requires_a_recent_setuptools() -> None:
    """C45 (#32): a bare `setuptools` requirement let setuptools < 61 build a wheel without any module.

    77 is also the first release that reads the SPDX `license` string and `license-files`.
    """
    floors = [m for req in PYPROJECT["build-system"]["requires"] if (m := re.fullmatch(r"setuptools>=(\d+)", req))]
    assert len(floors) == 1, PYPROJECT["build-system"]["requires"]
    assert int(floors[0][1]) >= 77


def test_regression_C45_packages_are_declared_explicitly() -> None:
    """C45 (#32): the wheel contents came from setuptools auto-discovery because no `packages` option was read."""
    packages = SETUPTOOLS["packages"]
    assert isinstance(packages, list) or packages["find"]["include"]


@pytest.mark.parametrize("package", package_names())
def test_regression_C45_every_package_directory_is_shipped(package: str) -> None:
    """C45 (#32): each directory holding modules must be selected by the declared `packages` configuration."""
    packages = SETUPTOOLS["packages"]
    if isinstance(packages, list):
        assert package in packages
        return
    find = packages["find"]
    assert any(fnmatch.fnmatchcase(package, pattern) for pattern in find["include"])
    assert not any(fnmatch.fnmatchcase(package, pattern) for pattern in find.get("exclude", []))
    is_regular = (ROOT.joinpath(*package.split(".")) / "__init__.py").is_file()
    assert is_regular or find.get("namespaces", True), f"{package} has no __init__.py and namespaces are disabled"


# ------------------------------------------------------------------------------------------- development environment

DEV_TOOLS = {"pytest": "pytest", "pytest-cov": "pytest_cov", "hypothesis": "hypothesis", "mypy": "mypy", "ruff": "ruff"}


def requirement(text: str) -> tuple[str, str, str]:
    """Split a PEP 508 requirement without extras into (name, specifier, marker)."""
    match = re.fullmatch(r"([A-Za-z0-9._-]+)\s*([^;]*?)\s*(?:;\s*(.+?)\s*)?", text)
    assert match, f"unsupported requirement {text!r}"
    return match[1], match[2], match[3] or ""


def release(version: str) -> tuple[int, ...]:
    """The numeric release segment of a version, e.g. '6.100' -> (6, 100)."""
    match = re.match(r"\d+(?:\.\d+)*", version)
    assert match, f"unsupported version {version!r}"
    return tuple(int(part) for part in match[0].split("."))


DEV_GROUP = {name: (spec, marker) for name, spec, marker in map(requirement, PYPROJECT["dependency-groups"]["dev"])}


@pytest.fixture(scope="module")
def lock() -> dict[str, Any]:
    path = ROOT / "uv.lock"
    assert path.is_file(), "uv.lock is missing: run `uv lock` and commit the result"
    return tomllib.loads(path.read_text(encoding="utf-8"))


def locked(lock: dict[str, Any], name: str) -> list[dict[str, Any]]:
    return [package for package in lock["package"] if package["name"] == name]


@pytest.mark.parametrize(("name", "module"), DEV_TOOLS.items())
def test_dev_group_installs_each_tool(name: str, module: str) -> None:
    spec, marker = DEV_GROUP[name]
    assert marker == "", f"{name} is needed on every platform"
    assert importlib.util.find_spec(module) is not None, f"{name} is not installed: run `uv sync`"
    floor = spec.removeprefix(">=")
    assert release(importlib.metadata.version(name)) >= release(floor)


def test_tzdata_is_only_needed_on_windows() -> None:
    assert DEV_GROUP["tzdata"][1] == "sys_platform == 'win32'"


def test_lockfile_records_the_current_dev_group(lock: dict[str, Any]) -> None:
    """A lock resolved from another dev group makes `uv sync --locked` fail in CI."""
    [project] = locked(lock, DISTRIBUTION)
    recorded = project["metadata"]["requires-dev"]["dev"]
    assert {(e["name"], e.get("specifier", ""), e.get("marker", "")) for e in recorded} == {
        (name, spec, marker) for name, (spec, marker) in DEV_GROUP.items()
    }


def test_lockfile_matches_the_project(lock: dict[str, Any]) -> None:
    [project] = locked(lock, DISTRIBUTION)
    assert lock["requires-python"] == PROJECT["requires-python"]
    assert project["version"] == PROJECT["version"]
    assert project["source"] == {"editable": "."}
    assert "dependencies" not in project, "the library itself must stay dependency-free"


@pytest.mark.parametrize("name", DEV_TOOLS)
def test_environment_runs_the_locked_tool_versions(lock: dict[str, Any], name: str) -> None:
    versions = [package["version"] for package in locked(lock, name)]
    assert importlib.metadata.version(name) in versions, f"{name} differs from uv.lock: run `uv sync`"


@pytest.mark.parametrize(
    "path",
    [
        ".venv/",
        "build/",
        "dist/",
        "pyvalueobjects.egg-info/",
        ".pytest_cache/",
        ".coverage",
        "htmlcov/",
        ".hypothesis/",
    ],
)
def test_generated_paths_are_ignored_by_git(path: str) -> None:
    """Directories carry a trailing slash, so git matches them as directories even when they do not exist."""
    check = subprocess.run(["git", "check-ignore", "--quiet", "--no-index", path], cwd=ROOT, check=False)
    assert check.returncode == 0, f"{path} is not in .gitignore"


# ------------------------------------------------------------------------------------------- test configuration

TEST_MODULES = sorted(
    path.relative_to(ROOT).as_posix()
    for path in (ROOT / "tests").rglob("*.py")
    if path.name.startswith("test_") or path.name.endswith("_test.py")
)


@pytest.fixture(scope="module")
def collected() -> set[str]:
    """Test files that a fresh `pytest --collect-only` run collects items from."""
    run = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 0, run.stdout[-2000:] + run.stderr[-2000:]
    return {line.split("::")[0] for line in run.stdout.splitlines() if "::" in line}


@pytest.mark.parametrize("path", TEST_MODULES)
def test_pytest_collects_every_test_module(collected: set[str], path: str) -> None:
    """The 0.x unittest modules (*_test.py) run under pytest next to the new test_*.py modules."""
    assert path in collected


@pytest.mark.parametrize(
    "category",
    [UserWarning, DeprecationWarning, PendingDeprecationWarning, FutureWarning, RuntimeWarning, ResourceWarning],
)
def test_warnings_are_errors(category: type[Warning]) -> None:
    with pytest.raises(category, match="unexpected"):
        warnings.warn("unexpected", category, stacklevel=1)


@pytest.mark.parametrize(
    ("category", "message"),
    [
        (DeprecationWarning, "invalid escape sequence '\\d'"),  # Python 3.11
        (SyntaxWarning, "invalid escape sequence '\\d'"),  # Python 3.12 to 3.14
        (SyntaxWarning, '"\\d" is an invalid escape sequence. Did you mean "\\\\d"?'),  # Python 3.15
    ],
)
def test_transitional_filter_silences_invalid_escape_sequences(category: type[Warning], message: str) -> None:
    """The legacy cpe.py regex is not a raw string; the filter goes away when cpe.py is replaced."""
    with warnings.catch_warnings(record=True) as caught:  # keeps the configured filters, records what passes them
        warnings.warn(message, category, stacklevel=1)
    assert caught == []


@pytest.mark.parametrize(
    ("category", "message"),
    [
        (SyntaxWarning, "'return' in a 'finally' block"),
        (DeprecationWarning, "datetime.datetime.utcnow() is deprecated"),
        (UserWarning, "invalid escape sequence '\\d'"),
        (RuntimeWarning, "invalid escape sequence '\\d'"),
    ],
)
def test_transitional_filter_silences_nothing_else(category: type[Warning], message: str) -> None:
    with pytest.raises(category):
        warnings.warn(message, category, stacklevel=1)


def test_invalid_escape_sequences_compile_on_every_supported_python() -> None:
    code = compile("PATTERN = '[a-z\\d]+'", "legacy.py", "exec")
    namespace: dict[str, object] = {}
    exec(code, namespace)
    assert namespace["PATTERN"] == "[a-z\\d]+"


def test_other_compile_time_warnings_still_fail() -> None:
    with pytest.raises(SyntaxError, match='"is" with'):
        compile("1 is 1", "module.py", "exec")


@pytest.mark.parametrize("option", ["-ra", "--strict-markers", "--strict-config"])
def test_pytest_runs_strict(pytestconfig: pytest.Config, option: str) -> None:
    assert option in pytestconfig.getini("addopts")
    assert pytestconfig.getini("xfail_strict") is True
