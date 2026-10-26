"""Project-level checks: packaging metadata, test configuration, Makefile, CI and contributor docs.

The metadata tests read the installed distribution, so the project must be installed from this
checkout (`uv run pytest` does that).
"""

import decimal
import fnmatch
import importlib.metadata
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import sysconfig
import tarfile
import tomllib
import warnings
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from hypothesis import settings

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


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("Name", PROJECT["name"]),
        ("Version", PROJECT["version"]),
        ("Summary", PROJECT["description"]),
        ("Requires-Python", PROJECT["requires-python"]),  # C08/C44 (#32): the 0.28.1 wheel had none
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


def test_the_version_lives_only_in_pyproject() -> None:
    import pyvalueobjects

    assert not hasattr(pyvalueobjects, "__version__"), "read the version with importlib.metadata.version()"


def test_python_classifiers_run_from_the_floor_without_gaps() -> None:
    versions = classifier_versions()
    assert versions, "declare one `Programming Language :: Python :: X.Y` classifier per supported version"
    assert versions[0] == python_floor()
    assert versions == [(3, minor) for minor in range(versions[0][1], versions[0][1] + len(versions))]
    assert "Programming Language :: Python :: 3 :: Only" in PROJECT["classifiers"]


def test_regression_typed_classifier_comes_with_the_py_typed_marker() -> None:
    """The metadata claimed `Typing :: Typed` before pyvalueobjects/py.typed existed (#39 review).

    The classifier, the package data that ships the marker and the marker itself arrive together.
    """
    marker = (ROOT / "pyvalueobjects" / "py.typed").is_file()
    assert ("Typing :: Typed" in PROJECT["classifiers"]) == marker
    assert ("py.typed" in SETUPTOOLS.get("package-data", {}).get("pyvalueobjects", [])) == marker


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


def uv_build(source: Path, out_dir: Path, *args: str) -> None:
    """Build `source` into `out_dir` with uv, offline from the cached build backend when the cache has it."""
    uv = os.environ.get("UV") or require("uv")  # `uv run` exports the uv that runs the suite
    for network in (["--offline"], []):
        command = [uv, "build", *network, "--quiet", "--out-dir", str(out_dir), *args, str(source)]
        run = subprocess.run(command, capture_output=True, text=True, check=False)
        if run.returncode == 0:
            return
    pytest.fail(f"uv build failed: {run.stderr[-2000:]}")


def test_sdist_ships_the_library_and_no_tests(tmp_path: Path) -> None:
    """setuptools adds tests/test*.py to an sdist by default, and alone they fail at collection (#39 review)."""
    uv_build(export(tmp_path / "export"), tmp_path / "dist", "--sdist")
    [sdist] = (tmp_path / "dist").glob("*.tar.gz")
    with tarfile.open(sdist) as archive:
        files = {member.name.split("/", 1)[1] for member in archive.getmembers() if member.isfile()}
    library = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "pyvalueobjects").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    generated = {"PKG-INFO", "setup.cfg"}  # setuptools writes both, and the egg-info directory
    sources = {"LICENSE", "MANIFEST.in", "README.md", "pyproject.toml"}
    assert {path for path in files if not path.startswith(f"{DISTRIBUTION}.egg-info/")} == library | generated | sources


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


# Paths that builds, test runs and tools create; `make clean` removes all of them except the environment.
GENERATED_PATHS = [
    "build/",
    "dist/",
    "pyvalueobjects.egg-info/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    ".coverage",
    "htmlcov/",
    ".hypothesis/",
]


# Paths that must stay tracked.
SOURCE_PATHS = [".github/", "pyvalueobjects/", "tests/", "AGENTS.md", "Makefile", "pyproject.toml", "uv.lock"]


