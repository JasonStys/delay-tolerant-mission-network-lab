"""Independent release/source/archive authorization cases by Jason Stys.

Functions: fixtures and test_*; variables: fake GH metadata and synthetic bytes, never credentials.
All remote calls are substituted; archive bytes are real. Exact lines: docs/CODE_INDEX.md.
"""

import copy
import hashlib
import json
import subprocess
import zipfile

import pytest

from tools import portable_archive as archives
from tools import release_contract as release
from tools.smoke_app import RefuseRedirects

SOURCE = "a" * 40
METADATA = {
    "schema_version": 1,
    "name": "delay-tolerant-mission-network-lab",
    "version": "1.1.0",
    "source_commit": SOURCE,
    "source_dirty": False,
    "platform": "windows",
    "machine": "amd64",
}
REPOSITORY = "JasonStys/delay-tolerant-mission-network-lab"


def run_record(workflow):
    """Independent complete GitHub response fields, not implementation-created run objects."""
    return {
        "head_sha": SOURCE,
        "status": "completed",
        "conclusion": "success",
        "event": "push",
        "head_branch": "main",
        "path": ".github/workflows/" + workflow,
        "repository": {"full_name": REPOSITORY},
    }


@pytest.fixture
def context(monkeypatch):
    """An isolated authorized release context without inspecting environment credentials."""
    monkeypatch.setattr(release, "source_metadata", lambda: copy.deepcopy(METADATA))
    for key, value in {
        "VERSION": "1.1.0",
        "GITHUB_SHA": SOURCE,
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_REPOSITORY": REPOSITORY,
    }.items():
        monkeypatch.setenv(key, value)


def test_product_versions_are_coherent():
    """Current runtime/npm/lock product identity agree; native browser verifies the built UI version."""
    config = release.configuration()
    assert config["version"] == "1.1.0"
    lock = json.loads((release.ROOT / "package-lock.json").read_text())
    assert lock["version"] == lock["packages"][""]["version"] == config["version"]


def test_native_http_probe_refuses_redirects_before_following():
    """Even a valid-looking local redirect cannot make the smoke issue an outside HTTP request."""
    with pytest.raises(ValueError, match="refuses redirects"):
        RefuseRedirects().redirect_request(
            None, None, 302, "redirect", {}, "https://outside.invalid"
        )


@pytest.mark.parametrize(
    "kind",
    [
        "invalid-version",
        "npm-mismatch",
        "runtime-mismatch",
        "dynamic-runtime",
        "duplicate-workflow",
        "package-escape",
    ],
)
def test_configuration_refuses_incoherent_or_unsafe_version_sources(tmp_path, monkeypatch, kind):
    """Independent source files cannot authorize a version by evaluating code or escaping the package."""
    portable = '[tool.portable]\npackage="example"\nexecutable="Example"\nworkflows=["validate.yml","codeql.yml"]\n'
    project = '[project]\nname="example-project"\nversion="1.1.0"\n'
    npm = {"name": "example-project", "version": "1.1.0"}
    runtime = '__version__ = "1.1.0"\n'
    if kind == "invalid-version":
        project = project.replace('"1.1.0"', '"01.1.0"')
    elif kind == "npm-mismatch":
        npm["version"] = "1.0.0"
    elif kind == "runtime-mismatch":
        runtime = '__version__ = "1.0.0"\n'
    elif kind == "dynamic-runtime":
        runtime = '__version__ = str("1.1.0")\n'
    elif kind == "duplicate-workflow":
        portable = portable.replace('"codeql.yml"', '"validate.yml"')
    elif kind == "package-escape":
        portable = portable.replace('package="example"', 'package="../outside"')
    (tmp_path / "pyproject.toml").write_text(project + portable)
    (tmp_path / "package.json").write_text(json.dumps(npm))
    (tmp_path / "example").mkdir()
    (tmp_path / "example/__init__.py").write_text(runtime)
    monkeypatch.setattr(release, "ROOT", tmp_path)
    with pytest.raises(ValueError):
        release.configuration()


@pytest.mark.parametrize(
    "field,value",
    [
        ("VERSION", "1.0.0"),
        ("GITHUB_SHA", "b" * 40),
        ("GITHUB_REF", "refs/heads/feature"),
        ("GITHUB_REPOSITORY", "AnotherOwner/other"),
    ],
)
def test_release_context_refuses_mismatched_identity(context, monkeypatch, field, value):
    """Main, repository, source and software version are independent authorization requirements."""
    monkeypatch.setenv(field, value)
    with pytest.raises(ValueError):
        release.release_context()


