from pathlib import Path

from youtubarr import availability
from youtubarr.acquisition import _normalise_media_fields
from youtubarr.arr import generate_mapping_suggestions
from youtubarr.models import Integration, MediaItem
from youtubarr.security import hash_password, verify_password


def test_password_roundtrip():
    hashed = hash_password("a-long-test-password")
    assert verify_password("a-long-test-password", hashed)
    assert not verify_password("wrong", hashed)


def test_root_mapping_suggestions_do_not_collapse_multiple_roots():
    app = Integration(id=1, kind="sonarr", name="Sonarr", base_url="http://sonarr", api_key_enc="x")
    roots = [
        {"path": "/zurg/tv/kids", "freeSpace": 1},
        {"path": "/zurg/tv/bbc", "freeSpace": 1},
        {"path": "/another/location/kids", "freeSpace": 1},
    ]
    rows = generate_mapping_suggestions(app, roots)
    assert rows[0]["localPath"] == "/library/tv/kids"
    assert rows[1]["localPath"] == "/library/tv/bbc"
    assert rows[2]["localPath"] != rows[0]["localPath"]
    assert len({row["localPath"] for row in rows}) == 3


def test_radarr_and_lidarr_families_are_distinct():
    radarr = Integration(id=2, kind="radarr", name="Radarr", base_url="http://radarr", api_key_enc="x")
    lidarr = Integration(id=3, kind="lidarr", name="Lidarr", base_url="http://lidarr", api_key_enc="x")
    assert generate_mapping_suggestions(radarr, [{"path": "/remote/main"}])[0]["localPath"].startswith("/library/movies/")
    assert generate_mapping_suggestions(lidarr, [{"path": "/remote/main"}])[0]["localPath"].startswith("/library/music/")


def test_episode_media_normalises_music_only_not_null_fields():
    media = MediaItem(
        integration_id=1,
        remote_id=42,
        kind="episode",
        title="Pilot",
        track_number=None,
        disc_number=None,
        duration=None,
    )
    media = _normalise_media_fields(media)
    assert media.track_number == 0
    assert media.disc_number == 1
    assert media.duration == 0
    assert media.season_number == 0
    assert media.episode_number == 0


def test_completed_youtubarr_media_overlays_arr_missing_state(monkeypatch):
    monkeypatch.setattr(
        availability,
        "completed_availability",
        lambda kind, remote_ids=None: {
            42: {
                "remoteId": 42,
                "outputPath": "/library/tv/Test/Season 01/Test - S01E01.mp4",
                "assetId": "asset-1",
            }
        },
    )
    row = availability.overlay_items("episode", [{"id": 42, "title": "Pilot", "hasFile": False}])[0]
    assert row["arrHasFile"] is False
    assert row["youtubarrHasFile"] is True
    assert row["hasFile"] is True
    assert row["availability"] == "youtubarr"


def test_arr_registered_media_wins_over_youtubarr_state(monkeypatch):
    monkeypatch.setattr(
        availability,
        "completed_availability",
        lambda kind, remote_ids=None: {42: {"remoteId": 42, "outputPath": "/library/test", "assetId": "asset-1"}},
    )
    row = availability.overlay_items("episode", [{"id": 42, "hasFile": True}])[0]
    assert row["arrHasFile"] is True
    assert row["hasFile"] is True
    assert row["availability"] == "registered"


def test_wanted_missing_filters_verified_youtubarr_media(monkeypatch):
    monkeypatch.setattr(
        availability,
        "completed_availability",
        lambda kind, remote_ids=None: {42: {"remoteId": 42, "outputPath": "/library/test", "assetId": "asset-1"}},
    )
    payload = {"records": [{"id": 42, "hasFile": False}, {"id": 43, "hasFile": False}], "totalRecords": 2}
    result = availability.filter_missing_payload("episode", payload)
    assert [row["id"] for row in result["records"]] == [43]
    assert result["totalRecords"] == 1
