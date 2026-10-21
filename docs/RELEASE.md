# Release and maintenance runbook

Author: Jason Stys. Release assets are unsigned offline lab applications, not public-hosted services.

## Before pushing or running Actions

Check account Actions billing and available artifact inventory **read-only**. Live artifact bytes are not the same measurement as accrued billing usage; caches are separate. Report the available billing meter and uncertainty to the owner. Do not delete any runs, artifacts or caches without fresh explicit approval and verified archive policy. This repository uses no Actions artifact uploads or dependency caches; direct draft-release assets are a separate mechanism. Do not execute historical archived Actions evidence.

## Source gate

1. Format Python/Rust/web/docs, run lint/strict type checks and regenerate `tools/verify_repo.py --write` indexes. A normal verification run must then pass without writing.
2. Run the native tests, Python branch-inclusive coverage, all browser unit/e2e checks, dependency audits and deterministic benchmark contracts. Investigate drift before deliberately changing a reviewed contract.
3. Build the actual portable application and execute its smoke test. Review source diff, ignored private files and model limitations; never suppress a real test failure to get a green badge.
4. Push reviewed source. Require all eight Validation jobs and both CodeQL language jobs to succeed at the **exact commit**. Inspect open CodeQL alerts separately: a green analysis job does not itself prove zero findings.

## Portable release gate

Manually dispatch **Portable release** with a new `digits.digits.digits` version on main. Preparation requires the latest exact-SHA Validation and CodeQL runs to be successful. It creates a draft, never publishes automatically. Three OS runners build the website and pinned Rust worker, freeze the app, actually run its CLI + SQLite restart + HTTP smoke, and upload a ZIP/checksum pair directly to the draft. Uploads do not overwrite existing assets.

Before publishing:

- Confirm all three platform jobs passed and draft target/tag/main refer to the reviewed source.
- Download all three **newly generated owned-source** ZIP/checksum pairs to a new folder; compare ZIP SHA-256 with its manifest and GitHub asset digest where available.
- Extract and execute the downloaded native bundle on the available local platform; verify a custom input, persisted fresh-worker handoff and SQL history against the reviewed source output. Do not claim local execution on unavailable OSes; their runner smoke tests are separate evidence.
- Review release notes with source SHA, actual workflow links/results, measured test counts and scope limits. Publish the verified draft only after this review.

## Teardown / rollback

Stop only preview/test processes launched for this task and verify their ports are closed. Preserve the final release URL; do not leave an unintended local service running. Retain local evidence and do not clean unrelated app processes or change OS protections.

If a released bug/security issue appears, warn users, remove Latest status as appropriate and fix forward under a new version. Do not silently replace published archives or rewrite existing hashes. No database migration or cloud deployment occurs here. Users can retain an older whole-directory bundle and its separate evidence files; never overwrite their histories/exports during recovery.
