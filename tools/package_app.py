"""Build portable native bundles from reviewed source by Jason Stys.

Function: main. Variables: root, slug, executable, PyInstaller command, zip manifest.
Generated bundles are unsigned; exact symbols: docs/CODE_INDEX.md. No installer/elevation.
"""

import hashlib
import platform
import shutil
import subprocess
import sys
from importlib.metadata import distribution
from pathlib import Path


def main() -> int:
    """Freeze the existing production web build, smoke it, then zip this platform's bundle."""
    root = Path(__file__).resolve().parents[1]
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
    subprocess.run(command, cwd=root, check=True, timeout=600)
    executable = (
        root
        / "dist/MissionNetworkLab"
        / ("MissionNetworkLab.exe" if sys.platform == "win32" else "MissionNetworkLab")
    )
    subprocess.run(
        [sys.executable, "tools/smoke_app.py", str(executable)], cwd=root, check=True, timeout=90
    )
    slug = f"delay-tolerant-mission-network-lab-{platform.system().lower()}-{platform.machine().lower()}"
    archive = Path(
        shutil.make_archive(str(root / "dist" / slug), "zip", root / "dist", "MissionNetworkLab")
    )
    with archive.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    (root / "dist" / f"{slug}.sha256").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    print(f"Portable bundle verified: {archive.name} SHA-256 {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