def export(destination: Path) -> Path:
    """A copy of the checkout without .git, the environment or generated files, like a `git archive` export."""
    generated = [path.rstrip("/") for path in GENERATED_PATHS]
    shutil.copytree(ROOT, destination, ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", *generated))
    return destination


@pytest.fixture(scope="module")
def git_ignores(tmp_path_factory: pytest.TempPathFactory) -> Callable[[str], bool]:
    """Whether .gitignore ignores a path, asked of a scratch repository that holds only a copy of it.

    Asking git in ROOT needs ROOT to be a git work tree, and the user's global excludes took part.
    """
    git = require("git")
    scratch = tmp_path_factory.mktemp("gitignore")
    shutil.copy(ROOT / ".gitignore", scratch)
    subprocess.run([git, "init", "--quiet"], cwd=scratch, capture_output=True, check=True)
    no_global_excludes = f"core.excludesFile={scratch / 'no-global-excludes'}"

    def ignores(path: str) -> bool:
        """Directories carry a trailing slash, so git matches them as directories even when they do not exist."""
        args = [git, "-c", no_global_excludes, "check-ignore", "--quiet", "--no-index", path]
        check = subprocess.run(args, cwd=scratch, capture_output=True, text=True, check=False)
        assert check.returncode in (0, 1), check.stderr  # 0 ignored, 1 not ignored; 128 is an error, not an answer
        return check.returncode == 0

    return ignores


def gitignore_sections() -> dict[str, list[str]]:
    """The patterns of .gitignore under each `# heading` line."""
    sections: dict[str, list[str]] = {}
    heading = ""
    for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
        elif line.strip():
            sections.setdefault(heading, []).append(line.strip())
    return sections


@pytest.mark.parametrize(
    ("heading", "patterns"), [("mypy", [".mypy_cache/", ".dmypy.json", "dmypy.json"]), ("ruff", [".ruff_cache/"])]
)
def test_regression_gitignore_lists_each_dev_tool_under_its_heading(heading: str, patterns: list[str]) -> None:
    """`# ruff` was inserted above the mypy daemon files, which then sat under the ruff heading (#39 review)."""
    assert gitignore_sections()[heading] == patterns


@pytest.mark.parametrize("path", [".venv/", *GENERATED_PATHS])
def test_generated_paths_are_ignored_by_git(git_ignores: Callable[[str], bool], path: str) -> None:
    assert git_ignores(path), f"{path} is not in .gitignore"


@pytest.mark.parametrize("path", SOURCE_PATHS)
def test_source_paths_are_not_ignored_by_git(git_ignores: Callable[[str], bool], path: str) -> None:
    assert not git_ignores(path), f".gitignore ignores {path}"


def test_regression_gitignore_checks_pass_in_an_export_without_git(tmp_path: Path) -> None:
    """In a `git archive` export or a release tarball, git exited 128 in ROOT and every check failed (#39 review)."""
    require("git")
    tree = export(tmp_path / "export")
    selection = "generated_paths_are_ignored_by_git or source_paths_are_not_ignored_by_git"
    pytest_args = ["-q", "-p", "no:cacheprovider", "--basetemp", str(tmp_path / "basetemp"), "-k", selection]
    run = subprocess.run(
        [sys.executable, "-m", "pytest", *pytest_args, "tests/test_project.py"],
        cwd=tree,
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 0, run.stdout[-2000:] + run.stderr[-2000:]
    assert re.search(rf"^{1 + len(GENERATED_PATHS) + len(SOURCE_PATHS)} passed\b", run.stdout, re.MULTILINE), run.stdout


# ------------------------------------------------------------------------------------------- test configuration

TEST_MODULES = sorted(
    path.relative_to(ROOT).as_posix()
    for path in (ROOT / "tests").rglob("*.py")
    if path.name.startswith("test_") or path.name.endswith("_test.py")
)


REPORT_TAG = "collection report: "
COLLECT = f"""
import decimal, fractions, json, sys  # loaded first, as by any library module that uses Decimal or Fraction
import pytest

class Report:
    def pytest_collection_finish(self, session):
        functions = [item for item in session.items if isinstance(item, pytest.Function)]
        self.files = sorted({{item.nodeid.split("::")[0] for item in session.items}})
        self.modules = sorted({{item.module.__name__ for item in functions}})

report = Report()
code = pytest.main(["--collect-only", "-q", "-p", "no:cacheprovider", *sys.argv[1:]], plugins=[report])
import numbers
fraction = str(fractions.Fraction(1, 3) + 1)
print({REPORT_TAG!r} + json.dumps(
    {{"numbers": numbers.__file__, "fraction": fraction, "files": report.files, "modules": report.modules}}
))
sys.exit(code)
"""


def collection_report(lines: list[str]) -> dict[str, Any]:
    """The JSON report that COLLECT prints on its tagged line: paths may contain spaces."""
    [report] = [line.removeprefix(REPORT_TAG) for line in lines if line.startswith(REPORT_TAG)]
    parsed: dict[str, Any] = json.loads(report)
    return parsed


def collect(*pytest_args: str) -> dict[str, Any]:
    """The report of a fresh `pytest --collect-only` run in a process that imported the stdlib numbers first."""
    run = subprocess.run(
        [sys.executable, "-c", COLLECT, *pytest_args], cwd=ROOT, capture_output=True, text=True, check=False
    )
    assert run.returncode == 0, run.stdout[-2000:] + run.stderr[-2000:]
    return collection_report(run.stdout.splitlines())


@pytest.fixture(scope="module")
def collection() -> dict[str, Any]:
    """The report of a collection run with this repository's configuration."""
    return collect()


@pytest.mark.parametrize("path", TEST_MODULES)
def test_pytest_collects_every_test_module(collection: dict[str, Any], path: str) -> None:
    """The 0.x unittest modules (*_test.py) run under pytest next to the new test_*.py modules."""
    assert path in collection["files"]


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
        (SyntaxWarning, "invalid escape sequence '\\d'"),  # Python 3.12 and 3.13
        (  # Python 3.14 and later
            SyntaxWarning,
            '"\\d" is an invalid escape sequence. Such sequences will not work in the future. '
            'Did you mean "\\\\d"? A raw string is also an option.',
        ),
    ],
)
def test_transitional_filter_silences_invalid_escape_sequences(category: type[Warning], message: str) -> None:
    """The legacy cpe.py regex is not a raw string; the filter goes away when cpe.py is replaced."""
    with warnings.catch_warnings(record=True) as caught:  # keeps the configured filters, records what passes them
        warnings.warn(message, category, stacklevel=1)
    assert caught == []


