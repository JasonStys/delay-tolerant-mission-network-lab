"""Version, source and immutable draft-release contracts by Jason Stys.

Functions: configuration, source_metadata, release_context, require_checks, prepare, upload.
Variables: ROOT and bounded version/source identities; exact lines: docs/CODE_INDEX.md.
GitHub calls are explicit release-tool operations, never application startup behavior.
"""

import ast
import hashlib
import json
import os
import platform
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")
SHA = re.compile(r"[a-f0-9]{40}")


def require(condition: bool, message: str) -> None:
    """Keep release gates active even when Python optimization disables assertions."""
    if not condition:
        raise ValueError(message)


def configuration() -> dict[str, Any]:
    """Check one explicit portable contract against Python, npm and runtime versions."""
    document = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project, portable = document["project"], document["tool"]["portable"]
    version, name = project["version"], project["name"]
    require(isinstance(version, str) and VERSION.fullmatch(version) is not None, "Invalid version")
    require(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) is not None, "Invalid project name")
    require(re.fullmatch(r"[a-z][a-z0-9_]*", portable["package"]) is not None, "Invalid package")
    require(
        re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", portable["executable"]) is not None,
        "Invalid executable",
    )
    npm = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    require(npm["version"] == version and npm["name"] == name, "Python/npm identity mismatch")
    module = ast.parse((ROOT / portable["package"] / "__init__.py").read_text(encoding="utf-8"))
    declared = [
        ast.literal_eval(node.value)
        for node in module.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets
        )
    ]
    require(declared == [version], "Runtime version mismatch")
    workflows = portable["workflows"]
    require(
        isinstance(workflows, list) and bool(workflows) and len(set(workflows)) == len(workflows),
        "Invalid required workflows",
    )
    require(
        all(
            isinstance(item, str) and re.fullmatch(r"[a-z0-9_-]+\.yml", item) for item in workflows
        ),
        "Invalid workflow filename",
    )
    return {"name": name, "version": version, **portable}


def git(*arguments: str) -> str:
    """Read the local checkout without changing refs, credentials or working files."""
    return subprocess.run(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
    ).stdout.strip()


def source_metadata() -> dict[str, Any]:
    """Label local dirty builds honestly; CI packages require the exact clean workflow SHA."""
    config = configuration()
    sha = git("rev-parse", "HEAD")
    require(SHA.fullmatch(sha) is not None, "Invalid source commit")
    dirty = bool(git("status", "--porcelain"))
    if os.environ.get("GITHUB_ACTIONS") == "true":
        require(
            not dirty and os.environ.get("GITHUB_SHA") == sha, "CI source is not exact and clean"
        )
    return {
        "schema_version": 1,
        "name": config["name"],
        "version": config["version"],
        "source_commit": sha,
        "source_dirty": dirty,
        "platform": platform.system().lower(),
        "machine": platform.machine().lower(),
    }


