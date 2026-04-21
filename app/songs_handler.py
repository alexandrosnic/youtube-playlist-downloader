"""Track-level logic: fetching songs, normalizing titles/artists, and downloading."""

from utils.utils import (
    load_ydl_opts_from_json,
    list_files_in_directory,
    filter_name,
    read_json,
    read_json_if_exists,
    write_to_json,
    youtube_search,
    extract_all_artists,
    extract_main_artist,
    get_artist_folder,
    get_video_details,
    get_playlist_m3u8_output_dir,
)
from utils.quota_manager import handle_quota_error, add_rate_limit_delay
from googleapiclient.errors import HttpError

from app.video_data_handler import generate_artist_name, finalize_file_name

import os
import yt_dlp
import re
import mutagen
import difflib


def get_songs(playlist, youtube_service, playlist_data):
    """
    Retrieve all songs for the specified playlist.
    
    :param playlist: Playlist dictionary from API
    :param youtube_service: Authenticated YouTube service
    :param playlist_data: Playlist data dictionary (for caching)
    :return: List of songs/videos
    """
    # Retrieve all songs for the specified playlist
    songs_per_playlist = []
    next_page_token = None
    playlist_id = playlist['id']
    playlist_title = playlist['snippet']['title']
    page_n = 0
    
    while True:
        try:
            add_rate_limit_delay()  # Rate limiting
            # Get all the videos in the playlist
            playlist_items_response = youtube_service.playlistItems().list(
                part='snippet',
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token
            ).execute()

            songs_per_playlist.extend(playlist_items_response['items'])
            next_page_token = playlist_items_response.get('nextPageToken')

            print(f"Fetched {(page_n + 1) * 50} songs of {playlist_title}. Getting the next page")
            page_n += 1
            if not next_page_token:
                print(f"Fetched all the songs of {playlist_title}")
                break
        except HttpError as e:
            if handle_quota_error(e, f"Fetching songs from playlist '{playlist_title}'"):
                # If quota exceeded, try to use cached data
                try:
                    cached_data = read_json_if_exists("data", "playlist_data_test.json")
                    if cached_data and "playlists" in cached_data and playlist_title in cached_data["playlists"]:
                        print(f"\nUsing cached data for playlist '{playlist_title}'...")
                        return cached_data["playlists"][playlist_title]
                except:
                    pass
                raise  # Re-raise if no cache available
            else:
                raise  # Re-raise non-quota errors
    
    # Save playlist items data for this playlist
    # playlist_data["playlists"][playlist_id] = songs_per_playlist
    return songs_per_playlist

def hyphen_not_in_parenthesis(video_title):
    pattern = r"\(([^)]*?)-([^\)]*)\)"
    match = re.findall(pattern, video_title)
    if match:
        index_of_first_hyphen_title = video_title.find('-')
        index_of_hyphen_match = video_title.find(match[0][0]) + len(match[0][0])
        if index_of_hyphen_match != index_of_first_hyphen_title:
            return True
    elif " -" in video_title:
        return True
    else:
        return False

def extract_video_info(song_title, video_artist):
    song_title, video_artist = filter_name(song_title, video_artist)
    if hyphen_not_in_parenthesis(song_title):
        full_video_title = song_title
        video_artist = song_title.split(' -')[0].strip()
        # print(song_title)
        song_title = song_title.split(' -')[1].strip()
    else:
        full_video_title = video_artist + " - " + song_title

    # Ensure the final file/title consistently includes both artist and song
    # when they are available and not identical.
    if video_artist and song_title and video_artist != song_title:
        full_video_title = f"{video_artist} - {song_title}"
    artists = extract_all_artists(video_artist)
    return full_video_title, song_title, artists


def extract_videos(playlist_data):
    # playlist_data = read_json('data', 'playlist_data_test.json')
    playlist_videos = {}  # Dictionary to store playlist videos
    for playlist_id, playlist in playlist_data["playlists"].items():
        print(f"Processing Playlist ID: {playlist_id}")
        playlist_videos[playlist_id] = []  # Initialize the list for this playlist
        for video in playlist:
            song_title = video['snippet']['title']
            video_id = video['snippet']['resourceId']['videoId']
            video_url = f'https://www.youtube.com/watch?v={video_id}'
            # video_artist = None
            if song_title != "Deleted video" and song_title != "Private video":
                video_artist = video['snippet']['videoOwnerChannelTitle']
            full_video_title, song_title, artists = extract_video_info(song_title, video_artist)

            # Append video info to the playlist's video list
            playlist_videos[playlist_id].append({
                "full_video_title": full_video_title,
                "song_title": song_title,
                "artists": artists,
                "video_url": video_url
            })
    # Write in playlists_with_songs_final.json the info of the youtube playlists in a more readable way         
    write_to_json('data', 'playlists_with_songs_final.json', playlist_videos)
    return playlist_videos


