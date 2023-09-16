
import yt_dlp
import re
import os
import argparse
import mutagen
from mutagen.id3 import ID3, TIT2, TPE1
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import re
import requests

# OAuth scopes required for YouTube API access
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

def get_authenticated_service():
    # Load the credentials from the client_secrets.json file
    flow = InstalledAppFlow.from_client_secrets_file(
        'client_secret_813955237327-jeptn7hq5njdct94osd2d7p95c782au1.apps.googleusercontent.com.json', scopes=SCOPES)
    credentials = flow.run_local_server(port=0)

    # Build the YouTube service using the authenticated credentials
    youtube_service = build('youtube', 'v3', credentials=credentials)
    return youtube_service


def get_common_substring(string1, string2):
    common_substring = ""
    for i in range(len(string1)):
        for j in range(len(string2)):
            if string1[i] == string2[j]:
                # Found a matching character, start checking for common substring
                k = 1
                while (i + k < len(string1) and j + k < len(string2) and
                       string1[i + k] == string2[j + k]):
                    k += 1
                # Check if the found substring is longer than the current common substring
                if k > len(common_substring):
                    common_substring = string1[i:i + k]
    return common_substring


def generate_artist_name(title, artist, uploader, channel):
    if artist:
        artist_or_uploader_or_channel = artist
    elif channel:
        artist_or_uploader_or_channel = channel
    elif uploader:
        artist_or_uploader_or_channel = uploader

    if ' - Topic' in artist_or_uploader_or_channel:
        artist_or_uploader_or_channel = artist_or_uploader_or_channel.replace(" - Topic", "")

    is_substring_artist = any(
        substring in channel for substring in
        (artist_or_uploader_or_channel[i:j] for i in range(len(artist_or_uploader_or_channel)) for j in
         range(i + 1, len(artist_or_uploader_or_channel) + 1)))
    is_substring_title = any(
        substring in channel for substring in (title[i:j] for i in range(len(title)) for j in
                                               range(i + 1, len(title) + 1)))
    common_substring_artist = get_common_substring(artist_or_uploader_or_channel, channel)
    common_substring_title = get_common_substring(title, channel)

    if not is_substring_title:
        if not is_substring_artist:
            if not artist:
                artist_or_uploader_or_channel += f' ({channel})'
            else:
                title += f' ({channel})'

    artist_or_uploader_or_channel = remove_duplicate_names(artist_or_uploader_or_channel)

    return artist_or_uploader_or_channel

def remove_duplicate_names(name):
    # Split the name into individual artists
    artists = name.split(', ')

    # Remove duplicates while preserving the order
    unique_artists = list(dict.fromkeys(artists))

    # Join the unique artists back into a single string
    unique_name = ', '.join(unique_artists)

    return unique_name


def youtube_search(youtube_service, query):
    search_response = youtube_service.search().list(
        q=query,
        part='id',
        maxResults=10
    ).execute()

    videos = search_response.get('items', [])
    video_ids = [video['id']['videoId'] for video in videos if video['id']['kind'] == 'youtube#video']
    return video_ids

def get_video_details(video_url):
    try:
        response = requests.get(video_url)
        if response.status_code == 200:
            html = response.text
            title_match = re.search(r'<title>(.*?)</title>', html)
            artist_match = re.search(r'"author":"(.*?)"', html)

            if title_match and artist_match:
                video_title = title_match.group(1)
                artist = artist_match.group(1)

                return video_title, artist
            else:
                print("Unable to retrieve video details.")
        else:
            print(f"Error: {response.status_code} - {response.reason}")
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving video page: {str(e)}")

    return None, None

def try_download_alternate(youtube_service, ydl, ydl_opts, video_url, playlist_folder, downloaded_songs, downloaded_file_path):
    # Use the get_video_details function to get the video title and artist
    video_title, artist = get_video_details(video_url)

    if video_title and artist:
        # Search for the first alternate version based on the video title and artist
        alternate_video_ids = youtube_search(youtube_service, f"{video_title} {artist}")
        if alternate_video_ids:
            alternate_video_id = alternate_video_ids[0]
            alternate_video_url = f'https://www.youtube.com/watch?v={alternate_video_id}'
            print(f"Downloading alternate version: {alternate_video_url}")

            try:
                if try_download(ydl, ydl_opts, alternate_video_url, playlist_folder, downloaded_songs, downloaded_file_path):
                    return True
            except Exception as e:
                print(f"Error downloading alternate video: {alternate_video_url}")
                print(e)

    return False

def finalize_file_name(artist_or_uploader_or_channel, title, artist):
    if artist_or_uploader_or_channel in title:
        file_name = f'{title}'
    elif not artist:
        file_name = f'{title} - {artist_or_uploader_or_channel}'
    else:
        file_name = f'{artist_or_uploader_or_channel} - {title}'

    file_name = file_name.replace('\x92', '')
    file_name = file_name.replace('\u0301', '')

    file_name = re.sub(r'[\/:*?"<>#|’]', '-', file_name)
    encoded_title = file_name.encode('utf-8', 'ignore')
    file_name = encoded_title.decode('utf-8')

    # Remove trailing spaces and dot from file_name
    file_name = file_name.rstrip('. ').strip()

    return file_name