def gh_json(endpoint: str, *, missing: bool = False) -> Any:
    """Only an explicit HTTP404 means absence; auth/network failures never authorize creation."""
    result = subprocess.run(
        ["gh", "api", endpoint],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    if result.returncode:
        if missing and "(HTTP 404)" in result.stderr:
            return None
        raise RuntimeError("GitHub metadata request failed; no release mutation authorized")
    return json.loads(result.stdout)


def release_context() -> tuple[dict[str, Any], str]:
    """Require main, the configured version and the clean source selected by this workflow."""
    metadata = source_metadata()
    require(not metadata["source_dirty"], "Release checkout is dirty")
    require(os.environ.get("GITHUB_REF") == "refs/heads/main", "Release requires main")
    require(os.environ.get("GITHUB_SHA") == metadata["source_commit"], "Release source mismatch")
    require(os.environ.get("VERSION") == metadata["version"], "Release/software version mismatch")
    repository = f"JasonStys/{metadata['name']}"
    require(os.environ.get("GITHUB_REPOSITORY") == repository, "Unexpected release repository")
    return metadata, repository


def require_checks(metadata: dict[str, Any], repository: str) -> None:
    """Require current main and complete green exact-source runs, including one main push per lane."""
    sha = metadata["source_commit"]
    require(
        gh_json(f"repos/{repository}/git/ref/heads/main")["object"]["sha"] == sha,
        "Main moved; revalidate source",
    )
    for workflow in configuration()["workflows"]:
        envelope = gh_json(
            f"repos/{repository}/actions/workflows/{workflow}/runs?head_sha={sha}&per_page=100"
        )
        runs = envelope["workflow_runs"]
        require(
            bool(runs) and envelope["total_count"] == len(runs) <= 100,
            "Missing/incomplete workflow history",
        )
        for run in runs:
            require(
                run["head_sha"] == sha
                and run["status"] == "completed"
                and run["conclusion"] == "success"
                and run["path"] == f".github/workflows/{workflow}"
                and run["repository"]["full_name"] == repository,
                "Nonpassing or differently sourced workflow",
            )
        require(
            sum(run["event"] == "push" and run["head_branch"] == "main" for run in runs) == 1,
            "Required main push is missing or ambiguous",
        )


def prepare() -> None:
    """Create a fresh draft only; neither public tags nor older drafts are retargeted/reused."""
    metadata, repository = release_context()
    require_checks(metadata, repository)
    tag = f"v{metadata['version']}"
    require(
        gh_json(f"repos/{repository}/git/ref/tags/{tag}", missing=True) is None,
        "Version tag already exists",
    )
    require(
        gh_json(f"repos/{repository}/releases/tags/{tag}", missing=True) is None,
        "Release version already exists",
    )
    subprocess.run(
        [
            "gh",
            "release",
            "create",
            tag,
            "--repo",
            repository,
            "--target",
            metadata["source_commit"],
            "--draft",
            "--title",
            f"{configuration()['title']} {tag}",
            "--notes",
            "Unsigned portable applications by Jason Stys. Windows ZIP; Linux/macOS tar.gz. Extract the full archive, verify SHA-256 and read RELEASE.json. Educational synthetic software, not operational equipment. Draft only: publish after all three extracted-native journeys and exact asset checks pass.",
        ],
        cwd=ROOT,
        check=True,
        timeout=30,
    )


def asset_paths(metadata: dict[str, Any]) -> tuple[Path, Path]:
    """Version, OS and CPU are explicit; unrelated previous dist output is never uploaded."""
    system, machine = metadata["platform"], metadata["machine"]
    require(system in {"windows", "linux", "darwin"}, "Unsupported platform")
    require(re.fullmatch(r"[a-z0-9_]+", machine) is not None, "Invalid CPU identity")
    stem = f"{metadata['name']}-v{metadata['version']}-{system}-{machine}"
    suffix = ".zip" if system == "windows" else ".tar.gz"
    return ROOT / "dist" / (stem + suffix), ROOT / "dist" / (stem + ".sha256")


def upload() -> None:
    """Upload only an exact source/version archive pair to its unchanged draft, never replace assets."""
    if __package__:
        from .portable_archive import archive_metadata
    else:
        from portable_archive import archive_metadata
    metadata, repository = release_context()
    tag = f"v{metadata['version']}"
    release = gh_json(f"repos/{repository}/releases/tags/{tag}")
    require(
        release["draft"] is True
        and release["tag_name"] == tag
        and release["target_commitish"] == metadata["source_commit"],
        "Draft target/source mismatch",
    )
    require(
        gh_json(f"repos/{repository}/git/ref/tags/{tag}", missing=True) is None,
        "Version tag already exists",
    )
    archive, checksum = asset_paths(metadata)
    require(archive.is_file() and checksum.is_file(), "Missing versioned archive/checksum")
    with archive.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    require(
        checksum.read_text(encoding="utf-8") == f"{digest}  {archive.name}\n",
        "Archive checksum mismatch",
    )
    require(
        archive_metadata(archive, configuration()["executable"]) == metadata,
        "Archive source metadata mismatch",
    )
    require(
        not {archive.name, checksum.name} & {item["name"] for item in release["assets"]},
        "Asset already exists; no overwrite permitted",
    )
    subprocess.run(
        ["gh", "release", "upload", tag, "--repo", repository, str(archive), str(checksum)],
        cwd=ROOT,
        check=True,
        timeout=180,
    )