def build_m3u8_index(playlist_m3u8_path, only_playlist: str | None = None):
    """
    Build a global index of all songs already in m3u8 playlists.
    Returns: dict[playlist_name, set(song_titles)]
    """
    playlist_names = list_files_in_directory(playlist_m3u8_path)
    if only_playlist:
        playlist_names = [name for name in playlist_names if name.split('.')[0] == only_playlist]
    
    m3u8_index = {}
    for playlist_m3u8 in playlist_names:
        playlist_m3u8_name = playlist_m3u8.split('.')[0]
        playlist_path = os.path.join(playlist_m3u8_path, playlist_m3u8)
        existing_songs = set()
        if os.path.exists(playlist_path):
            with open(playlist_path, 'r', encoding="utf-8") as existing_m3u8:
                lines = existing_m3u8.readlines()
                for line in lines:
                    if line.startswith("#EXTINF"):
                        song_title = ",".join(line.split(",")[1:]).strip()
                        existing_songs.add(song_title)
        m3u8_index[playlist_m3u8_name] = existing_songs
    return m3u8_index


def build_downloaded_files_index(artists_parent_folder):
    """
    Build a global index of all downloaded files across all artist folders.
    Returns: dict[artist_folder_path, set(lowercase_filenames)]
    This avoids re-scanning the same folders repeatedly.
    """
    downloaded_index = {}
    if not os.path.exists(artists_parent_folder):
        return downloaded_index
    
    for artist_folder_name in os.listdir(artists_parent_folder):
        artist_folder = os.path.join(artists_parent_folder, artist_folder_name)
        if os.path.isdir(artist_folder):
            files = [f.lower() for f in os.listdir(artist_folder) if os.path.isfile(os.path.join(artist_folder, f))]
            downloaded_index[artist_folder] = set(files)
    return downloaded_index


def download_songs(playlists_with_songs_data, youtube_service, only_playlist: str | None = None, dry_run: bool = False):
    # Path to the playlist m3u8 file
    playlist_m3u8_path = get_playlist_m3u8_output_dir()
    artists_parent_folder = os.path.join(os.path.dirname(playlist_m3u8_path), 'Artists')

    # Build indexes once at startup instead of scanning repeatedly
    print("Building indexes of existing files and playlists...")
    m3u8_index = build_m3u8_index(playlist_m3u8_path, only_playlist)
    downloaded_index = build_downloaded_files_index(artists_parent_folder)
    print(f"Indexed {len(m3u8_index)} playlists and {len(downloaded_index)} artist folders")

    # List all the locally saved playlists
    playlist_names = list_files_in_directory(playlist_m3u8_path)
    if only_playlist:
        playlist_names = [name for name in playlist_names if name.split('.')[0] == only_playlist]
    
    for playlist_m3u8 in playlist_names:
        playlist_m3u8_name = playlist_m3u8.split('.')[0] # without the extension
        playlist_path = os.path.join(playlist_m3u8_path, playlist_m3u8)
        
        # Use pre-built index instead of re-reading file
        existing_songs = m3u8_index.get(playlist_m3u8_name, set())

        with open(playlist_path, 'a', encoding="utf-8") as m3u8_file:
            for playlist_in_json in playlists_with_songs_data:
                if playlist_in_json == playlist_m3u8_name:
                    # Uncomment this line if you want to check only one playlist
                # if playlist_in_json == playlist_m3u8_name == "Love in full tempo":
                    for song in playlists_with_songs_data[playlist_in_json]:
                        full_song_title = song['full_video_title']
                        # Check if the song is already in the m3u8 file
                        if full_song_title in existing_songs:
                            print(f'{full_song_title} already exists in {playlist_m3u8}. Skipping!')
                            continue
                        extract_song_info_and_download(
                            song, youtube_service, m3u8_file, 
                            downloaded_index=downloaded_index,
                            dry_run=dry_run
                        )
                        existing_songs.add(full_song_title)
    print("Successfully downloaded all songs")


