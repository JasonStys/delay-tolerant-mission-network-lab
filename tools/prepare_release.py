"""Prepare only a new version/source-bound draft by Jason Stys.

Function: main; shared authorization contract: release_contract.py. Index: docs/CODE_INDEX.md.
No public tag, release or prior draft is retargeted or reused.
"""

if __package__:
    from .release_contract import prepare
else:
    from release_contract import prepare


def main() -> None:
    """Require exact clean main, coherent version and complete passing prerequisite workflows."""
    prepare()


if __name__ == "__main__":
    main()
