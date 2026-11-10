# Delay Tolerant Mission Network Lab handbook

By Jason Stys.

Rehearse bounded store-and-forward delivery across fictional scheduled contacts. Inspect routing, expiry, storage pressure and delivery outcomes without connecting to spacecraft or claiming an interoperable operational protocol stack.

Replay delayed message delivery, inspect queue and hop waterfalls, and export evidence through versioned 1.1 portable applications.

Makes simulated recovery and latency investigation available without a developer setup, while checked extraction and release identity connect the download to reviewed source.

## Read the documentation

| Edition                                                      | Audience and contents                                                                                              |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| [project-guide.docx](reports/project-guide.docx)             | User and developer guide: purpose, current usage, design, boundaries and source references.                        |
| [validation-review.docx](reports/validation-review.docx)     | Reviewer edition: exact tested baseline, observed workflows, dated local results and remaining limits.             |
| [validation-evidence.xlsx](reports/validation-evidence.xlsx) | Two filterable Excel Tables for observed workflows and test-source inventory, with recalculating outcome formulas. |

The editable Markdown remains the maintenance source. The Word files are readable editions. The workbook is an evidence index rather than a test runner. See [publication identities and review](reports/publications.json) and the [documentation refresh record](reports/documentation-refresh-2026-11-09.md).

## Current usage and help

[README quick start](../README.md) is the entry point. Use the project-specific guides below before changing inputs, operating modes or deployment assumptions.

### Usage and operations

- [RELEASE](RELEASE.md)
- [USER GUIDE](USER_GUIDE.md)

### Design and contracts

- [API](API.md)
- [ARCHITECTURE](ARCHITECTURE.md)
- [MODEL](MODEL.md)

### Security and validation

- [VALIDATION](VALIDATION.md)

## Historical results and reproduction

The reviewed source is [`df32f632dc89a329cfdd4eaf9c9f7b7248f8f5ac`](https://github.com/JasonStys/delay-tolerant-mission-network-lab/tree/df32f632dc89a329cfdd4eaf9c9f7b7248f8f5ac). The observed functional workflow baseline is `df32f632dc89a329cfdd4eaf9c9f7b7248f8f5ac`; those observations are recorded at `2026-11-10T05:25:40.628667+00:00`. They do not certify an unrun later revision.

- [Detailed recorded validation](reports/PORTABLE_RELEASE_20261109.md)
- [Current Actions](https://github.com/JasonStys/delay-tolerant-mission-network-lab/actions) records later integration checks separately.
- Preserve dated measurements and follow the existing testing guide to reproduce them; a test-source inventory alone does not establish execution.

## Practical boundaries

- Invented bounded topology and logical ticks; no real radios, BPv7/BPSec interoperability or exactly-once networking.
- Waterfalls explain a complete simulated experiment; causal replay separately hides future outcomes. Neither diagnoses actual radio faults.
- Unsigned portable files for documented desktop OS/CPU targets; no system installer, native mobile app, production host or operational assurance.

## Maintaining these editions

Update the editable usage/design/test documents first. Rebuild and visually review every Word page and workbook tab before replacing an edition; verify the exact binary digests and evidence source in publications.json. Keep account data, logs with secrets, installed-app state and private test stores out of documentation. Source and release assets retain their existing security and licensing boundaries.
