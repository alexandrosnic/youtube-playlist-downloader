import json
import os
import re
import difflib
import requests
import time
import ssl

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# -----------------------------------------------------------------------------
# Paths and configuration helpers
# -----------------------------------------------------------------------------

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def get_project_file_path(parent_dir, file_name):
    """Return an absolute path inside the project root."""
    return os.path.join(project_root, parent_dir, file_name)


def read_json(parent_dir, file_name):
    """
    Read a JSON file located under the given parent directory (relative to the
    project root) and return the parsed Python object.
    
    Raises FileNotFoundError with a helpful message if the file doesn't exist,
    suggesting to copy from the .example file.
    """
    file_path = get_project_file_path(parent_dir, file_name)
    if not os.path.exists(file_path):
        example_file = f"{file_name}.example"
        example_path = get_project_file_path(parent_dir, example_file)
        if os.path.exists(example_path):
            raise FileNotFoundError(
                f"Config file not found: {file_path}\n"
                f"Please copy {example_path} to {file_path} and fill in your values."
            )
        else:
            raise FileNotFoundError(
                f"Config file not found: {file_path}\n"
                f"Please create this file with the required configuration."
            )
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_json_if_exists(parent_dir, file_name, default=None):
    """Read a JSON file if it exists, otherwise return the provided default."""
    file_path = get_project_file_path(parent_dir, file_name)
    if not os.path.exists(file_path):
        return default

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_to_json(parent_dir, file_name, data):
    """
    Write a Python object as JSON into a file located under the given parent
    directory (relative to the project root).
    """
    file_path = get_project_file_path(parent_dir, file_name)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def load_ydl_opts_from_json():
    """
    Load yt-dlp options from the ytdlp_config.json file in the config folder.
    Raises FileNotFoundError if the config file is missing.
    """
    return read_json("config", "ytdlp_config.json")


def get_playlist_config():
    """
    Return the contents of playlist_path.json as a dictionary.
    """
    return read_json("config", "playlist_path.json")


def get_playlist_m3u8_output_dir() -> str:
    """Return the YouTube m3u8 output directory from local config."""
    config = get_playlist_config()
    return config["youtube_paths"]["youtube_playlist_m3u8_dir"]


def get_authenticated_service():
    """
    Authenticate with the YouTube Data API and return a service client.
    
    Raises FileNotFoundError if config or client secret files are missing.
    """
    # Load the config file (will raise FileNotFoundError with helpful message if missing)
    config = read_json("config", "google_api_config.json")
    google_api_config = config["google_api"]
    client_secret_file = os.path.join(project_root, "config", google_api_config["client_secret_file"])
    
    if not os.path.exists(client_secret_file):
        raise FileNotFoundError(
            f"OAuth client secret file not found: {client_secret_file}\n"
            f"Please download your OAuth 2.0 client credentials from Google Cloud Console\n"
            f"and save them as {client_secret_file}"
        )
    
    scopes = google_api_config["scopes"]

    # Some editors save JSON with a UTF-8 BOM; utf-8-sig handles both BOM/no-BOM files.
    with open(client_secret_file, "r", encoding="utf-8-sig") as f:
        client_config = json.load(f)

    flow = InstalledAppFlow.from_client_config(client_config, scopes=scopes)
    credentials = flow.run_local_server(port=0, open_browser=False)

    # Build the YouTube service using the authenticated credentials
    youtube_service = build("youtube", "v3", credentials=credentials)
    return youtube_service


def open_or_create_m3u8_file(playlist_folder, playlist_title):
    """
    Ensure an m3u8 file exists for the given playlist and return its contents
    (as a list of lines) together with the file path.
    """
    m3u8_file_path = os.path.join(playlist_folder, f"{playlist_title}.m3u8")
    if not os.path.exists(m3u8_file_path):
        with open(m3u8_file_path, "w", encoding="utf-8") as m3u8_file:
            m3u8_file.write("#EXTM3U\n")

    with open(m3u8_file_path, "r", encoding="utf-8") as f:
        m3u8_data = f.read().splitlines()

    return m3u8_data, m3u8_file_path