def try_download(ydl, ydl_opts, video_url, playlist_folder, downloaded_songs, downloaded_file_path):

    info_dict = ydl.extract_info(video_url, download=False)
    title = info_dict['title']
    uploader = info_dict['uploader']
    channel = info_dict['channel']
    try:
        artist = info_dict['artist']
    except KeyError:
        artist = None

    artist_or_uploader_or_channel = generate_artist_name(title, artist, uploader, channel)

    file_name = finalize_file_name(artist_or_uploader_or_channel, title, artist)
    
    file_path = os.path.join(playlist_folder, file_name)

    # Check if song is already downloaded
    if file_name not in downloaded_songs:
        print(f"{file_name} is not yet downloaded. Download it now")

        try:
            tmp_ops = ydl_opts.copy()
            tmp_ops['outtmpl'] = file_path
            # tmp_ops['no-flat-playlist'] = True
            # tmp_ops['flat-playlist'] = False

            # Download the wav file
            with yt_dlp.YoutubeDL(tmp_ops) as ydl:
                ydl.download([video_url])

                # Load the audio file
                audio = mutagen.File(f"{file_path}.wav", easy=True)

                # Add metadata to the audio file
                audio['title'] = title
                audio['artist'] = artist_or_uploader_or_channel

                # Save the metadata
                audio.save()

            # Delete the .webp file
            if os.path.exists(file_path + ".webp"):
                os.remove(file_path + ".webp")

            downloaded_songs.append(file_name)
            # Write the downloaded songs to the text file
            with open(downloaded_file_path, "w") as f:
                f.write("\n".join(downloaded_songs))

            print(f"Added {file_name}")
        except Exception as e:
            print(f"Error adding song: {file_name}")
            print(e)
    else:
        print(f"Skipped already downloaded song: {file_name}")
        return True
    return False

def get_downloaded_songs_file(playlist_folder):
    # Text file to keep track of downloaded songs
    downloaded_songs_file = "downloaded_songs.txt"
    # Create the downloaded songs text file if it doesn't exist
    downloaded_file_path = os.path.join(playlist_folder, downloaded_songs_file)
    if not os.path.exists(downloaded_file_path):
        open(downloaded_file_path, "w").close()

    # Load downloaded songs from text file
    with open(downloaded_file_path, "r") as f:
        downloaded_songs = f.read().splitlines()

    return downloaded_songs, downloaded_file_path

def fetch_playlist(playlist, youtube_service, skip_playlist):
    playlist_id = playlist['id']
    playlist_title = playlist['snippet']['title']
    playlist_folder = f"D:/XIAOMI ALEX/Music/Download/{playlist_title}"

    print(f"Fetching {playlist_title} playlist")

    if (playlist_title == "Alternative - Chill Deep House Music" or
        playlist_title == "Salsa moves" or
        playlist_title == "SpC18 The Transport Network" or
        playlist_title == "Guitar Playlist" or
        playlist_title == "Greek Alternative" or
        playlist_title == "Feeling Good" or
        playlist_title == "Winter Recap '23" or
        playlist_title == "2022 Recap" or
        playlist_title == "Fall Recap '22" or
        playlist_title == "Stuck in the music" or
        playlist_title == "Dynamic Playlist" or
        playlist_title == "Liked videos"):
        skip_playlist = True
    os.makedirs(playlist_folder, exist_ok=True)

    # Get all the videos in the playlist
    playlist_items_response = youtube_service.playlistItems().list(
        part='snippet',
        playlistId=playlist_id,
        maxResults=200
    ).execute()

    return playlist_items_response, playlist_folder, skip_playlist

def find_playlists_and_download(youtube_service):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': '%(title)s - %(artist_or_uploader_or_channel)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '320',
        }],
        'add-metadata': True,
        'nooverwrites': True,
        'concurrent-fragments': 20,
        'embed-metadata': True,
        'ignoreerrors': True, # include this if you want to ignore download errors
        'ciw': True, # include this for case-insensitive filename matching
        'no_mtime': True, # include this to not use the Last-Modified header to set the file modification time
        'quiet': False,  # Make sure to set quiet to False to see potential error messages
        # 'flat-playlist': True,
        #'downloader': 'dash,m3u8:native',
        #'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',

    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        # Retrieve all playlists for the authorized user's YouTube channel
        playlists = []
        next_page_token = None

        while True:
            response = youtube_service.playlists().list(
                part='snippet',
                mine=True,
                maxResults=50,  # Adjust the number of results per page as desired
                pageToken=next_page_token
            ).execute()

            playlists.extend(response['items'])
            next_page_token = response.get('nextPageToken')

            if not next_page_token:
                break

        # Check each playlist for the specified playlist ID
        for playlist in playlists:
            skip_playlist = False
            playlist_items_response, playlist_folder, skip_playlist = fetch_playlist(playlist, youtube_service, skip_playlist)
            if skip_playlist:
                continue

            downloaded_songs, downloaded_file_path = get_downloaded_songs_file(playlist_folder)

            for video in playlist_items_response['items']:
                video_id = video['snippet']['resourceId']['videoId']
                video_url = f'https://www.youtube.com/watch?v={video_id}'

                try:
                    if try_download(ydl, ydl_opts, video_url, playlist_folder, downloaded_songs, downloaded_file_path):
                        continue

                except Exception as e:
                    print(f"Error downloading video: {video_url}")
                    print(e)
                    print(f"Searching for alternate versions...")

                    # If the primary video download fails, try to download an alternate version
                    try:
                        if try_download_alternate(youtube_service, ydl, ydl_opts, video_url, playlist_folder, downloaded_songs, downloaded_file_path):
                            continue
                    except Exception as e:
                        print(f"Error again downloading video: {video_url}")
                        print(e)



def main():
    youtube_service = get_authenticated_service()
    find_playlists_and_download(youtube_service)


if __name__ == "__main__":
    main()
