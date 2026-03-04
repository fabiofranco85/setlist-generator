"""End-to-end API workflow integration tests.

Tests run against a local Supabase instance using fixtures from conftest.py.
Each test exercises a multi-step workflow that spans several endpoints.
"""

from __future__ import annotations

import urllib.parse

import pytest

pytestmark = [pytest.mark.supabase, pytest.mark.slow]


# -- helpers -----------------------------------------------------------------


def _encode(title: str) -> str:
    """URL-encode a song title for use in path parameters."""
    return urllib.parse.quote(title, safe="")


# -- workflow tests ----------------------------------------------------------


class TestGenerateRetrieveReplaceVerify:
    """Generate -> Retrieve -> Replace -> Verify workflow."""

    def test_full_replace_cycle(self, make_client, seed_songs):
        client = make_client("editor")

        # Create a 5th song so there's a replacement candidate when all 4
        # seed songs occupy louvor positions.
        client.post("/songs", json={
            "title": "Extra Louvor Song",
            "energy": 2,
            "tags": {"louvor": 5},
            "visibility": "org",
        })

        # Step 1: Generate a setlist with explicit overrides for louvor
        gen_resp = client.post("/setlists/generate", json={
            "date": "2026-06-15",
            "overrides": {
                "louvor": [
                    "Upbeat Song",
                    "Moderate Song",
                    "Reflective Song",
                    "Worship Song",
                ],
            },
        })
        assert gen_resp.status_code == 200
        gen_data = gen_resp.json()
        assert gen_data["date"] == "2026-06-15"
        original_louvor = gen_data["moments"]["louvor"]
        assert len(original_louvor) == 4

        # Step 2: Retrieve and verify it matches
        get_resp = client.get("/setlists/2026-06-15")
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert set(get_data["moments"]["louvor"]) == set(original_louvor)

        # Step 3: Replace the song at louvor position 0 (auto-select)
        replace_resp = client.post("/setlists/2026-06-15/replace", json={
            "moment": "louvor",
            "position": 0,
        })
        assert replace_resp.status_code == 200

        # Step 4: Retrieve again and verify the setlist changed
        final_resp = client.get("/setlists/2026-06-15")
        assert final_resp.status_code == 200
        final_data = final_resp.json()
        final_louvor = final_data["moments"]["louvor"]
        # The replacement should have introduced "Extra Louvor Song"
        # (the only available candidate not already in louvor)
        assert "Extra Louvor Song" in final_louvor, (
            f"Expected 'Extra Louvor Song' in replaced louvor, "
            f"got: {final_louvor}"
        )


class TestGenerateDeriveLabeledVariant:
    """Generate -> Derive labeled variant -> Verify both exist."""

    def test_derive_evening_variant(self, make_client, seed_songs):
        client = make_client("editor")

        # Create extra songs so derivation has replacement candidates.
        for i, energy in enumerate([1, 3], start=1):
            client.post("/songs", json={
                "title": f"Extra Song {i}",
                "energy": energy,
                "tags": {"louvor": 4},
                "visibility": "org",
            })

        # Step 1: Generate the base setlist
        gen_resp = client.post("/setlists/generate", json={
            "date": "2026-06-16",
            "overrides": {
                "louvor": [
                    "Upbeat Song",
                    "Moderate Song",
                    "Reflective Song",
                    "Worship Song",
                ],
            },
        })
        assert gen_resp.status_code == 200
        base_louvor = gen_resp.json()["moments"]["louvor"]

        # Step 2: Derive an "evening" labeled variant, replacing 2 songs
        derive_resp = client.post("/setlists/2026-06-16/derive", json={
            "label": "evening",
            "replace_count": 2,
        })
        assert derive_resp.status_code == 200
        derived_data = derive_resp.json()
        assert derived_data["label"] == "evening"
        assert derived_data["date"] == "2026-06-16"
        derived_louvor = derived_data["moments"]["louvor"]

        # Step 3: List setlists with empty label — base should be present
        list_resp = client.get("/setlists", params={"label": ""})
        assert list_resp.status_code == 200
        base_dates = [s["date"] for s in list_resp.json() if s["label"] == ""]
        assert "2026-06-16" in base_dates

        # Step 4: Retrieve the labeled variant directly
        evening_resp = client.get("/setlists/2026-06-16", params={"label": "evening"})
        assert evening_resp.status_code == 200
        assert evening_resp.json()["label"] == "evening"

        # Step 5: Verify some songs differ between base and derived
        # With 6 louvor-tagged songs and replace_count=2, derivation
        # should produce a visibly different setlist
        differences = sum(
            1 for a, b in zip(base_louvor, derived_louvor) if a != b
        )
        assert differences > 0, (
            f"Expected at least one difference between base {base_louvor} "
            f"and derived {derived_louvor}"
        )


class TestCreateSongThenGenerate:
    """Create song -> Generate setlist -> Verify new song appears."""

    def test_new_song_selected_for_empty_moment(self, make_client, seed_songs):
        client = make_client("editor")

        # Step 1: Create a song tagged exclusively for "criancas" with high weight.
        # The seed_songs fixture provides no songs for "criancas", so this song
        # will be the only candidate and must be selected.
        create_resp = client.post("/songs", json={
            "title": "Brand New Song",
            "energy": 2,
            "tags": {"crianças": 10},
            "visibility": "org",
        })
        assert create_resp.status_code == 200
        assert create_resp.json()["title"] == "Brand New Song"

        # Step 2: Generate a setlist (no overrides — let the algorithm pick)
        gen_resp = client.post("/setlists/generate", json={
            "date": "2026-06-17",
        })
        assert gen_resp.status_code == 200
        moments = gen_resp.json()["moments"]

        # Step 3: Verify "Brand New Song" appears in the criancas moment
        assert "crianças" in moments, (
            f"Expected 'crianças' moment in setlist, got moments: {list(moments.keys())}"
        )
        assert "Brand New Song" in moments["crianças"], (
            f"Expected 'Brand New Song' in crianças moment, "
            f"got: {moments['crianças']}"
        )


class TestSharingWorkflow:
    """Create user song -> Share to org -> Verify visibility -> Admin access."""

    def test_share_to_org_and_admin_access(self, make_client, seed_songs):
        editor = make_client("editor")
        sys_admin = make_client("system_admin")

        # Step 1: Create a user-level song
        create_resp = editor.post("/songs", json={
            "title": "Shareable Song",
            "energy": 3,
            "tags": {"louvor": 3},
            "visibility": "user",
        })
        assert create_resp.status_code == 200

        # Step 2: Share the song to org visibility
        share_resp = editor.post(f"/songs/{_encode('Shareable Song')}/share")
        assert share_resp.status_code == 200
        assert "shared" in share_resp.json()["detail"].lower()

        # Step 3: Verify the song is visible in the editor's song list
        list_resp = editor.get("/songs")
        assert list_resp.status_code == 200
        titles = {s["title"] for s in list_resp.json()}
        assert "Shareable Song" in titles

        # Step 4: Verify system admin can access the admin songs endpoint
        admin_resp = sys_admin.get("/admin/songs/global")
        assert admin_resp.status_code == 200
