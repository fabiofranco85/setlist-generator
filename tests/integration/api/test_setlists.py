"""Integration tests for setlist API endpoints against local Supabase.

Tests cover: generation, listing, retrieval, replacement, derivation,
PDF download, RBAC enforcement, and markdown output creation.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.supabase, pytest.mark.slow]


# -- helpers -----------------------------------------------------------------

GENERATE_URL = "/setlists/generate"
SETLISTS_URL = "/setlists"
TEST_DATE = "2099-12-31"  # Far-future date to avoid history collisions

ALL_SONG_TITLES = {
    "Upbeat Song",
    "Moderate Song",
    "Reflective Song",
    "Worship Song",
}


def _generate_setlist(client, date=TEST_DATE, **extra):
    """Helper: generate a setlist and return the response."""
    payload = {"date": date, **extra}
    return client.post(GENERATE_URL, json=payload)


def _generate_with_overrides(client, date=TEST_DATE):
    """Helper: generate a setlist with overrides covering all moments.

    With only 4 songs and no songs tagged for 'criancas', we use overrides
    for moments that might not have candidates so the generator succeeds
    cleanly.  Moment names use the canonical Portuguese spelling with
    accents as defined in ``MOMENTS_CONFIG`` / ``system_config``.
    """
    overrides = {
        "louvor": ["Upbeat Song", "Moderate Song", "Reflective Song", "Worship Song"],
        "prel\u00fadio": ["Upbeat Song"],
        "sauda\u00e7\u00e3o": ["Moderate Song"],
        "ofert\u00f3rio": ["Reflective Song"],
        "posl\u00fadio": ["Worship Song"],
        "crian\u00e7as": ["Upbeat Song"],
    }
    return _generate_setlist(client, date=date, overrides=overrides)


# -- 1. Generate basic setlist (editor) -------------------------------------


class TestGenerateSetlist:
    """POST /setlists/generate"""

    def test_generate_basic(self, make_client, seed_songs):
        """Editor can generate a setlist; response has date and moments."""
        client = make_client("editor")
        resp = _generate_with_overrides(client)

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["date"] == TEST_DATE
        assert isinstance(body["moments"], dict)
        # At least louvor should be present with songs
        assert "louvor" in body["moments"]
        assert len(body["moments"]["louvor"]) > 0

    # -- 2. Generate with overrides ------------------------------------------

    def test_generate_with_overrides(self, make_client, seed_songs):
        """Overrides for louvor are honoured in the response."""
        client = make_client("editor")
        override_songs = [
            "Reflective Song",
            "Worship Song",
            "Upbeat Song",
            "Moderate Song",
        ]
        resp = _generate_setlist(
            client,
            overrides={"louvor": override_songs},
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        # The louvor moment must contain exactly the overridden songs
        # (energy ordering may reorder them, but the set must match)
        assert set(body["moments"]["louvor"]) == set(override_songs)

    # -- 3. Generate with label ----------------------------------------------

    def test_generate_with_label(self, make_client, seed_songs):
        """Generating with a label stores and returns the label."""
        client = make_client("editor")

        # First generate the base setlist
        _generate_with_overrides(client, date="2099-11-01")

        # Now generate a labeled variant for the same date
        resp = _generate_with_overrides(client, date="2099-11-02")
        assert resp.status_code == 200

        resp_labeled = _generate_setlist(
            client,
            date="2099-11-02",
            label="evening",
            overrides={
                "louvor": ["Worship Song", "Reflective Song", "Moderate Song", "Upbeat Song"],
                "prel\u00fadio": ["Upbeat Song"],
                "sauda\u00e7\u00e3o": ["Moderate Song"],
                "ofert\u00f3rio": ["Reflective Song"],
                "posl\u00fadio": ["Worship Song"],
                "crian\u00e7as": ["Upbeat Song"],
            },
        )
        assert resp_labeled.status_code == 200, resp_labeled.text
        body = resp_labeled.json()
        assert body["label"] == "evening"
        assert body["date"] == "2099-11-02"

    # -- 13. Viewer cannot generate (403) ------------------------------------

    def test_viewer_cannot_generate(self, make_client, seed_songs):
        """Viewer role is rejected with 403."""
        client = make_client("viewer")
        resp = _generate_setlist(client)

        assert resp.status_code == 403


# -- 4 & 5. List setlists ---------------------------------------------------


class TestListSetlists:
    """GET /setlists"""

    def test_list_returns_results(self, make_client, seed_songs):
        """After generating, the list endpoint returns at least one entry."""
        client = make_client("editor")
        _generate_with_overrides(client, date="2099-10-01")

        resp = client.get(SETLISTS_URL)
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert any(s["date"] == "2099-10-01" for s in body)

    def test_list_filter_by_label(self, make_client, seed_songs):
        """Label query param filters correctly."""
        client = make_client("editor")
        _generate_with_overrides(client, date="2099-10-02")
        _generate_setlist(
            client,
            date="2099-10-03",
            label="morning",
            overrides={
                "louvor": ["Upbeat Song", "Moderate Song", "Reflective Song", "Worship Song"],
                "prel\u00fadio": ["Upbeat Song"],
                "sauda\u00e7\u00e3o": ["Moderate Song"],
                "ofert\u00f3rio": ["Reflective Song"],
                "posl\u00fadio": ["Worship Song"],
                "crian\u00e7as": ["Upbeat Song"],
            },
        )

        # Filter for labeled setlists only
        resp = client.get(SETLISTS_URL, params={"label": "morning"})
        assert resp.status_code == 200
        body = resp.json()
        assert all(s["label"] == "morning" for s in body)

        # Filter for unlabeled
        resp_unlabeled = client.get(SETLISTS_URL, params={"label": ""})
        assert resp_unlabeled.status_code == 200
        body_unlabeled = resp_unlabeled.json()
        assert all(s.get("label", "") == "" for s in body_unlabeled)


# -- 6 & 7. Get by date -----------------------------------------------------


class TestGetSetlist:
    """GET /setlists/{date}"""

    def test_get_by_date_found(self, make_client, seed_songs):
        """Retrieving a generated setlist by date returns 200."""
        client = make_client("editor")
        _generate_with_overrides(client, date="2099-09-01")

        resp = client.get(f"{SETLISTS_URL}/2099-09-01")
        assert resp.status_code == 200
        body = resp.json()
        assert body["date"] == "2099-09-01"
        assert "moments" in body

    def test_get_by_date_not_found(self, make_client, seed_songs):
        """Requesting a non-existent date returns 404."""
        client = make_client("editor")
        resp = client.get(f"{SETLISTS_URL}/1900-01-01")
        assert resp.status_code == 404


# -- 8 & 9 & 10. Replace song -----------------------------------------------


class TestReplaceSong:
    """POST /setlists/{date}/replace"""

    def test_replace_auto_select(self, make_client, seed_songs):
        """Auto-replace (song=null) at louvor position 0 returns 200."""
        client = make_client("editor")
        gen_resp = _generate_with_overrides(client, date="2099-08-01")
        assert gen_resp.status_code == 200

        original_louvor = gen_resp.json()["moments"]["louvor"]

        resp = client.post(
            f"{SETLISTS_URL}/2099-08-01/replace",
            json={"moment": "louvor", "position": 0},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["date"] == "2099-08-01"
        # The louvor list should still have songs
        assert len(body["moments"]["louvor"]) == len(original_louvor)

    def test_replace_manual_song(self, make_client, seed_songs):
        """Manual replacement with a specific song works."""
        client = make_client("editor")
        gen_resp = _generate_with_overrides(client, date="2099-08-02")
        assert gen_resp.status_code == 200

        original_louvor = gen_resp.json()["moments"]["louvor"]
        # Pick a song that is currently in the list to replace position 0
        # and specify a different song for position 0
        target_song = "Reflective Song"

        resp = client.post(
            f"{SETLISTS_URL}/2099-08-02/replace",
            json={
                "moment": "louvor",
                "position": 0,
                "song": target_song,
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        # The target song must be somewhere in louvor (energy reordering
        # may move it away from position 0)
        assert target_song in body["moments"]["louvor"]

    def test_replace_invalid_moment(self, make_client, seed_songs):
        """Replacing in a non-existent moment returns 422."""
        client = make_client("editor")
        _generate_with_overrides(client, date="2099-08-03")

        resp = client.post(
            f"{SETLISTS_URL}/2099-08-03/replace",
            json={"moment": "nonexistent_moment", "position": 0},
        )
        assert resp.status_code == 422


# -- 11. Derive labeled variant ----------------------------------------------


class TestDeriveSetlist:
    """POST /setlists/{date}/derive"""

    def test_derive_labeled_variant(self, make_client, seed_songs):
        """Deriving creates a labeled setlist; it may differ from the base."""
        client = make_client("editor")
        gen_resp = _generate_with_overrides(client, date="2099-07-01")
        assert gen_resp.status_code == 200
        base_moments = gen_resp.json()["moments"]

        resp = client.post(
            f"{SETLISTS_URL}/2099-07-01/derive",
            json={"label": "evening", "replace_count": 2},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["label"] == "evening"
        assert body["date"] == "2099-07-01"

        # Collect all songs from both setlists
        def _all_songs(moments):
            return [s for songs in moments.values() for s in songs]

        base_songs = _all_songs(base_moments)
        derived_songs = _all_songs(body["moments"])

        # With replace_count=2 and only 4 unique songs in the pool,
        # the derived setlist may still overlap heavily, but it should
        # at least exist and be valid.
        assert len(derived_songs) > 0
        # The derived setlist should be retrievable by label
        get_resp = client.get(
            f"{SETLISTS_URL}/2099-07-01",
            params={"label": "evening"},
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["label"] == "evening"


# -- 12. PDF download -------------------------------------------------------


class TestPdfDownload:
    """GET /setlists/{date}/pdf"""

    def test_pdf_download(self, make_client, seed_songs):
        """PDF endpoint returns application/pdf content."""
        client = make_client("editor")
        _generate_with_overrides(client, date="2099-06-01")

        resp = client.get(f"{SETLISTS_URL}/2099-06-01/pdf")
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"] == "application/pdf"
        # PDF magic bytes: %PDF
        assert resp.content[:5] == b"%PDF-"

    def test_pdf_not_found(self, make_client, seed_songs):
        """PDF for non-existent date returns 404."""
        client = make_client("editor")
        resp = client.get(f"{SETLISTS_URL}/1900-01-01/pdf")
        assert resp.status_code == 404


# -- 14. Generate creates markdown output ------------------------------------


class TestMarkdownOutput:
    """Verify that generation persists a markdown file."""

    def test_generate_creates_markdown(self, make_client, seed_songs, tmp_path):
        """After generation, an output markdown file should exist."""
        client = make_client("editor")
        resp = _generate_with_overrides(client, date="2099-05-01")
        assert resp.status_code == 200, resp.text

        # The make_client fixture uses tmp_path for output.
        # Check that an .md file was created for the date.
        md_files = list(tmp_path.rglob("2099-05-01*.md"))
        assert len(md_files) >= 1, (
            f"Expected at least one markdown file for 2099-05-01 under "
            f"{tmp_path}, found: {list(tmp_path.rglob('*'))}"
        )

        # Verify the file has content
        content = md_files[0].read_text()
        assert len(content) > 0
        assert "2099-05-01" in content or "louvor" in content.lower()