def test_regression_transitional_filter_silences_the_warning_of_this_python() -> None:
    """The filter was checked against a made-up message: the reworded one already comes from 3.14 (#39 review)."""
    with warnings.catch_warnings(record=True) as emitted:
        warnings.simplefilter("always")
        compile("PATTERN = '[a-z\\d]+'", "legacy.py", "exec")
    [warning] = emitted
    assert "invalid escape sequence" in str(warning.message)
    with warnings.catch_warnings(record=True) as caught:
        warnings.warn(str(warning.message), warning.category, stacklevel=1)
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


def test_pytest_xfail_is_strict(pytestconfig: pytest.Config) -> None:
    assert pytestconfig.getini("xfail_strict") is True


def test_every_test_runs_under_a_hostile_decimal_context() -> None:
    """tests/conftest.py: library code that relied on the caller's decimal context would fail here."""
    context = decimal.getcontext()
    assert (context.prec, context.rounding) == (3, decimal.ROUND_FLOOR)
    assert not any(context.traps.values())


@pytest.mark.parametrize(("profile", "examples"), [("dev", 100), ("ci", 1000)])
def test_hypothesis_profiles(profile: str, examples: int) -> None:
    assert settings.get_profile(profile).max_examples == examples


def test_ci_hypothesis_profile_is_reproducible() -> None:
    ci = settings.get_profile("ci")
    assert ci.derandomize is True and ci.deadline is None


def test_hypothesis_profile_comes_from_the_environment() -> None:
    expected = settings.get_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))
    assert settings().max_examples == expected.max_examples and settings().derandomize == expected.derandomize


# ------------------------------------------------------------------------------------------- Makefile

MAKEFILE = (ROOT / "Makefile").read_text(encoding="utf-8")
MAKE_TARGETS = sorted(m[1] for m in re.finditer(r"^([A-Za-z0-9_-]+)\s*:(?!=)", MAKEFILE, re.MULTILINE))
PHONY = {name for m in re.finditer(r"^\.PHONY\s*:(?!=)(.*)$", MAKEFILE, re.MULTILINE) for name in m[1].split()}


def require(tool: str) -> str:
    """The path of a command-line tool; skips the calling test when it is not installed."""
    path = shutil.which(tool)
    if path is None:
        pytest.skip(f"{tool} is not installed")
    return path


def make(*args: str, cwd: Path = ROOT) -> list[str]:
    """The commands `make` would run for `args`, printed with -n instead of being run."""
    run = subprocess.run([require("make"), "-n", *args], cwd=cwd, capture_output=True, text=True, check=False)
    assert run.returncode == 0, run.stderr
    return [line for line in run.stdout.splitlines() if not line.startswith("make")]  # drops "Nothing to be done"


def test_regression_C50_phony_is_a_rule_not_a_variable() -> None:
    """C50 (#32): `.PHONY = test` assigned a variable, so a file named `test` turned `make test` into a no-op."""
    assert not re.search(r"^\.PHONY\s*[:?+!]?=", MAKEFILE, re.MULTILINE)
    assert PHONY


@pytest.mark.parametrize("target", MAKE_TARGETS)
def test_regression_C50_every_target_is_phony(target: str) -> None:
    assert target in PHONY


def test_phony_lists_only_real_targets() -> None:
    assert PHONY.issubset(MAKE_TARGETS), PHONY.difference(MAKE_TARGETS)


@pytest.mark.parametrize("target", MAKE_TARGETS)
def test_regression_C50_a_file_named_like_a_target_does_not_skip_it(tmp_path: Path, target: str) -> None:
    clean, shadowed = tmp_path / "clean", tmp_path / "shadowed"
    for directory in (clean, shadowed):
        directory.mkdir()
        shutil.copy(ROOT / "Makefile", directory)
    (shadowed / target).touch()
    assert make(target, cwd=clean), f"`make {target}` runs nothing"
    assert make(target, cwd=shadowed) == make(target, cwd=clean)


def test_default_goal_is_the_full_check() -> None:
    assert make() == make("check")


