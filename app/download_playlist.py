"""High-level workflow to sync YouTube playlists into local JSON and m3u8 files."""

from utils.utils import get_authenticated_service
from app.playlist_handler import get_playlists_from_youtube, fetch_playlists
from app.songs_handler import extract_videos, download_songs


def download_playlist(only_playlist: str | None = None, dry_run: bool = False, use_cache: bool = False) -> None:
    """
    Orchestrate the end-to-end playlist sync:
    - authenticate with YouTube,
    - fetch playlists and their items (optionally a single playlist),
    - persist a simplified playlists-with-songs JSON,
    - download missing songs and update m3u8 playlists (or just log in dry-run).

    :param only_playlist: Exact title of a single playlist to process, or None for all.
    :param dry_run: If True, do not download or write files, only log actions.
    """

    # Authenticate YouTube service
    youtube_service = get_authenticated_service()

    # Retrieve playlists (use cache if requested and quota is an issue)
    playlists = get_playlists_from_youtube(youtube_service, use_cache=use_cache)

    # Build a dictionary that contains the playlists and all the songs of each YouTube playlist.
    playlist_data = fetch_playlists(playlists, youtube_service, only_playlist=only_playlist)

    # For all the YouTube playlists saved in the above dictionary, write the contained videos/songs in another JSON.
    playlists_with_songs_data = extract_videos(playlist_data)

    # Download the songs and include them in the m3u8 playlist (or simulate in dry run).
    download_songs(playlists_with_songs_data, youtube_service, only_playlist=only_playlist, dry_run=dry_run)