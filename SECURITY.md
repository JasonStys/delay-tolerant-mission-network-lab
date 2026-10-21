# Security and responsible reporting

Author: Jason Stys. This is an offline educational lab, not a production multiuser or mission system.

## Boundaries

- Loopback-only read-only HTTP with exact Host and same-origin/Fetch Metadata checks; no CORS, account forms, uploads, remote fetches or mutation API.
- A restrictive Content Security Policy permits local built assets, not inline/eval/remote scripts; framing, content sniffing and referrer controls are set. No analytics, ads, external fonts or automatic telemetry.
- Strict finite browser settings; local JSON imports reject duplicate keys, coercions, excessive size and unsupported fields. Assets cannot traverse paths or follow symlinks out of their root.
- Payload bytes remain opaque. HTML output escapes all evidence; CSV contains numeric samples. Native process paths are fixed, shell execution is not used, and input cannot select commands or URLs.
- Rust forbids unsafe code and uses checked bounded parsing, release overflow checks and explicit checkpoint validation. CRC and report hashes are **not authentication**, encryption or signatures.
- Optional SQLite/history/exports are deliberately unencrypted local user-owned data. Git ignores databases, keys, environments, dependency trees and builds. Nothing uploads them automatically.

These controls do not protect against a compromised OS, malicious local executable replacement, a local user reading files, hostile browser extensions or unlimited concurrent local requests. The Python development service lacks public-hosting authentication, rate limits, TLS and tenant isolation. Do not bind/proxy it to a public or shared network, feed it confidential material, or connect it to real systems.

## Supply chain and downloads

Python development packages use exact hashed locks; npm uses an integrity lock; Rust has no external crates. CI actions are pinned to commit SHAs, checkout credentials are not persisted, and job permissions are minimized. CodeQL covers Python and JavaScript/TypeScript, **not Rust**. Audits and scans are point-in-time checks, not proof of absence of vulnerabilities.

Portable downloads are unsigned. Verify the SHA-256 file against the ZIP; that detects corruption, not a compromised release publisher. Release preparation requires exact-commit successful Validation and CodeQL runs; a reviewer must additionally check security alerts and downloaded bundle behavior before publishing. Never bypass browser/OS security warnings. Runtime notices ship with each whole-directory bundle.

## Reporting

For ordinary non-sensitive defects, open a [project issue](https://github.com/JasonStys/delay-tolerant-mission-network-lab/issues). Do **not** post credentials, personal data, private payloads, local account paths or exploit-ready secrets. Use GitHub's private vulnerability reporting if it is available for this repository; otherwise contact the maintainer through the [public profile](https://github.com/JasonStys) to arrange a private channel before sending details. No private channel availability is promised here.

Only the latest reviewed source/release is maintained. If a release is found unsafe, stop using it, retain evidence, remove its Latest designation or mark the release warning, fix forward, and publish a new version; do not silently replace existing assets.
