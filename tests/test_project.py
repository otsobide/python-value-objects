"""Project-level checks: packaging metadata, test configuration, Makefile, CI and contributor docs.

The metadata tests read the installed distribution, so the project must be installed from this
checkout (`uv run pytest` does that).
"""

import fnmatch
import importlib.metadata
import json
import re
import tomllib
from pathlib import Path

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