def test_source_metadata_labels_local_dirty_build_and_refuses_ci_mismatch(monkeypatch):
    """Local dirty evidence is explicit; the same state can never label a clean CI release."""
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setattr(
        release, "git", lambda *args: SOURCE if args[0] == "rev-parse" else " M source.py"
    )
    assert release.source_metadata()["source_dirty"] is True
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_SHA", SOURCE)
    with pytest.raises(ValueError, match="exact and clean"):
        release.source_metadata()
    monkeypatch.setattr(release, "git", lambda *args: SOURCE if args[0] == "rev-parse" else "")
    monkeypatch.setenv("GITHUB_SHA", "b" * 40)
    with pytest.raises(ValueError, match="exact and clean"):
        release.source_metadata()


def test_explicit_http404_only_is_absence(monkeypatch):
    """Authentication/network failures cannot be mistaken for an unused release version."""
    for message in ["Forbidden (HTTP 403)", "network unavailable", "Not Found but no HTTP status"]:
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, message=message, **k: subprocess.CompletedProcess([], 1, "", message),
        )
        with pytest.raises(RuntimeError):
            release.gh_json("repos/owned/path", missing=True)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess([], 1, "", "Not Found (HTTP 404)"),
    )
    assert release.gh_json("repos/owned/path", missing=True) is None
    with pytest.raises(RuntimeError):
        release.gh_json("repos/owned/path")


@pytest.mark.parametrize(
    "field,value",
    [
        ("head_sha", "b" * 40),
        ("status", "in_progress"),
        ("conclusion", "failure"),
        ("event", "workflow_dispatch"),
        ("head_branch", "feature"),
        ("path", ".github/workflows/unrelated.yml"),
        ("repository", {"full_name": "Other/repo"}),
    ],
)
def test_prerequisite_runs_cannot_false_pass(context, monkeypatch, field, value):
    """A successful label alone is insufficient when source/event/branch/status disagree."""

    def response(endpoint):
        """Return one independently invalid run while retaining the main identity fixture."""
        if endpoint.endswith("heads/main"):
            return {"object": {"sha": SOURCE}}
        workflow = endpoint.split("/workflows/")[1].split("/")[0]
        run = run_record(workflow)
        run[field] = value
        return {"total_count": 1, "workflow_runs": [run]}

    monkeypatch.setattr(release, "gh_json", response)
    with pytest.raises(ValueError):
        release.require_checks(METADATA, REPOSITORY)


@pytest.mark.parametrize(
    "kind", ["empty", "incomplete", "duplicate", "newer-running", "main-moved"]
)
def test_missing_ambiguous_or_unfinished_workflow_history_is_not_selected_away(
    context, monkeypatch, kind
):
    """No fallback to an older green run conceals a missing/current/ambiguous prerequisite."""

    def response(endpoint):
        """Provide bounded workflow history with one deliberate independent fault."""
        if endpoint.endswith("heads/main"):
            return {"object": {"sha": "b" * 40 if kind == "main-moved" else SOURCE}}
        workflow = endpoint.split("/workflows/")[1].split("/")[0]
        runs = [run_record(workflow)]
        if kind == "empty":
            runs = []
        if kind in {"duplicate", "newer-running"}:
            runs.append(run_record(workflow))
        if kind == "newer-running":
            runs[-1].update(status="in_progress", conclusion=None, event="workflow_dispatch")
        return {"total_count": len(runs) + (kind == "incomplete"), "workflow_runs": runs}

    monkeypatch.setattr(release, "gh_json", response)
    with pytest.raises(ValueError):
        release.require_checks(METADATA, REPOSITORY)


@pytest.mark.parametrize("existing", ["tag", "public-release", "old-draft"])
def test_prepare_never_retargets_or_reuses_an_existing_version(context, monkeypatch, existing):
    """Even an unpublished draft is preserved; author chooses a reviewed fresh version instead."""
    monkeypatch.setattr(release, "require_checks", lambda *args: None)

    def response(endpoint, *, missing=False):
        """Explicit occupied tag or release responses; no process may mutate them."""
        if "/git/ref/tags/" in endpoint:
            return {"object": {"sha": SOURCE}} if existing == "tag" else None
        return {"draft": existing == "old-draft", "target_commitish": "b" * 40}

    monkeypatch.setattr(release, "gh_json", response)

    def forbidden(*args, **kwargs):
        """Any write process here proves the guard failed."""
        pytest.fail("Existing release/tag must not trigger a write")

    monkeypatch.setattr(subprocess, "run", forbidden)
    with pytest.raises(ValueError):
        release.prepare()