def list_files_in_directory(directory):
    """
    Return a flat list of all filenames under the given directory (recursively).
    """
    files = []
    for root, dirs, filenames in os.walk(directory):
        for filename in filenames:
            files.append(filename)
    return files


# -----------------------------------------------------------------------------
# Title and artist helpers
# -----------------------------------------------------------------------------


def filter_name(video_title, video_artist):
    # Normalise dashes and simple punctuation issues.
    video_title = video_title.replace("\u2013", "-")
    video_title = video_title.replace("~", "-")
    video_title = video_title.replace(" ...", "")
    video_title = video_title.replace('\x92', "'")
    video_title = video_title.replace('\u0301', '')

    # Strip common YouTube-specific suffixes from page titles, e.g. " - YouTube".
    # This is a safeguard in addition to cleaning done in get_video_details.
    video_title = re.sub(r"\s*-\s*YouTube(\s+Music)?$", "", video_title, flags=re.IGNORECASE)

    # Handle colon vs hyphen for "Artist - Track" style titles.
    video_title = video_title.replace(':', '-') if ':' in video_title and '-' not in video_title else video_title.replace(':', '')

    # Remove characters that are problematic in file names.
    video_title = re.sub(r'[\/*?"<>#|]', '', video_title)

    # Remove various "Official ..." decorations.
    video_title = video_title.replace(' (Official Music Video)', '')
    video_title = video_title.replace(' [Official Music Video]', '')
    video_title = video_title.replace(' Official Music Video', '')
    video_title = video_title.replace(' (Official Version)', '')
    video_title = video_title.replace(' (Official Audio)', '')
    video_title = video_title.replace(' [Official Audio]', '')
    video_title = video_title.replace(' Official Audio', '')
    video_title = video_title.replace(' (Official 4K Video)', '')
    video_title = video_title.replace(' (Official)', '')
    video_title = video_title.replace(' (Official Visualizer)', '')
    video_title = video_title.replace(' Official Visualizer', '')
    video_title = video_title.replace(' (Official Video HD)', '')
    video_title = video_title.replace(' (Official HD Video)', '')
    video_title = video_title.replace(' (Official Video)', '')
    video_title = video_title.replace(' [Official Video]', '')
    video_title = video_title.replace(' (Official Lyric Video)', '')
    video_title = video_title.replace(' [Official Lyrics Video]', '')
    video_title = video_title.replace(' [Official Lyric Video]', '')
    if video_title.endswith('.') or video_title.endswith(' '):
        video_title = video_title[:-1]
    if video_title.endswith('..'):
        video_title = video_title[:-2]

    video_artist = video_artist.replace(' - Topic', '')
    video_artist = video_artist.replace('VEVO', '')
    video_artist = video_artist.replace('Official', '')
    video_artist = video_artist.replace(' Official', '')
    video_artist = video_artist.replace('\u00f6', 'o')
    # Trim trailing dot or space if present
    video_artist = video_artist[:-1] if video_artist.endswith('.') else video_artist
    if video_artist.endswith('.') or video_artist.endswith(' '):
        video_artist = video_artist[:-1]
    video_artist = video_artist.replace(':', '')
    video_artist = video_artist.replace('*', '')
    video_artist = video_artist.replace('/', ' ')


    return video_title, video_artist


def extract_all_artists(video_artist):
    """
    Split a raw artist string into individual artist names.
    """
    # List of separators to split the artist name
    separators = [r' x ', r'feat\.', r'ft\.', r' vs ', r' & ', r' feat', r' Feat', r', ']

    # Combine the separators into a single regular expression pattern
    separator_pattern = '|'.join(re.escape(separator) for separator in separators)

    # Split the artist name using the defined separators
    artist_parts = re.split(separator_pattern, video_artist, flags=re.IGNORECASE)
    
    # Remove leading and trailing whitespace from each part
    cleaned_artists = [part.strip() for part in artist_parts if part.strip()]
    return cleaned_artists


def count_songs_in_artist_folder(artist_folder):
    # Assuming each song is represented by a file in the artist folder
    if os.path.isdir(artist_folder):
        return len([f for f in os.listdir(artist_folder) if os.path.isfile(os.path.join(artist_folder, f))])
    else:
        return 0

