import yt_dlp
import re
import os
import argparse
import mutagen
from mutagen.id3 import ID3, TIT2, TPE1

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
    # print(uploader)
    # print(channel)
    # Determine the artist or uploader or channel
    if artist:
        artist_or_uploader_or_channel = artist
        # print("00")
    elif channel:
        artist_or_uploader_or_channel = channel
        # print("11")
    elif uploader:
        artist_or_uploader_or_channel = uploader
        # print("22")

    # Remove " - Topic" from the channel name, if present
    if ' - Topic' in artist_or_uploader_or_channel:
        artist_or_uploader_or_channel = artist_or_uploader_or_channel.replace(" - Topic", "")
        # print("33")
        # print(artist_or_uploader_or_channel)

    # Split channel_name into all possible substrings
    # substrings = [channel[i:j] for i in range(len(channel)) for j in range(i + 1, len(channel) + 1)]
    # Check if any substring is present in artist_name
    is_substring_artist = any(substring in channel for substring in (artist_or_uploader_or_channel[i:j] for i in range(len(artist_or_uploader_or_channel)) for j in range(i + 1, len(artist_or_uploader_or_channel) + 1)))
    is_substring_title = any(substring in channel for substring in (title[i:j] for i in range(len(title)) for j in range(i + 1, len(title) + 1)))
    common_substring_artist = get_common_substring(artist_or_uploader_or_channel, channel)
    common_substring_title = get_common_substring(title, channel)

    # print(is_substring_artist)
    # print(is_substring_title)
    # print(substrings)
    #
    # # Check if any substring is present in artist_name
    # is_part_of_artist_name = any(substring.replace(" ", "").lower() in artist_or_uploader_or_channel.replace(" ", "").lower() for substring in substrings)
    # is_part_of_title_name = any(substring.replace(" ", "").lower() in title.replace(" ", "").lower() for substring in substrings)


    # Add the channel name to the artist_or_uploader_or_channel, if not already included
    if not is_substring_title:
        if not is_substring_artist:
            if not artist:
                # Maybe I can delete this
                artist_or_uploader_or_channel += f' ({channel})'
            else:
                title += f' ({channel})'
            # print("55")
            # print(title)

    # If title: Cowboys on Acid, uploader: Project, artist: None, then Name: Project - Cowboys on Acid
    # If title: Joachim Pastor - Kenia, uploader: MrSuicideSheep, artist: None, then name: MrSuicideSheep - Joachim Pastor - Kenia (5 cases in african voices)
    # I cannot comply with both cases
    # print(artist_or_uploader_or_channel)

    return artist_or_uploader_or_channel


