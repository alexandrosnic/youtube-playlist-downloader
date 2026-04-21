"""Helpers for fetching YouTube playlists and preparing local playlist data."""

from app.songs_handler import get_songs
from utils.utils import (
    open_or_create_m3u8_file,
    write_to_json,
    read_json,
    read_json_if_exists,
    get_playlist_m3u8_output_dir,
)
from utils.quota_manager import handle_quota_error, add_rate_limit_delay, check_cached_data_available
from googleapiclient.errors import HttpError

import os


project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def get_playlists_from_youtube(youtube_service, use_cache=False):
    """
    Retrieve all playlists for the authorized user's YouTube channel.
    
    :param youtube_service: Authenticated YouTube service
    :param use_cache: If True, try to use cached data first
    :return: List of playlists
    """
    # Try cache first if requested
    if use_cache:
        try:
            cached_playlists = read_json_if_exists("data", "playlists.json")
            if cached_playlists is not None:
                print("Using cached playlists data...")
                return cached_playlists
        except:
            print("Cache file exists but couldn't be read, fetching from API...")
    
    # Retrieve all playlists for the authorized user's YouTube channel
    playlists = []
    next_page_token = None

    page_n = 0
    while True:
        try:
            add_rate_limit_delay()  # Rate limiting
            response = youtube_service.playlists().list(
                part='snippet',
                mine=True,
                maxResults=50,  # Adjust the number of results per page as desired
                pageToken=next_page_token
            ).execute()

            playlists.extend(response['items'])
            next_page_token = response.get('nextPageToken')

            print(f"Fetched {(page_n + 1) * 50} playlists. Getting the next page")
            page_n += 1
            if not next_page_token:
                print(f"Fetched all the playlists")
                break
        except HttpError as e:
            if handle_quota_error(e, "Fetching playlists"):
                # If quota exceeded, try to return cached data if available
                if check_cached_data_available():
                    print("\nTrying to use cached playlists data...")
                    try:
                        cached_playlists = read_json_if_exists("data", "playlists.json")
                        if cached_playlists is not None:
                            return cached_playlists
                    except:
                        pass
                raise  # Re-raise if no cache available
            else:
                raise  # Re-raise non-quota errors

    write_to_json("data", "playlists.json", playlists)
    return playlists


def fetch_playlists(playlists, youtube_service, only_playlist: str | None = None):
    playlist_data = {"playlists": {}}  # Dictionary to store playlist data
    playlist_m3u8_folder = get_playlist_m3u8_output_dir()
    os.makedirs(playlist_m3u8_folder, exist_ok=True)
    
    for playlist in playlists:
        playlist_title = playlist["snippet"]["title"]

        if only_playlist and playlist_title != only_playlist:
            continue
        if should_skip_playlist(playlist):
            print(f"Skipping {playlist_title} playlist")
            continue
        
        print(f"Fetching {playlist_title} playlist")

        # Check if M3U8 file exists, if not, create it
        m3u8_data, m3u8_file_path = open_or_create_m3u8_file(playlist_m3u8_folder, playlist_title)

        # It returns a list with all the info of all the songs of the Youtube channel's playlist 
        # for each playlist
        songs_per_playlist = get_songs(playlist, youtube_service, playlist_data)

        playlist_data["playlists"][playlist_title] = songs_per_playlist

        # playlist_json_file = f"{playlist_title}/{playlist_title}.json"
        # os.makedirs(os.path.dirname(playlist_json_file), exist_ok=True)
        # write_to_json(songs_per_playlist, 'playlist_json_file.json')

    # playlists_data_path = os.path.join(project_root, 'data', 'playlist_data_test.json')
    # save in playlist_data_test.json all the Youtube playlists and their data (songs etc)
    write_to_json("data", "playlist_data_test.json", playlist_data)
    return playlist_data


def should_skip_playlist(playlist):
    playlists_to_skip = read_json("config", "skipped_playlists.json")
    # skipped_playlists_path = os.path.join(project_root, 'config', 'skipped_playlists.json')
    # with open(skipped_playlists_path, 'r') as skip_file:
    #     playlists_to_skip = json.load(skip_file)
    playlist_title = playlist['snippet']['title']
    return playlist_title in playlists_to_skip


    