def test_prepare_creates_only_exact_version_source_draft(context, monkeypatch):
    """Literal arguments bind the new draft to reviewed SHA without publishing flags."""
    monkeypatch.setattr(release, "require_checks", lambda *args: None)
    monkeypatch.setattr(release, "gh_json", lambda *args, **kwargs: None)
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda argv, **kwargs: calls.append(argv))
    release.prepare()
    assert len(calls) == 1 and calls[0][:4] == ["gh", "release", "create", "v1.1.0"]
    assert calls[0][calls[0].index("--target") + 1] == SOURCE
    assert "--draft" in calls[0] and "--clobber" not in calls[0]


@pytest.mark.parametrize("conclusion", ["success", "failure"])
def test_prepare_requires_prerequisites_before_creating(context, monkeypatch, conclusion):
    """Integrated fake GH replies prove actual prerequisite evaluation precedes mutation."""
    queried, writes = [], []

    def response(endpoint, *, missing=False):
        """Return independent branch/runs/absence endpoints without replacing the gate itself."""
        queried.append(endpoint)
        if endpoint.endswith("heads/main"):
            return {"object": {"sha": SOURCE}}
        if "/actions/workflows/" in endpoint:
            workflow = endpoint.split("/workflows/")[1].split("/")[0]
            run = run_record(workflow)
            run["conclusion"] = conclusion
            return {"total_count": 1, "workflow_runs": [run]}
        return None

    monkeypatch.setattr(release, "gh_json", response)
    monkeypatch.setattr(subprocess, "run", lambda argv, **kwargs: writes.append(argv))
    if conclusion == "success":
        release.prepare()
        assert len(writes) == 1
        assert all(
            any(f"/workflows/{name}/" in query for query in queried)
            for name in ["validate.yml", "codeql.yml"]
        )
    else:
        with pytest.raises(ValueError):
            release.prepare()
        assert writes == []


@pytest.fixture
def upload_fixture(context, tmp_path, monkeypatch):
    """Real small versioned ZIP/checksum; fixture bytes are never launched."""
    config = release.configuration()
    monkeypatch.setattr(release, "ROOT", tmp_path)
    monkeypatch.setattr(release, "configuration", lambda: config)
    bundle = tmp_path / config["executable"]
    bundle.mkdir()
    (bundle / "RELEASE.json").write_text(json.dumps(METADATA))
    (bundle / "example.txt").write_text("Synthetic archive bytes")
    (tmp_path / "dist").mkdir()
    archive, checksum = release.asset_paths(METADATA)
    archives.create_archive(bundle, archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    info = {"draft": True, "tag_name": "v1.1.0", "target_commitish": SOURCE, "assets": []}
    monkeypatch.setattr(
        release, "gh_json", lambda endpoint, **kwargs: None if "/git/ref/" in endpoint else info
    )
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda argv, **kwargs: calls.append(argv))
    return info, archive, checksum, calls


@pytest.mark.parametrize(
    "kind",
    [
        "public",
        "wrong-sha",
        "wrong-tag",
        "collision",
        "checksum",
        "metadata",
        "wrong-source-metadata",
    ],
)
def test_upload_refuses_wrong_draft_or_bytes(upload_fixture, kind):
    """Published/mismatched targets and stale/tampered assets never reach an upload process."""
    info, archive, checksum, calls = upload_fixture
    if kind == "public":
        info["draft"] = False
    elif kind == "wrong-sha":
        info["target_commitish"] = "b" * 40
    elif kind == "wrong-tag":
        info["tag_name"] = "v1.0.0"
    elif kind == "collision":
        info["assets"] = [{"name": archive.name}]
    elif kind == "checksum":
        checksum.write_text("0" * 64 + f"  {archive.name}\n")
    elif kind == "metadata":
        archive.write_bytes(b"Not an archive")
        checksum.write_text(
            hashlib.sha256(archive.read_bytes()).hexdigest() + f"  {archive.name}\n"
        )
    elif kind == "wrong-source-metadata":
        bundle = archive.parent.parent / release.configuration()["executable"]
        (bundle / "RELEASE.json").write_text(json.dumps({**METADATA, "source_commit": "b" * 40}))
        archive.unlink()
        archives.create_archive(bundle, archive)
        checksum.write_text(
            hashlib.sha256(archive.read_bytes()).hexdigest() + f"  {archive.name}\n"
        )
    with pytest.raises((ValueError, OSError, zipfile.BadZipFile)):
        release.upload()
    assert calls == []


def test_upload_uses_only_expected_pair_without_clobber(upload_fixture):
    """Other dist files cannot hitchhike into the release upload."""
    _, archive, checksum, calls = upload_fixture
    (archive.parent / "unrelated-private.txt").write_text("must not upload")
    release.upload()
    assert len(calls) == 1 and calls[0][-2:] == [str(archive), str(checksum)]
    assert "--clobber" not in calls[0]