@pytest.mark.parametrize("target", sorted(set(MAKE_TARGETS) - {"clean"}))
def test_make_targets_run_tools_through_uv(target: str) -> None:
    """uv runs every tool from the environment that uv.lock pins."""
    assert all(re.search(r"(?:^|&& )uv ", command) for command in make(target)), make(target)


def test_make_cov_measures_branch_coverage_of_the_package() -> None:
    assert make("cov") == ["uv run pytest --cov --cov-report=term-missing"]
    run = PYPROJECT["tool"]["coverage"]["run"]
    assert run["branch"] is True
    assert run["source"] == ["pyvalueobjects"]


def test_coverage_reports_every_module_of_the_package(tmp_path: Path) -> None:
    """Modules that nothing imports count as uncovered, also inside a subpackage without __init__.py.

    The 0.x security subpackage has none, so its 14 never-imported modules were missing and the total
    read 98 % instead of 69 % (#39 review).
    """
    stub, report = tmp_path / "stub.py", tmp_path / "coverage.json"
    stub.write_text("import pyvalueobjects\n", encoding="utf-8")
    env = {**os.environ, "COVERAGE_FILE": str(tmp_path / ".coverage")}
    for args in (["run", str(stub)], ["json", "--fail-under=0", "-o", str(report)]):
        run = subprocess.run(
            [sys.executable, "-m", "coverage", *args], cwd=ROOT, env=env, capture_output=True, text=True, check=False
        )
        assert run.returncode == 0, run.stdout + run.stderr
    omit = PYPROJECT["tool"]["coverage"]["run"].get("omit", [])
    modules = {path.relative_to(ROOT).as_posix() for path in (ROOT / "pyvalueobjects").rglob("*.py")}
    expected = {module for module in modules if not any(fnmatch.fnmatch(module, pattern) for pattern in omit)}
    assert set(json.loads(report.read_text(encoding="utf-8"))["files"]) == expected


def test_make_clean_removes_generated_paths_and_keeps_the_rest(tmp_path: Path) -> None:
    make_command = require("make")
    shutil.copy(ROOT / "Makefile", tmp_path)
    for path in GENERATED_PATHS:
        if path.endswith("/"):
            (tmp_path / path / "nested").mkdir(parents=True)
        else:
            (tmp_path / path).touch()
    (tmp_path / ".venv").mkdir()
    (tmp_path / "keep.py").touch()
    subprocess.run([make_command, "clean"], cwd=tmp_path, capture_output=True, check=True)
    assert sorted(path.name for path in tmp_path.iterdir()) == [".venv", "Makefile", "keep.py"]


def test_regression_C43_make_test_lets_pytest_name_the_modules() -> None:
    """C43 (#32): `unittest discover -s ./tests` without `-t` put tests/ on sys.path, so tests/numbers became `numbers`."""
    assert make("test") == ["uv run pytest"]


@pytest.mark.parametrize("directory", sorted({str(Path(path).parent) for path in TEST_MODULES}))
def test_regression_C43_every_test_directory_is_a_package(directory: str) -> None:
    """pytest imports tests/numbers/int_test.py as tests.numbers.int_test only while each directory has __init__.py."""
    for package in [Path(directory), *Path(directory).parents][:-1]:
        assert (ROOT / package / "__init__.py").is_file(), f"{package} is not a package"


def test_regression_C43_test_modules_are_imported_under_the_tests_package(collection: dict[str, Any]) -> None:
    """C43 (#32): unittest discovery imported tests/numbers/int_test.py as `numbers.int_test`.

    The names come from the full collection run, not from this session, which a `-k` or a single file narrows.
    """
    expected = sorted(path.removesuffix(".py").replace("/", ".") for path in TEST_MODULES)
    assert collection["modules"] == expected


def test_regression_C43_collection_keeps_the_stdlib_numbers_module(collection: dict[str, Any]) -> None:
    """With `decimal` imported first, 0.28.1 discovery failed with "'numbers' is not a package"."""
    assert Path(collection["numbers"]).parent == Path(sysconfig.get_path("stdlib"))
    assert collection["fraction"] == "4/3"
    import numbers

    assert Path(numbers.__file__).parent == Path(sysconfig.get_path("stdlib"))


@pytest.mark.parametrize(
    "path",
    [
        "C:\\Program Files\\Python311\\Lib\\numbers.py",  # a python.org install on Windows
        "/Users/Ada Lovelace/.local/share/uv/python/cpython-3.12/lib/python3.12/numbers.py",  # a home with a space
    ],
)
def test_regression_C43_collection_report_keeps_paths_with_spaces(path: str) -> None:
    """The report was one space-separated line, so a stdlib path with a space was cut (#39 review)."""
    report = {"numbers": path, "fraction": "4/3", "files": ["tests/test_project.py"], "modules": ["tests.test_project"]}
    assert collection_report(["tests/test_project.py::test_x", REPORT_TAG + json.dumps(report)]) == report


# ------------------------------------------------------------------------------------------- lint and type checks

