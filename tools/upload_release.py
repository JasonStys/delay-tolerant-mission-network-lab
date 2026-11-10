"""Upload one inspected source/version archive pair by Jason Stys.

Function: main; shared authorization contract: release_contract.py. Index: docs/CODE_INDEX.md.
No public release or existing asset is replaced; SHA-256 and archive metadata are rechecked.
"""

if __package__:
    from .release_contract import upload
else:
    from release_contract import upload


def main() -> None:
    """Require unchanged draft target and exact source/platform/version bytes before upload."""
    upload()


if __name__ == "__main__":
    main()
