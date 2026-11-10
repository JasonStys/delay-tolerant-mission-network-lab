"""Independent real-shape draft API contract fixtures by Jason Stys.

Functions: row, reader and test_*; variables: synthetic list/detail pages, swaps and HTTP failures.
No GitHub calls or product state changes. Exact lines: docs/CODE_INDEX.md.
"""

import copy
import unittest

from tools.draft_lookup import MAX_PAGES, PER_PAGE, find_release, read_by_id, require_draft

REPO = "JasonStys/example-lab"
SOURCE = "a" * 40
BASE = f"repos/{REPO}"


def row(identifier=439911956, **changes):
    """Build independent metadata with a legitimate untagged draft HTML URL."""
    result = {
        "id": identifier,
        "tag_name": "v1.1.0",
        "draft": True,
        "prerelease": False,
        "target_commitish": SOURCE,
        "url": f"https://api.github.com/{BASE}/releases/{identifier}",
        "upload_url": f"https://uploads.github.com/{BASE}/releases/{identifier}/assets{{?name,label}}",
        "assets_url": f"https://api.github.com/{BASE}/releases/{identifier}/assets",
        "assets": [],
        "html_url": f"https://github.com/{REPO}/releases/tag/untagged-fixture",
    }
    result.update(changes)
    return result