RUFF = PYPROJECT["tool"]["ruff"]
MYPY = PYPROJECT["tool"]["mypy"]
RUFF_LEGACY = RUFF.get("extend-exclude", [])
MYPY_LEGACY = sorted(module for o in MYPY.get("overrides", []) if o.get("ignore_errors") for module in o["module"])
MYPY_EXCLUDE = [MYPY["exclude"]] if isinstance(MYPY.get("exclude"), str) else MYPY.get("exclude", [])


def write_tree(root: Path, files: dict[str, str]) -> None:
    """Write `files` ({relative path: text}) under `root`, next to a copy of this pyproject.toml."""
    shutil.copy(ROOT / "pyproject.toml", root)
    for path, text in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8")


def ruff_files(root: Path) -> set[str]:
    """Files that `ruff check .` lints under `root`, relative to it."""
    run = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--show-files", "."],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 0, run.stderr
    return {Path(line).relative_to(root).as_posix() for line in run.stdout.splitlines() if line.strip()}


def test_ruff_and_mypy_target_the_oldest_supported_python() -> None:
    major, minor = python_floor()
    assert RUFF["target-version"] == f"py{major}{minor}"
    assert MYPY["python_version"] == f"{major}.{minor}"


def test_mypy_checks_the_package_and_the_typing_contract_strictly() -> None:
    assert MYPY["strict"] is True
    assert MYPY["files"] == ["pyvalueobjects", "tests/static"]
    assert (ROOT / "tests" / "static" / "check_api.py").is_file()


def test_the_typing_contract_is_never_run_by_pytest(collection: dict[str, Any]) -> None:
    """tests/static/check_api.py only exists for mypy: its module-level calls must not run as a test."""
    assert not [path for path in collection["files"] if path.startswith("tests/static/")]


@pytest.mark.parametrize("path", RUFF_LEGACY)
def test_ruff_exclusions_point_at_existing_legacy_code(path: str) -> None:
    """A stale exclusion would silently skip whatever later lands at that path."""
    assert (ROOT / path).exists()


@pytest.mark.parametrize("module", MYPY_LEGACY)
def test_mypy_overrides_point_at_existing_legacy_packages(module: str) -> None:
    assert module.endswith(".*")
    assert ROOT.joinpath(*module.removesuffix(".*").split(".")).is_dir()


def test_ruff_and_mypy_skip_the_same_legacy_packages() -> None:
    """mypy needs both the `exclude` and the override: it still follows the imports of pyvalueobjects/__init__.py."""
    packages = {path for path in RUFF_LEGACY if path.startswith("pyvalueobjects/")}
    assert packages == {module.removesuffix(".*").replace(".", "/") for module in MYPY_LEGACY}
    for package in packages:
        assert any(re.search(pattern, f"{package}/module.py") for pattern in MYPY_EXCLUDE), package


def test_ruff_lints_new_code_and_skips_legacy_code(tmp_path: Path) -> None:
    new = ["pyvalueobjects/__init__.py", "pyvalueobjects/_core.py", "tests/__init__.py", "tests/test_core.py"]
    write_tree(tmp_path, dict.fromkeys(new + [f"{path}/module.py" for path in RUFF_LEGACY], ""))
    assert ruff_files(tmp_path) == {"pyproject.toml", *new}


TOO_LONG = "# " + "x" * 119  # 121 characters, one over the line length
RUFF_FAMILIES = ["E", "F", "W", "I", "UP", "B", "SIM", "RUF", "PT", "C4", "PIE"]
RUFF_PROBE = f'''\
import sys
import os
from typing import List

import pytest

{TOO_LONG}


class Probe:
    __slots__ = ("b", "a")  # RUF023 stays off: the order is the constructor's field order


def probe(items: List[int] = []) -> object:
    """Trips at least one rule of every selected family."""
    pass
    if items == None:
        return "\\d"
    try:
        squares = list(x * x for x in items)
    except Exception:
        pass
    return [1] + squares, sys.path[0].startswith("a") or sys.path[0].startswith("b")


@pytest.mark.parametrize("a,b", [(1, 2)])
def test_probe(a: int, b: int) -> None:
    assert a
'''
RUFF_TEST_PROBE = f"""\
{TOO_LONG}
KELVIN = "\u212a"


def test_probe() -> None:
    assert KELVIN and 1
"""


