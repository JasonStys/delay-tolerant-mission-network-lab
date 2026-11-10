# Portable application and release runbook

Maintained by Jason Stys. Delay Tolerant Mission Network Lab is an unsigned educational desktop application,
not a production hosted service, signed installer or real-equipment controller.

## Download, extract and launch

Use the official [repository releases](https://github.com/JasonStys/delay-tolerant-mission-network-lab/releases).
Version 1.1 uses a versioned **Windows ZIP** or **Linux/macOS tar.gz**, plus an adjacent
SHA-256 file. Older published assets remain immutable and may predate current features.

1. Select the correct CPU/OS build and compare its SHA-256 with the sidecar. On Windows,
   `Get-FileHash -Algorithm SHA256` computes the digest; on Linux/macOS use `sha256sum`
   or `shasum -a 256`. A checksum identifies bytes, not publisher authenticity or safety.
2. Extract into a new user-owned folder. Windows users extract the whole ZIP. On Linux/macOS,
   use a tar-aware extractor such as `tar -xzf <archive.tar.gz>`; tar preserves PyInstaller's
   relative internal links and executable permissions. Do not flatten the archive, run from
   inside it or separate the executable from `_internal` and its license notices.
3. Inspect `MissionNetworkLab/RELEASE.json`. Its name, version, source commit, platform,
   CPU and clean/dirty status must agree with the chosen release. Published builds require
   `source_dirty: false`; a local dirty development build is not exact-source release proof.
4. Open `MissionNetworkLab.exe` on Windows, or `./MissionNetworkLab` on Linux/macOS.
   The launcher opens your normal browser on a private ephemeral `127.0.0.1` port. Keep its
   console open; Ctrl+C stops that process. No compiler, Python/Node setup, Docker, account,
   administrator elevation or public host is required for the portable application.

The targets are desktop Windows x64, Linux x64 and macOS arm64 under their tested runner
conditions, not every OS version or a native mobile installation. Builds are unsigned and
unnotarized. Respect OS/organization policy; never disable security controls to run them.
Keep user-created histories and exports separate from installation folders. Local report
histories are not encrypted account stores. Preserve original model/data/provenance limits.

## Source and package acceptance

Before pushing or invoking Actions, inspect storage/billing read-only and report available
usage with its uncertainty. Artifact bytes, accrued billing usage and caches are different
measurements. Do not delete runs, artifacts or caches without fresh explicit authorization.
These workflows do not upload Actions artifacts or dependency caches.

Run formatting, strict types, source inventories, independent model/native tests, Python
branch-inclusive coverage, browser unit/journey tests and dependency audits. Do not refresh
reference results merely to hide a failure. Preserve numerical/model contracts and user data.

The portable build freezes reviewed production UI/resources, writes source/version metadata,
creates the native archive and checksum, then inspects and extracts it into a fresh temporary
folder. Its actual extracted executable must complete CLI/resource checks, owned health/version
proof, real built JavaScript/CSS delivery and the new-feature Chromium/API/export journey.
No source-server substitution, mocked successful HTTP response or unrelated existing service
can establish native acceptance. All owned test processes and browser contexts must close.
A package launch is not clean-machine installer certification, signing or notarization.

## Draft-only publication

Dispatch **Portable release** on main with version `1.1.0` only after that exact clean source
passes every configured Validation/CodeQL lane. Python, npm and runtime versions must agree.
The conservative gate rejects missing, active, failed, foreign or ambiguous exact-source runs,
and confirms current main before creating a **new draft**. Existing tags/releases are rejected;
never retarget or reuse published assets.

All three OS jobs build and test extracted native bundles. Upload requires the same draft
source/version, complete embedded metadata, exact archive digest and no existing same-name
asset. Release assets go directly to the draft, not Actions storage. No step publishes it.

Before publication, verify all three native jobs and exact source checks, every archive's
sidecar and GitHub asset digest, expected platform set and release notes. Download and test
only newly built/reviewed assets, never historical archived Actions evidence. Record local
execution separately from unavailable OSes' hosted evidence. Successful CodeQL execution
does not by itself establish zero open security findings.

## Teardown and recovery

Stop only the test/preview processes you created. Do not kill unknown services, overwrite
histories or modify OS security. Keep old whole-directory bundles for rollback. Fix published
bugs under a fresh version; do not silently replace archives, hashes or old release tags.

## Authenticated draft lookup

GitHub's release-by-tag REST endpoint is for published releases, so a draft's tag returning
404 does not establish absence. `tools/draft_lookup.py` completely lists visible releases
within a three-page/100-per-page cap, rejects ambiguity, then rereads a unique numeric ID.
Incomplete histories, API failures and changed identity fail closed. Preparation rejects any
existing version; upload requires the exact-source unpublished draft plus the original
archive, digest and no-overwrite checks. See the portable release report for the observed
API failure, correction and independent regression cases.
