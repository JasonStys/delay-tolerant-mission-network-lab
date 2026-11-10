# Portable 1.1 release validation — 2026-11-09

Author: Jason Stys. This report describes observed local validation and the source contract
for the next portable release. It does not claim hosted results before those workflows run.

## Purpose and implementation

The published1.0 portable artifacts predate the latest practical workflow. Version1.1 makes
product identity consistent across Python, npm/lock metadata, the running service and UI.
`RELEASE.json` binds a bundle to its declared source, version, platform and clean/dirty state.
Older published releases and users' histories are preserved.

Packaging now checks the actual **freshly extracted** application from a new temporary working
directory. The earlier pre-archive-only smoke did not prove that extraction retained native
links or execute bits. Windows uses ZIP; Linux/macOS use tar.gz. Bounded archive tests reject
traversal, aliases, duplicate members, escaping links, wrong types and excessive content.

The stdlib release guard checks coherent versions, exact clean workflow source, current main,
complete successful required runs and a fresh draft/tag. Upload checks that unchanged draft's
source/version, embedded metadata, actual digest and absent same-name assets. It cannot replace
published assets. These guards remain active with Python optimization. Privileged release
jobs still have job-level contents-write permission; the GH token is supplied only to explicit
transport steps. No application startup calls GitHub or transmits user data.

## Actual new-feature acceptance

Complete-run message waterfalls, causal replay separation, corruption and an empty network. Native and reference traces agree; queue plus in-flight ticks reconcile with observed elapsed time. The actual downloaded JSON preserves the reviewed waterfall. Preserved checks exercise fresh-process recovery, committed checkpoint SQLite and bundled Rust/runtime notices.

The compiled child must announce its owned ephemeral loopback URL and echo the random smoke
marker, runtime version and exact embedded metadata. Probes refuse redirects/proxies, enforce
bounded HTTP reads and fetch real built JavaScript/CSS. An owned Chromium context uses the
compiled service, blocks outside-origin resources, rejects browser errors and exercises the
new feature. Original domain-native checks remain in `tools/legacy_smoke.py` under guards
that are active with `python -O`; they were not discarded when the new browser journey was added.

## Observed local results

Windows/Python3.14.6 and Node24.18.1, using each repository's isolated locked environment:

| Gate                                                                     | Observed result                                       |
| ------------------------------------------------------------------------ | ----------------------------------------------------- |
| Complete Python/model/native/HTTP suite                                  | 384 passed; 99.75% combined statement/branch coverage |
| Focused release/archive/frozen-identity negative cases                   | 70 passed, included in the complete suite above       |
| Existing TypeScript unit suite                                           | 12 passed                                             |
| Strict TypeScript/Vite production build                                  | Passed                                                |
| Ruff lint/format and strict domain mypy                                  | Passed                                                |
| Fresh frozen Windows archive extraction + actual CLI/API/Chromium/export | Passed                                                |
| Original native notices/resource/persistence checks                      | Passed                                                |
| Independent ZIP CRC, sidecar, app executable and metadata inspection     | Passed                                                |

Observed local dirty-build archive (not a published or exact-clean CI artifact):

- File:`delay-tolerant-mission-network-lab-v1.1.0-windows-amd64.zip`
- Bytes:11660357; members:106
- SHA-256:`2e2ee1ae63f719657e75e8ed05899a9b855bbdaa4b6c297e1daf8da6c12bd1d0`
- Embedded source:`4df5db2092226c2b1093413215b06d6d76c2b362` with `source_dirty:true`.

The dirty flag is intentional for local pre-commit acceptance. A release requires a fresh
clean CI build at its accepted commit; this local checksum must not be presented as that
future release's checksum. No Linux/macOS native execution is claimed from this Windows run.
Their required hosted native jobs separately rebuild, extract and exercise each platform.

## Failures investigated and corrected

Restricted-shell HTTP tests failed with WinError10013 before reaching disposable listeners.
The unchanged suites passed in normal-user loopback scope; no warning or coverage gate was
weakened. The local Rust driver uses the existing explicit pinned toolchain rather than
assuming Windows subprocess lookup honors a child-only PATH.

New acceptance initially retained Flight-specific nominal/reset/240-tick checks from the
shared pilot, which are not APIs of this application. Those were replaced by this domain's
new-feature oracle and its preserved original smoke. The authored HTML title, not the release
display title, identifies compiled HTML. Sensor/Reactor button lookup used the existing
accessible names including their arrow decoration. Failures were not accepted as passes;
corrected checks ran against fresh extracted artifacts. Private failed evidence remains
outside the repository. No application numerical algorithm was changed to satisfy the harness.

Chromium dependency installation has a15-minute setup budget inside a25-minute native job,
based on observed hosted setup duration. Actual CLI30-second, HTTP8-second, browser45-second
and complete extracted-smoke120-second hard deadlines remain bounded, without test retries.

## Scope and limitations

Invented bounded topology and logical ticks; no real radios, BPv7/BPSec interoperability, exactly-once networking or operational routing.

These are unsigned/unnotarized desktop portable packages, not signed installers, public
hosting, native mobile installation or clean-machine installer certification. Local histories
are unencrypted files under the user's control. Hashes identify bytes, not authorship or truth.
No user store, real equipment, account or OS security setting was changed by validation.
