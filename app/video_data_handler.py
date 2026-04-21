"""Helpers for working with YouTube/track metadata and generating file names."""

import re


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


def remove_duplicate_names(name):
    # Split the name into individual artists
    artists = name.split(', ')

    # Remove duplicates while preserving the order
    unique_artists = list(dict.fromkeys(artists))

    # Join the unique artists back into a single string
    unique_name = ', '.join(unique_artists)

    return unique_name


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
    print(common_substring_artist)
    print(common_substring_title)

    if not is_substring_title:
        if not is_substring_artist:
            if not artist:
                artist_or_uploader_or_channel += f' ({channel})'
            else:
                title += f' ({channel})'

    artist_or_uploader_or_channel = remove_duplicate_names(artist_or_uploader_or_channel)

    return artist_or_uploader_or_channel