def test_ruff_enforces_the_rule_set_and_the_test_exemptions(tmp_path: Path) -> None:
    """Each selected family flags the probe, while RUF023 and the exemptions for tests/ stay quiet."""
    write_tree(tmp_path, {"pyvalueobjects/_core.py": RUFF_PROBE, "tests/test_probe.py": RUFF_TEST_PROBE})
    run = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--no-cache", "--output-format=concise", "."],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    found = re.findall(r"^(\S+?):\d+:\d+: ([A-Z]+[0-9]+)", run.stdout, re.MULTILINE)
    codes = {code for path, code in found if path.replace("\\", "/") == "pyvalueobjects/_core.py"}
    families = {
        next((f for f in RUFF_FAMILIES if code.startswith(f) and code[len(f)].isdigit()), code) for code in codes
    }
    assert families == set(RUFF_FAMILIES), run.stdout
    assert "E501" in codes
    assert "RUF023" not in codes
    assert [path for path, _ in found if path.replace("\\", "/") != "pyvalueobjects/_core.py"] == [], run.stdout


def test_mypy_checks_new_code_strictly_and_skips_legacy_code(tmp_path: Path) -> None:
    """The 0.x packages need `exclude` and the `ignore_errors` override, because mypy follows the package imports."""
    legacy = [path for path in RUFF_LEGACY if path.startswith("pyvalueobjects/")]
    untyped = 'def legacy(value):\n    return value + 1\n\n\nWRONG: int = "s"\n'
    files = {f"{path}/module.py": untyped for path in legacy}  # no __init__.py, like the 0.x subpackages
    files["pyvalueobjects/__init__.py"] = "".join(
        f"from {path.replace('/', '.')}.module import legacy as _{Path(path).name}\n" for path in legacy
    )
    files["pyvalueobjects/_core.py"] = (
        'def untyped(value):\n    return value\n\n\ndef wrong() -> int:\n    return "s"\n'
    )
    files["tests/static/check_api.py"] = "from pyvalueobjects._core import wrong\n\nCHECKED: str = wrong()\n"
    write_tree(tmp_path, files)
    run = subprocess.run([sys.executable, "-m", "mypy"], cwd=tmp_path, capture_output=True, text=True, check=False)
    errors = re.findall(r"^(\S+?):\d+: error: .*\[([\w-]+)\]$", run.stdout, re.MULTILINE)
    expected = [
        ("pyvalueobjects/_core.py", "no-untyped-def"),
        ("pyvalueobjects/_core.py", "return-value"),
        ("tests/static/check_api.py", "assignment"),
    ]
    assert sorted((path.replace("\\", "/"), code) for path, code in errors) == expected, run.stdout + run.stderr


def test_ruff_lints_the_new_modules_of_this_repository() -> None:
    linted = ruff_files(ROOT)
    assert {"pyvalueobjects/__init__.py", "tests/test_project.py"} <= linted
    assert [path for path in linted if any(path.startswith(f"{legacy}/") for legacy in RUFF_LEGACY)] == []


@pytest.mark.parametrize(
    ("target", "commands"),
    [
        ("lint", ["uv run ruff check .", "uv run ruff format --check ."]),
        ("format", ["uv run ruff check --fix .", "uv run ruff format ."]),
        ("typecheck", ["uv run mypy"]),
    ],
)
def test_make_quality_targets(target: str, commands: list[str]) -> None:
    assert make(target) == commands


def test_make_check_runs_lint_then_types_then_coverage() -> None:
    assert make("check") == make("lint") + make("typecheck") + make("cov")


# ------------------------------------------------------------------------------------------- continuous integration

WORKFLOWS = ROOT / ".github" / "workflows"
CI_SOURCE = (WORKFLOWS / "tests.yml").read_text(encoding="utf-8")


def uncommented(text: str) -> str:
    """`text` without comment lines: a YAML comment, or a shell comment inside a `run: |` block, disables a line."""
    return "".join(line for line in text.splitlines(keepends=True) if not line.lstrip().startswith("#"))


def blocks(text: str, indent: int) -> dict[str, str]:
    """The `key:` entries of a YAML mapping at `indent`, each with the lines nested under it."""
    margin = " " * indent
    pattern = rf"^{margin}([\w-]+):[^\n]*\n(.*?)(?=^{margin}[\w-]+:|\Z)"
    return dict(re.findall(pattern, text, re.MULTILINE | re.DOTALL))


def ci_steps(job: str) -> list[dict[str, str]]:
    """The steps of a job as {key: value}; the lines nested under `run: |` or `with:` form one value."""
    steps: list[dict[str, str]] = []
    key = ""
    for line in job.split("\n    steps:\n", 1)[1].splitlines():
        if line.startswith("      - "):
            steps.append({})
            line = "        " + line.removeprefix("      - ")
        if match := re.fullmatch(r" {8}([\w-]+):(?: (.*))?", line):
            key = match[1]
            steps[-1][key] = "" if match[2] in (None, "|") else match[2]
        else:
            steps[-1][key] = f"{steps[-1][key]}\n{line.strip()}".lstrip("\n")
    return steps


CI = uncommented(CI_SOURCE)
CI_TRIGGERS = sorted(blocks(blocks(CI, 0)["on"], 2))
CI_JOBS = blocks(blocks(CI, 0)["jobs"], 2)


