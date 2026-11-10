# Documentation refresh — 2026-11-09

By Jason Stys.

This documentation-only edition describes source `df32f632dc89a329cfdd4eaf9c9f7b7248f8f5ac`. It does not change application behavior, accounts, private data, installers or published releases.

## Published editions and completed review

| File                                                 | Bytes | SHA-256                                                            | Reviewed scope                                                                                                                      |
| ---------------------------------------------------- | ----: | ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| [project-guide.docx](project-guide.docx)             | 75574 | `549e724615e395421f8ef32cf14aa7582d81f53c0db52cced4566bfa7e70bef1` | 5 pages, each viewed individually                                                                                                   |
| [validation-review.docx](validation-review.docx)     | 43747 | `08acc6ff81578a1ed0c74550c0e90f00e5a00a563506d4330e2332ed821cfca2` | 4 pages, each viewed individually                                                                                                   |
| [validation-evidence.xlsx](validation-evidence.xlsx) |  7385 | `ad0404f7926bc193373af618d0255822c786942fd50771cf17709550b906cd74` | Both tab previews; two actual Excel Tables/autoFilters; four formulas; failure-change/restore recalculation and zero formula errors |

Word review checked plain black titles, readable pagination, whole table rows, source references, practical limits and absence of clipping or overflow. Render receipts were matched to the current DOCX digest before approval. Workbook review inspected both tab previews and actual exported Table/autoFilter elements; recalculated success/failure summaries were compared independently with workflow metadata. Static previews do not draw Excel dropdown arrows; the exported workbook contains the actual filters.

## Evidence and change boundary

- Functional baseline: `df32f632dc89a329cfdd4eaf9c9f7b7248f8f5ac`.
- Workflow observation: `2026-11-10T05:25:40.628667+00:00`; exact run URLs and source identities remain in [publications.json](publications.json).
- Local document-package validation verifies exact copied bytes, Office ZIP integrity, approved page/tab identities and internal documentation links. Repository-specific documentation and source-policy commands are run separately and recorded in the integration handoff.
- Source/index metadata is regenerated using the repository’s existing tools. Existing privacy, security, coverage and workflow gates are retained.
- PR and later main workflows must pass independently. This record does not claim future or unrun integration CI success.

## Interpretation

The Word files document the cited source; dated source reports retain their original execution scope. A passing workflow is distinct from completed analysis with zero findings, and neither establishes production suitability. The Excel source inventory is not a per-test execution report. Checksums identify exact bytes, not a signature or publisher attestation.

Use the [handbook](../handbook.md) to choose usage, design, security and test documentation. Keep editable Markdown and reviewed editions together; do not replace historical measurements with undated claims.

## Integration-local checks

Observed at `2026-11-10T07:48:38.845410+00:00` on Windows with this repository’s existing development tools. Python commands use its isolated development environment. The documentation source baseline remains the immutable revision above; these checks validate this documentation integration locally.

| Command                                                        | Observed result |
| -------------------------------------------------------------- | --------------- |
| `python tools/verify_repo.py --write`                          | Passed, exit 0. |
| `python tools/verify_repo.py`                                  | Passed, exit 0. |
| `python -m ruff check dtnlab tests tools launcher.py`          | Passed, exit 0. |
| `python -m ruff format --check dtnlab tests tools launcher.py` | Passed, exit 0. |
| `python -m mypy dtnlab`                                        | Passed, exit 0. |
| `python -m pytest --cov=dtnlab --cov-report=term-missing`      | Passed, exit 0. |
| `node node_modules/prettier/bin/prettier.cjs --check .`        | Passed, exit 0. |
| `node node_modules/vitest/vitest.mjs run`                      | Passed, exit 0. |

The independent publication audit also matched every copied Office file to its approved SHA-256, checked ZIP package integrity and current page/tab approvals, compared immutable workflow/source metadata, and resolved every local handbook/report link within the repository. Hosted PR/main, browser, platform and container jobs remain separate required checks; they are not inferred from these local results.

The existing suite passed 407 Python tests at 99.75% combined coverage (90% floor retained) and 12 TypeScript tests. The first sandboxed attempt could not connect to the test-owned localhost listeners (Windows error 10013); the complete unchanged suites passed with narrowly scoped execution access. No user service was adopted or modified, no coverage floor was reduced, and no runtime implementation changed.