def extract_main_artist(artists):
    max_songs = 0
    new_artists = 0
    main_artist = artists[0]
    for artist in artists:
        artist_folder = get_artist_folder(artist)
        if (artist_folder) and artist != "Various Artists":
            song_count = count_songs_in_artist_folder(artist_folder)
            if song_count > max_songs:
                max_songs = song_count
                main_artist = os.path.basename(artist_folder)
        else:
            new_artists += 1
    if new_artists == len(artists):
        main_artist = artists[0]
    return main_artist


def get_artist_folder(artist, create_if_not_exists=False):
    """
    Return the folder path for the given artist. If create_if_not_exists is True
    and no close match is found, create a new folder for this artist.
    """
    playlist_m3u8_dir = get_playlist_m3u8_output_dir()
    artists_parent_folder = os.path.join(
        os.path.dirname(playlist_m3u8_dir), "Artists"
    )
    existing_folders_lower = [folder.lower() for folder in os.listdir(artists_parent_folder)]
    similar_folders_lower = difflib.get_close_matches(artist.lower(), existing_folders_lower, cutoff=0.8)
    if similar_folders_lower:
        similar_folder_original = next((w for w in os.listdir(artists_parent_folder) if w.lower() == similar_folders_lower[0]), None) 
        print(f"Check if the song exists in the folder: {similar_folder_original}")
        return os.path.join(artists_parent_folder, similar_folder_original)
    else:
        if create_if_not_exists:
            artist_folder = os.path.join(artists_parent_folder, artist)
            os.makedirs(artist_folder)
            print(f"{artist_folder} does not exists. Just created it")
            return artist_folder
        else:
            return None


# -----------------------------------------------------------------------------
# YouTube / HTTP helpers
# -----------------------------------------------------------------------------


def get_video_details(video_url):
    try:
        response = requests.get(video_url)
        if response.status_code == 200:
            html = response.text
            title_match = re.search(r'<title>(.*?)</title>', html)
            artist_match = re.search(r'"author":"(.*?)"', html)

            if title_match and artist_match:
                # Page titles are typically "<video title> - YouTube" or
                # "<video title> - YouTube Music". Strip that site suffix so it
                # doesn't leak into file names.
                raw_title = title_match.group(1)
                video_title = re.sub(r"\s*-\s*YouTube(\s+Music)?$", "", raw_title, flags=re.IGNORECASE)
                artist = artist_match.group(1)

                return video_title, artist
            else:
                print("Unable to retrieve video details.")
        else:
            print(f"Error: {response.status_code} - {response.reason}")
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving video page: {str(e)}")

    return None, None


def youtube_search(youtube_service, query, retries=3, backoff_factor=1.0):
    """
    Search YouTube for videos matching a query.
    
    Note: This uses the search API which costs 100 quota units per call (expensive!).
    Use sparingly to avoid quota issues.
    """
    from utils.quota_manager import handle_quota_error, add_rate_limit_delay
    
    attempt = 0
    while attempt < retries:
        try:
            add_rate_limit_delay()  # Rate limiting
            search_response = youtube_service.search().list(
                q=query,
                part='id',
                maxResults=10
            ).execute()
            videos = search_response.get('items', [])
            video_ids = [video['id']['videoId'] for video in videos if video['id']['kind'] == 'youtube#video']
            return video_ids
        except HttpError as e:
            if handle_quota_error(e, f"YouTube search for '{query}'"):
                # Quota exceeded - can't retry, return empty
                print("⚠ Search failed due to quota. Returning empty results.")
                return []
            elif e.resp.status in [500, 502, 503, 504]:
                attempt += 1
                time.sleep(backoff_factor * (2 ** attempt))
            else:
                raise
        except ssl.SSLError as e:
            if 'SSL: EOF occurred in violation of protocol' in str(e):
                attempt += 1
                time.sleep(backoff_factor * (2 ** attempt))
            else:
                raise
    raise Exception(f"Failed to complete request after {retries} attempts")