def ci_runs(job: str) -> list[str]:
    return [step["run"] for step in ci_steps(CI_JOBS[job]) if "run" in step]


README = (ROOT / "README.md").read_text(encoding="utf-8")
REPOSITORY = "otsobide/python-value-objects"


def make_calls(text: str) -> list[str]:
    """Every target named in a `make ...` command of `text`."""
    return [target for m in re.finditer(r"\bmake((?: [a-z][a-z-]*)+)", text) for target in m[1].split()]


def test_ci_has_a_test_matrix_and_a_quality_job() -> None:
    assert sorted(CI_JOBS) == ["quality", "test"]


def test_ci_runs_on_every_push_and_pull_request() -> None:
    assert {"push", "pull_request"} <= set(CI_TRIGGERS)


def test_ci_runs_hypothesis_with_the_ci_profile() -> None:
    assert re.search(r"^    env:\n      HYPOTHESIS_PROFILE: ci$", CI_JOBS["test"], re.MULTILINE)


def test_ci_tests_every_supported_python() -> None:
    [matrix] = re.findall(r"^ +python: \[(.*)\]$", CI_JOBS["test"], re.MULTILINE)
    assert re.findall(r'"(3\.\d+)"', matrix) == [f"{major}.{minor}" for major, minor in classifier_versions()]
    assert "fail-fast: false" in CI_JOBS["test"]


def test_ci_quality_job_runs_on_the_oldest_supported_python() -> None:
    major, minor = python_floor()
    assert re.findall(r'python-version: "([\d.]+)"', CI_JOBS["quality"]) == [f"{major}.{minor}"]
    assert f"uv venv /tmp/smoke -p {major}.{minor}" in CI_JOBS["quality"]


@pytest.mark.parametrize("job", ["test", "quality"])
def test_ci_installs_exactly_what_uv_lock_pins(job: str) -> None:
    actions = [step["uses"].split("@")[0] for step in ci_steps(CI_JOBS[job]) if "uses" in step]
    assert actions == ["actions/checkout", "astral-sh/setup-uv"]
    assert ci_runs(job)[0] == "uv sync --locked"
    assert "pip install -r" not in CI_JOBS[job]


def test_ci_runs_the_suite_with_coverage() -> None:
    assert ci_runs("test") == ["uv sync --locked", "uv run pytest --cov"]


def test_ci_quality_job_checks_lint_types_and_builds() -> None:
    assert ci_runs("quality")[:3] == [
        "uv sync --locked",
        "make lint typecheck",
        "make build && uvx twine check --strict dist/*",
    ]


@pytest.mark.parametrize(
    ("name", "command"),
    [
        ("The wheel ships every module of the source tree", "rglob('*.py')"),  # #32 C45
        # -I: import the installed wheel, not the checkout in the working directory
        ("The wheel installs alone and declares no dependencies", "/tmp/smoke/bin/python -I -c"),
        ("The wheel installs alone and declares no dependencies", "assert not m.requires('pyvalueobjects')"),
        (
            "The wheel installs alone and declares no dependencies",
            "m.metadata('pyvalueobjects')['Requires-Python'] == '>=3.11'",
        ),
    ],
)
def test_ci_quality_job_checks_the_built_wheel(name: str, command: str) -> None:
    [run] = [step["run"] for step in ci_steps(CI_JOBS["quality"]) if step.get("name") == name]
    assert command in run


@pytest.mark.parametrize("command", ["uv run pytest --cov", "make build", "/tmp/smoke/bin/python", "python3 -c"])
def test_regression_ci_checks_ignore_commented_out_steps(command: str) -> None:
    """The checks matched raw substrings of the workflow, so a step disabled with `#` still passed (#39 review)."""
    disabled = re.sub(rf"^( +)((?:- run: )?{re.escape(command)})", r"\1# \2", CI_SOURCE, flags=re.MULTILINE)
    assert disabled != CI_SOURCE
    jobs = blocks(blocks(uncommented(disabled), 0)["jobs"], 2).values()
    assert [run for job in jobs for step in ci_steps(job) if command in (run := step.get("run", ""))] == []


@pytest.mark.parametrize("target", make_calls(CI))
def test_ci_only_calls_existing_make_targets(target: str) -> None:
    assert target in MAKE_TARGETS


def test_ci_token_is_read_only() -> None:
    assert re.search(r"^permissions:\n  contents: read\n", CI, re.MULTILINE)


@pytest.mark.parametrize("action", sorted(set(re.findall(r"uses: (\S+)", CI))))
def test_ci_actions_are_pinned_to_a_major_version(action: str) -> None:
    assert re.fullmatch(r"[\w-]+/[\w-]+@v\d+", action)


