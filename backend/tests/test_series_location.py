from pathlib import Path

import pytest
from fastapi import HTTPException

from youtubarr.models import MediaItem
from youtubarr.series_location import _episode_destination, _normalise_remote_root, _series_folder_name


def test_normalise_youtubarr_tv_roots():
    assert _normalise_remote_root('/youtube-library/tv/kids/') == '/youtube-library/tv/kids'
    assert _normalise_remote_root(r'\youtube-library\tv\shows') == '/youtube-library/tv/shows'


def test_reject_non_youtubarr_tv_root():
    with pytest.raises(HTTPException):
        _normalise_remote_root('/zurg_mnt/zurg/__magic__/tv/kids')
    with pytest.raises(HTTPException):
        _normalise_remote_root('/youtube-library/tv/../music')


def test_series_folder_preserves_sonarr_folder_name():
    assert _series_folder_name({'title': 'Wolfblood', 'year': 2012, 'path': '/youtube-library/tv/shows/Wolfblood'}) == 'Wolfblood'


def test_episode_destination_changes_only_series_root():
    media = MediaItem(
        integration_id=1,
        remote_id=99,
        kind='episode',
        parent_remote_id=12,
        title='Episode 1',
        path='/library/tv/shows/ChuckleVision/Season 03/ChuckleVision - S03E01 - Episode 1.mp4',
        season_number=3,
        episode_number=1,
        track_number=0,
        disc_number=1,
        duration=0,
        monitored=True,
        has_file=False,
    )
    destination = _episode_destination(
        Path('/library/tv/kids/ChuckleVision'),
        media,
        media.path,
    )
    assert destination == Path('/library/tv/kids/ChuckleVision/Season 03/ChuckleVision - S03E01 - Episode 1.mp4')