def download_mp3(video_url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': '%(title)s - %(artist_or_uploader_or_channel)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }],
        'add-metadata': True,
        'nooverwrites': True,
        'concurrent-fragments': 10,
        'embed-metadata': True,
        'ignoreerrors': True, # include this if you want to ignore download errors
        'ciw': True, # include this for case-insensitive filename matching
        'no_mtime': True, # include this to not use the Last-Modified header to set the file modification time
        #'headers': {
        #    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        #},
    }


    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        playlist = ydl.extract_info(video_url, download=False)

        if "playlist?list=" in video_url:
            playlist_title = playlist.get('title', '')
            playlist_folder = f"D:/XIAOMI ALEX/Music/Download/{playlist_title}"
            os.makedirs(playlist_folder, exist_ok=True)

            # Text file to keep track of downloaded songs
            downloaded_songs_file = "downloaded_songs.txt"
            # Create the downloaded songs text file if it doesn't exist
            downloaded_file_path = os.path.join(playlist_folder, downloaded_songs_file)
            if not os.path.exists(downloaded_file_path):
                open(downloaded_file_path, "w").close()

            # Load downloaded songs from text file
            with open(downloaded_file_path, "r") as f:
                downloaded_songs = f.read().splitlines()

            for video in playlist['entries']:
                try:
                    # info = ydl.extract_info(video_url, download=False)
                    title = video.get('title', '')
                    artist = video.get('artist', '')
                    uploader = video.get('uploader', '')
                    channel = video.get('channel', '')

                    artist_or_uploader_or_channel = generate_artist_name(title, artist, uploader, channel)

                    if artist_or_uploader_or_channel in title:
                        file_name = f'{title}'
                    elif not artist:
                        file_name = f'{title} - {artist_or_uploader_or_channel}'
                    else:
                        file_name = f'{artist_or_uploader_or_channel} - {title}'

                    # Add the channel name to the artist_or_uploader_or_channel, if not already included
                    # if channel and channel.replace(" ", "").lower() not in artist_or_uploader_or_channel.replace(" ", "").lower():
                    #     artist_or_uploader_or_channel += f' ({channel})'
                    #     print("55")
                    #     print(artist_or_uploader_or_channel)




                    # Remove artist name from title, if it is already included
                    # if artist and artist in title:
                    #     title = re.sub(f' - {artist}', '', title, flags=re.IGNORECASE)
                    #     print("44")



                    #
                    # if artist_or_uploader_or_channel in title:
                    #     file_name = f'{title}'
                    # else:
                    #     file_name = f'{artist_or_uploader_or_channel} - {title}'
                    file_name = re.sub(r'[\/:*?"<>.|#]', '-', file_name)
                    # Check if song is already downloaded
                    if file_name not in downloaded_songs:
                        try:
                            downloaded_songs.append(file_name)
                            print(f"Added {file_name}")
                        except Exception as e:
                            print(f"Error adding song: {file_name}")
                            print(e)
                    else:
                        print(f"Skipped already downloaded song: {file_name}")
                        continue
                    file_path = os.path.join(playlist_folder, file_name)
                    print(file_path)

                    tmp_ops = ydl_opts.copy()
                    tmp_ops['outtmpl'] = file_path

                    # # Download the mp3 file
                    with yt_dlp.YoutubeDL(tmp_ops) as ydl:
                        ydl.download([video['webpage_url']])

                        # Load the audio file
                        audio = mutagen.File(f"{file_path}.mp3", easy=True)

                        # Add metadata to the audio file
                        audio['title'] = title
                        audio['artist'] = artist_or_uploader_or_channel

                        # Save the metadata
                        audio.save()

                    # Delete the .webp file
                    if os.path.exists(file_path + ".webp"):
                        os.remove(file_path + ".webp")

                except AttributeError:
                    print(f"Failed to extract information for video")

            # Write downloaded songs to text file
            with open(downloaded_file_path, "w") as f:
                f.write("\n".join(downloaded_songs))
                print(f"Downloaded songs list updated.")

        else:
            info_dict = ydl.extract_info(video_url, download=False)
            title = info_dict['title']
            uploader = info_dict['uploader']
            channel = info_dict['channel']
            try:
                artist = info_dict['artist']
            except KeyError:
                artist = None
            playlist_folder = f"D:/XIAOMI ALEX/Music/Download/NA"

            artist_or_uploader_or_channel = generate_artist_name(title, artist, uploader, channel)

            if artist_or_uploader_or_channel in title:
                file_name = f'{title}'
            else:
                file_name = f'{artist_or_uploader_or_channel} - {title}'










            # Remove artist name from title, if it is already included
            # if artist and artist in title:
            #     title = re.sub(f' - {artist}', '', title, flags=re.IGNORECASE)
            #     print("44")





            file_name = re.sub(r'[\/:*?"<>|]', '-', file_name)
            file_path = os.path.join(playlist_folder, file_name)
            print(file_path)

            tmp_ops = ydl_opts.copy()
            tmp_ops['outtmpl'] = file_path

            # # Download the mp3 file
            with yt_dlp.YoutubeDL(tmp_ops) as ydl:
                ydl.download([video_url])

                # Load the audio file
                audio = mutagen.File(f"{file_path}.mp3", easy=True)

                # Add metadata to the audio file
                audio['title'] = title
                audio['artist'] = artist_or_uploader_or_channel

                # Save the metadata
                audio.save()

            # Delete the .webp file
            if os.path.exists(file_path + ".webp"):
                os.remove(file_path + ".webp")



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download best quality mp3 from a video')
    parser.add_argument('url', metavar='URL', type=str, help='video url')

    args = parser.parse_args()

    download_mp3(args.url)