def extract_song_info_and_download(song, youtube_service, m3u8_file, downloaded_index: dict = None, dry_run: bool = False, recursion_depth: int = 0):
    """
    Extract song info and download if needed. Uses pre-built downloaded_index
    for fast lookups instead of scanning folders repeatedly.
    """
    full_song_title = song['full_video_title']
    song_title = song['song_title']
    artists = song['artists']
    main_artist = extract_main_artist(artists)
    artist_folder = get_artist_folder(main_artist, True)
    file_path = os.path.join(artist_folder, full_song_title)
    
    # Use pre-built index instead of scanning folder every time
    if downloaded_index is not None and artist_folder in downloaded_index:
        existing_files_lower = downloaded_index[artist_folder]
        full_song_title_lower = full_song_title.lower()
        
        # Fast exact match check first
        if f"{full_song_title_lower}.mp3" in existing_files_lower:
            print(f'{full_song_title} already downloaded. Skipping!')
            m3u8_file.write(f"#EXTINF:-1,{full_song_title}\n../Artists/{main_artist}/{full_song_title}.mp3\n")
            return
        
        # Then fuzzy match for similar names (only if needed)
        similar_songs_lower = difflib.get_close_matches(
            full_song_title_lower, 
            list(existing_files_lower), 
            cutoff=0.8
        )
        if similar_songs_lower:
            print(f'{full_song_title} already downloaded (similar: {similar_songs_lower[0]}). Skipping!')
            m3u8_file.write(f"#EXTINF:-1,{full_song_title}\n../Artists/{main_artist}/{full_song_title}.mp3\n")
            return
    else:
        # Fallback: scan folder if index not available (shouldn't happen normally)
        songs_of_artist_list = list_files_in_directory(artist_folder)
        if songs_of_artist_list:
            existing_songs_lower = [song.lower() for song in songs_of_artist_list]
            similar_songs_lower = difflib.get_close_matches(full_song_title.lower(), existing_songs_lower, cutoff=0.8)
            if similar_songs_lower:
                print(f'{full_song_title} already downloaded. Skipping!')
                m3u8_file.write(f"#EXTINF:-1,{full_song_title}\n../Artists/{main_artist}/{full_song_title}.mp3\n")
                return

    if dry_run:
        print(f"[DRY-RUN] Would download {full_song_title} to ../Artists/{main_artist}/{full_song_title}.mp3")
        return

    # if song_title == "Deleted video"
    print(f'Downloading {full_song_title}')
    download_song(song['video_url'], 
                  full_song_title, 
                  song_title, 
                  main_artist, 
                  file_path, 
                  youtube_service, 
                  m3u8_file,
                  recursion_depth=recursion_depth)
    
    # Update the index when we download a new file
    if downloaded_index is not None and artist_folder in downloaded_index:
        downloaded_index[artist_folder].add(f"{full_song_title.lower()}.mp3")
    
    m3u8_file.write(f"#EXTINF:-1,{full_song_title}\n../Artists/{main_artist}/{full_song_title}.mp3\n")



def download_song(video_url, full_song_title, song_title, artist, file_path, youtube_service, m3u8_file, recursion_depth: int = 0):
    ydl_opts = load_ydl_opts_from_json()
    ydl_opts['outtmpl'] = file_path
    
    # file_path = os.path.join(artist, song_title)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        # Guard against looping when artist resolves to "Various Artists"
        if artist == "Various Artists":
            if recursion_depth >= 1:
                print("Artist still 'Various Artists' after lookup; proceeding without further recursion.")
            else:
                detected_artist = (
                    info.get('artist')
                    or info.get('uploader')
                    or info.get('channel')
                    or "Various Artists"
                )
                full_video_title2, song_title2, artists2 = extract_video_info(song_title, detected_artist)
                song2 = {
                    "full_video_title": full_video_title2,
                    "song_title": song_title2,
                    "artists": artists2,
                    "video_url": video_url,
                }
                # Re-enter once with derived artist, then stop to avoid infinite recursion
                extract_song_info_and_download(
                    song2,
                    youtube_service,
                    m3u8_file,
                    downloaded_index=None,
                    dry_run=False,
                    recursion_depth=recursion_depth + 1,
                )
                return
        else:
            try:
                print("Download")
                ydl.download([video_url])
                print("Load")
                # Load the audio file
                audio = mutagen.File(f"{file_path}.mp3", easy=True)

                # Add metadata to the audio file
                audio['title'] = song_title
                audio['artist'] = artist

                # Save the metadata
                audio.save()

                # Delete the .webp file
                if os.path.exists(file_path + ".webp"):
                    os.remove(file_path + ".webp")

                # m3u8_file.write(f"#EXTINF:-1,{full_song_title}\n../Artists/{artist}/{full_song_title}.mp3\n")

                print(f"Added {full_song_title}")
            except Exception as e:
                print(f"Error adding song: {full_song_title}")
                print(e)
                # Attempt to find and download an alternative version, but keep
                # using the original artist/folder and full title so files are
                # placed under the correct artist and named consistently.
                try_download_alternative(
                    video_url=video_url,
                    youtube_service=youtube_service,
                    m3u8_file=m3u8_file,
                    original_full_title=full_song_title,
                    original_song_title=song_title,
                    original_artist=artist,
                )
            

def try_download_alternative(video_url, youtube_service, m3u8_file, original_full_title, original_song_title, original_artist):
    # Use the get_video_details function to get the video title and artist
    print("Get video details")
    video_title, artist = get_video_details(video_url)

    if video_title and artist:
        alternative_video_ids = youtube_search(youtube_service, f"{video_title} {artist}")
        if alternative_video_ids:
            alternative_video_id = alternative_video_ids[0]
            alternative_video_url = f'https://www.youtube.com/watch?v={alternative_video_id}'
            print(f"Downloading alternative version: {alternative_video_url}")

            # Keep using the original artist and titles so the track is stored
            # under the correct artist folder and has a stable name, while only
            # swapping the underlying YouTube URL.
            song = {
                "full_video_title": original_full_title,
                "song_title": original_song_title,
                "artists": [original_artist],
                "video_url": alternative_video_url,
            }
            # Note: downloaded_index not passed here to avoid circular dependency,
            # but the folder will be scanned once if needed (acceptable for fallback case)
            extract_song_info_and_download(song, youtube_service, m3u8_file, downloaded_index=None)
    return False