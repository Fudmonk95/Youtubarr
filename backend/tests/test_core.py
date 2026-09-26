from pathlib import Path

from youtubarr.arr import generate_mapping_suggestions
from youtubarr.models import Integration
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
