"""Build portable native bundles from reviewed source by Jason Stys.

Function: main. Variables: root, slug, executable, PyInstaller command, zip manifest.
Generated bundles are unsigned; exact symbols: docs/CODE_INDEX.md. No installer/elevation.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from importlib.metadata import distribution
from pathlib import Path

if __package__:
    from .portable_archive import archive_metadata, create_archive, extract_archive
    from .release_contract import ROOT, asset_paths, configuration, require, source_metadata
else:
    from portable_archive import archive_metadata, create_archive, extract_archive
    from release_contract import ROOT, asset_paths, configuration, require, source_metadata


def main() -> int:
    """Freeze production assets with required notices, then accept a safely extracted archive."""
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Build and accept the extracted portable application"
    )
    parser.add_argument("--output-root", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    config, metadata = configuration(), source_metadata()
    generated = root / ".runtime/package-meta"
    generated.mkdir(parents=True, exist_ok=True)
    identity = generated / "RELEASE.json"
    identity.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    if not (root / "web/dist/index.html").is_file():
        raise SystemExit("Run npm ci and npm run build first")
    worker = (
        root
        / "target/release"
        / ("network-core.exe" if sys.platform == "win32" else "network-core")
    )
    if not worker.is_file():
        raise SystemExit("Run cargo build --release --locked first")
    rust_root = Path(
        subprocess.check_output(["rustc", "--print", "sysroot"], text=True, timeout=30).strip()
    )
    rust_notices = rust_root / "share/doc/rust"
    if not (rust_notices / "COPYRIGHT-library.html").is_file():
        raise SystemExit("Install pinned rust-docs component to include standard-library notices")
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--console",
        "--name",
        "MissionNetworkLab",
        "--add-data",
        "web/dist:web/dist",
        "--add-data",
        "dtnlab/resources:dtnlab/resources",
        "--add-data",
        "LICENSE:licenses/project",
        "--add-data",
        "licenses/PYTHON.txt:licenses/python",
        "--add-data",
        "licenses/RUST-MIT.txt:licenses/rust",
        "--add-data",
        "licenses/RUST-APACHE.txt:licenses/rust",
        "--add-data",
        str(rust_notices / "COPYRIGHT-library.html") + ":licenses/rust",
        "--add-data",
        str(rust_notices / "licenses") + ":licenses/rust/licenses",
        "--add-binary",
        str(worker) + ":native",
        "--add-data",
        "docs/THIRD_PARTY.md:docs",
        "--add-data",
        "node_modules/vite/LICENSE.md:licenses/vite",
        "launcher.py",
    ]
    distribution_info = distribution("pyinstaller")
    notices = [
        distribution_info.locate_file(path)
        for path in (distribution_info.files or [])
        if str(path).endswith("licenses/COPYING.txt")
    ]
    if len(notices) != 1:
        raise SystemExit("Expected the locked PyInstaller distribution license")
    command[command.index("launcher.py") : command.index("launcher.py")] = [
        "--add-data",
        str(notices[0]) + ":licenses/pyinstaller",
    ]
    command[command.index("launcher.py") : command.index("launcher.py")] = [
        "--add-data",
        str(identity) + ":dtnlab/resources",
    ]
    subprocess.run(command, cwd=root, check=True, timeout=600)
    executable_name = config["executable"]
    bundle = root / "dist" / executable_name
    shutil.copyfile(identity, bundle / "RELEASE.json")
    archive, checksum = asset_paths(metadata)
    archive, checksum = (
        args.output_root.resolve() / archive.name,
        args.output_root.resolve() / checksum.name,
    )
    archive.parent.mkdir(parents=True, exist_ok=True)
    require(not checksum.exists(), "Checksum destination already exists")
    create_archive(bundle, archive)
    require(
        archive_metadata(archive, executable_name) == metadata, "Created archive identity mismatch"
    )
    with tempfile.TemporaryDirectory(
        prefix="delay-tolerant-mission-network-lab-extracted-"
    ) as temporary:
        extracted = extract_archive(archive, Path(temporary) / "unpacked", executable_name)
        executable = extracted / (executable_name + (".exe" if sys.platform == "win32" else ""))
        subprocess.run(
            [sys.executable, str(root / "tools/smoke_app.py"), str(executable)],
            cwd=temporary,
            check=True,
            timeout=120,
        )
    with archive.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    print(f"Extracted portable application passed: {archive.name} SHA-256 {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