class Fixtures(unittest.TestCase):
    """Independent authenticated-list, numeric-identity and failure fixtures; no network calls."""

    def reader(self, pages, detail=None):
        """Provide copied pages/details and record every requested endpoint."""
        self.calls = []

        def read(endpoint):
            """Return an authored API reply and reject published-only tag lookup."""
            self.calls.append(endpoint)
            if "/releases/tags/" in endpoint:
                self.fail("Published-only tag endpoint used for a draft")
            if "?per_page=100&page=" in endpoint:
                return copy.deepcopy(pages[int(endpoint.rsplit("=", 1)[1]) - 1])
            if detail is not None:
                if isinstance(detail, Exception):
                    raise detail
                return copy.deepcopy(detail)
            identifier = int(endpoint.rsplit("/", 1)[1])
            return copy.deepcopy(
                next(value for page in pages for value in page if value["id"] == identifier)
            )

        return read

    def test_untagged_draft_reads_numeric_id_not_public_tag(self):
        """Untagged draft reads numeric id not public tag."""
        value = row()
        actual = require_draft(self.reader([[value]]), REPO, "1.1.0", SOURCE)
        self.assertEqual(actual, value)
        self.assertEqual(
            self.calls, [f"{BASE}/releases?per_page=100&page=1", f"{BASE}/releases/439911956"]
        )

    def test_complete_empty_listing_allows_explicit_absence(self):
        """Complete empty listing allows explicit absence."""
        self.assertIsNone(find_release(self.reader([[]]), REPO, "v1.1.0", missing=True))

    def test_missing_required_release_is_error(self):
        """Missing required release is error."""
        with self.assertRaisesRegex(ValueError, "not found"):
            find_release(self.reader([[]]), REPO, "v1.1.0")

    def test_general_collision_lookup_retains_public_wrong_source(self):
        """General collision lookup retains public wrong source."""
        value = row(draft=False, target_commitish="main")
        self.assertEqual(find_release(self.reader([[value]]), REPO, "v1.1.0", missing=True), value)

    def test_later_page_exact_match(self):
        """Later page exact match."""
        first = [row(i + 1, tag_name=f"v0.0.{i}") for i in range(PER_PAGE)]
        actual = find_release(self.reader([first, [row()]]), REPO, "v1.1.0")
        self.assertEqual(actual["id"], 439911956)
        self.assertEqual(len(self.calls), 3)

    def test_all_full_pages_fail_without_false_absence(self):
        """All full pages fail without false absence."""
        pages = [
            [row(p * PER_PAGE + i + 1, tag_name=f"v0.{p}.{i}") for i in range(PER_PAGE)]
            for p in range(MAX_PAGES)
        ]
        with self.assertRaisesRegex(ValueError, "bounded complete"):
            find_release(self.reader(pages), REPO, "v1.1.0", missing=True)
        self.assertEqual(len(self.calls), MAX_PAGES)

    def test_full_cap_even_found_cannot_hide_later_duplicate(self):
        """Full cap even found cannot hide later duplicate."""
        pages = [
            [row(p * PER_PAGE + i + 1, tag_name=f"v0.{p}.{i}") for i in range(PER_PAGE)]
            for p in range(MAX_PAGES)
        ]
        pages[0][0]["tag_name"] = "v1.1.0"
        with self.assertRaisesRegex(ValueError, "bounded complete"):
            find_release(self.reader(pages), REPO, "v1.1.0")

    def test_duplicate_exact_tag_refuses_first_match(self):
        """Duplicate exact tag refuses first match."""
        with self.assertRaisesRegex(ValueError, "Ambiguous"):
            find_release(self.reader([[row(1), row(2, draft=False)]]), REPO, "v1.1.0")
        self.assertEqual(len(self.calls), 1)

    def test_repeated_id_pagination_refuses(self):
        """Repeated id pagination refuses."""
        page = [row(i + 1, tag_name=f"v0.0.{i}") for i in range(PER_PAGE)]
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            find_release(self.reader([page, [page[-1]]]), REPO, "v1.1.0")

    def test_malformed_pages_fail(self):
        """Malformed pages fail."""
        for page in ({}, None, [{}], [row()] * 101):
            with self.subTest(page=type(page).__name__), self.assertRaises(ValueError):
                find_release(self.reader([page]), REPO, "v1.1.0", missing=True)

    def test_invalid_ids_never_become_paths(self):
        """Invalid ids never become paths."""
        for identifier in (True, False, 0, -1, 2**63, "1", "../1"):
            with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                read_by_id(self.reader([[]]), REPO, identifier)
            self.assertEqual(self.calls, [])

    def test_foreign_list_namespace_refuses_before_detail(self):
        """Foreign list namespace refuses before detail."""
        with self.assertRaisesRegex(ValueError, "Foreign release"):
            find_release(
                self.reader([[row(url="https://outside.invalid/release")]]), REPO, "v1.1.0"
            )
        self.assertEqual(len(self.calls), 1)

    def test_detail_identity_swap_publication_and_retarget_refuse(self):
        """Detail identity swap publication and retarget refuse."""
        for changes in (
            {"id": 2},
            {"tag_name": "v2.0.0"},
            {"draft": False},
            {"target_commitish": "b" * 40},
            {"prerelease": True},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                find_release(self.reader([[row()]], row(**changes)), REPO, "v1.1.0")

    def test_detail_foreign_hypermedia_refuses(self):
        """Detail foreign hypermedia refuses."""
        for key in ("url", "upload_url", "assets_url"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                find_release(
                    self.reader([[row()]], row(**{key: "https://outside.invalid/path"})),
                    REPO,
                    "v1.1.0",
                )

    def test_lost_access_never_falls_back_to_list(self):
        """Lost access never falls back to list."""
        with self.assertRaisesRegex(RuntimeError, "HTTP404"):
            find_release(self.reader([[row()]], RuntimeError("HTTP404")), REPO, "v1.1.0")

    def test_auth_network_errors_are_not_absence(self):
        """Auth network errors are not absence."""
        for message in ("HTTP403", "HTTP404", "network unavailable"):

            def denied(_, message=message):
                """Raise the supplied transport or authorization failure without a fallback reply."""
                raise RuntimeError(message)

            with self.subTest(message=message), self.assertRaises(RuntimeError):
                find_release(denied, REPO, "v1.1.0", missing=True)

    def test_same_bad_state_in_both_snapshots_still_fails_draft_policy(self):
        """Same bad state in both snapshots still fails draft policy."""
        for changes in ({"draft": False}, {"target_commitish": "b" * 40}, {"prerelease": True}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                require_draft(self.reader([[row(**changes)]]), REPO, "1.1.0", SOURCE)

    def test_expected_prepared_id_is_bound(self):
        """Expected prepared id is bound."""
        self.assertEqual(
            require_draft(self.reader([[row()]]), REPO, "1.1.0", SOURCE, expected_id=439911956)[
                "id"
            ],
            439911956,
        )
        with self.assertRaisesRegex(ValueError, "Prepared release ID"):
            require_draft(self.reader([[row()]]), REPO, "1.1.0", SOURCE, expected_id=1)

    def test_invalid_namespace_tag_source_refuses_before_http(self):
        """Invalid namespace tag source refuses before http."""
        for repo, version, source in (
            ("owner/../../outside", "1.1.0", SOURCE),
            (REPO, "1.1.0?outside", SOURCE),
            (REPO, "1.1.0", "short"),
        ):
            read = self.reader([[]])
            with self.subTest(repo=repo, version=version), self.assertRaises(ValueError):
                require_draft(read, repo, version, source)
            self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
