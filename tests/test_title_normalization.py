import pytest

from utils.utils import filter_name
from app.songs_handler import extract_video_info


@pytest.mark.parametrize(
    "raw_title, raw_artist, expected_title, expected_artist",
    [
        (
            "Artist – Track (Official Music Video)",
            "Artist - Topic",
            "Artist - Track",
            "Artist",
        ),
        (
            "Track ~ Live",
            "SomeChannelVEVO",
            "Track - Live",
            "SomeChannel",
        ),
        (
            "Title...",
            "Artist.",
            "Title",
            "Artist",
        ),
    ],
)
def test_filter_name_normalizes_basic_cases(
    raw_title, raw_artist, expected_title, expected_artist
):
    title, artist = filter_name(raw_title, raw_artist)
    assert title == expected_title
    assert artist == expected_artist


@pytest.mark.parametrize(
    "song_title, video_artist, expected_full_prefix",
    [
        (
            "Artist - Track (Official Video)",
            "Artist",
            "Artist - Track",
        ),
        (
            "SOS (feat. Polina) (Skylark Remix - Nic Fanciulli Edit)",
            "Various Artists",
            "Various Artists - SOS (feat. Polina) (Skylark Remix - Nic Fanciulli Edit)",
        ),
    ],
)
def test_extract_video_info_basic_structures(song_title, video_artist, expected_full_prefix):
    full_video_title, _, _ = extract_video_info(song_title, video_artist)
    assert full_video_title.startswith(expected_full_prefix)