@pytest.mark.parametrize(
    "link", sorted(set(re.findall(r"https://github\.com/([^)\s]+?/actions/workflows/[^)\s/]+)", README)))
)
def test_readme_badges_point_at_existing_workflows(link: str) -> None:
    """The 0.28.1 badge linked a test.yml that never existed (#32 C52)."""
    repository, workflow = link.split("/actions/workflows/")
    assert repository == REPOSITORY
    assert (WORKFLOWS / workflow).is_file()


def test_readme_shows_the_ci_status_badge() -> None:
    badge = f"https://github.com/{REPOSITORY}/actions/workflows/tests.yml/badge.svg"
    assert f"[![Tests]({badge})](https://github.com/{REPOSITORY}/actions/workflows/tests.yml)" in README


# ------------------------------------------------------------------------------------------- contributor docs

AGENTS = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
AGENTS_CODE = "\n".join(re.findall(r"```.*?```|`[^`\n]+`", AGENTS, re.DOTALL))
AGENTS_PATHS = sorted(
    set(re.findall(r"`((?:\.github|pyvalueobjects|tests)/[^`\s<>*]*|[\w.-]+\.(?:toml|lock|md))`", AGENTS))
)
PYTEST_INI = PYPROJECT["tool"]["pytest"]["ini_options"]


def test_regression_C55_agents_md_does_not_claim_pytest_misses_the_tests() -> None:
    """C55 (#32): AGENTS.md said default pytest discovery won't find the *_test.py modules."""
    claim = r"[^.\n]*pytest[^.\n]*(?:won't|will not|does not|doesn't|cannot|can't) find[^.\n]*"
    assert re.findall(claim, AGENTS) == []


def test_regression_C55_default_pytest_discovery_finds_every_test_module(tmp_path: Path) -> None:
    """An empty config gives pytest's defaults, which already collect both test_*.py and *_test.py."""
    ini = tmp_path / "pytest.ini"
    ini.write_text("[pytest]\n", encoding="utf-8")
    assert collect("-c", str(ini), "--rootdir", str(ROOT), "tests")["files"] == TEST_MODULES


PYTEST_DEFAULT_FILES = ["test_*.py", "*_test.py"]  # pytest's built-in `python_files`


def test_regression_pyproject_does_not_restate_the_default_test_file_patterns(pytestconfig: pytest.Config) -> None:
    """The "transitional" `python_files = ["test_*.py", "*_test.py"]` was pytest's own default (#39 review)."""
    assert "python_files" not in PYTEST_INI
    assert pytestconfig.getini("python_files") == PYTEST_DEFAULT_FILES


@pytest.mark.parametrize("pattern", PYTEST_INI.get("python_files", PYTEST_DEFAULT_FILES))
def test_agents_md_documents_each_test_file_pattern(pattern: str) -> None:
    assert f"`{pattern}`" in AGENTS


@pytest.mark.parametrize("target", sorted(set(make_calls(AGENTS_CODE))))
def test_agents_md_only_mentions_existing_make_targets(target: str) -> None:
    assert target in MAKE_TARGETS


@pytest.mark.parametrize("target", sorted(set(MAKE_TARGETS) - {"publish"}))  # publishing is for maintainers
def test_agents_md_documents_every_make_target(target: str) -> None:
    assert f"make {target}" in AGENTS_CODE


@pytest.mark.parametrize("selector", sorted(set(re.findall(r"^uv run pytest (\S+)", AGENTS, re.MULTILINE))))
def test_agents_md_pytest_examples_select_existing_tests(selector: str) -> None:
    path, _, name = selector.partition("::")
    assert (ROOT / path).is_file()
    assert not name or re.search(rf"^def {name}\(", (ROOT / path).read_text(encoding="utf-8"), re.MULTILINE)


@pytest.mark.parametrize("path", AGENTS_PATHS)
def test_agents_md_only_mentions_existing_paths(path: str) -> None:
    assert (ROOT / path).exists()


def test_regression_C43_agents_md_warns_about_test_packages_named_after_stdlib_modules() -> None:
    """`cd tests && python -m pytest` still lets tests/numbers shadow the stdlib `numbers` (#32 C43, #39 review)."""
    tests = ROOT / "tests"
    shadowing = sorted(
        p.name for p in tests.iterdir() if (p / "__init__.py").is_file() and p.name in sys.stdlib_module_names
    )
    for name in shadowing:
        assert f"`tests/{name}` package shadows the stdlib `{name}` module" in AGENTS
        assert "Run the tests from the repository root." in AGENTS


def test_agents_md_states_the_supported_python_range() -> None:
    (major, first), *_, (_, last) = classifier_versions()
    assert f"Python {major}.{first}–{major}.{last}" in AGENTS
    assert f"stay {major}.{first}-compatible" in AGENTS


@pytest.mark.parametrize("stale", ["setup.cfg", "requirements.txt", "3.9", "unittest discover -s ./tests"])
def test_agents_md_does_not_mention_the_old_tooling(stale: str) -> None:
    assert stale not in AGENTS
