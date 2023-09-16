import re
import requests

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

# Example usage
video_url = 'https://www.youtube.com/watch?v=2SezJPxU-F4&ab_channel=SkinonSkin-Topic'
video_title, artist = get_video_details(video_url)

if video_title and artist:
    print(f"Video Title: {video_title}")
    print(f"Artist: {artist}")
else:
    print("Unable to retrieve video details.")
