from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

# Set up OAuth 2.0 credentials
flow = InstalledAppFlow.from_client_secrets_file('client_secret_813955237327-jeptn7hq5njdct94osd2d7p95c782au1.apps.googleusercontent.com.json', scopes=['https://www.googleapis.com/auth/youtube.force-ssl'])
credentials = flow.run_local_server(port=8080)

# Create a YouTube API service
youtube = build('youtube', 'v3', credentials=credentials)

# Retrieve all playlists for the authorized user's YouTube channel
playlists = []
next_page_token = None

while True:
    response = youtube.playlists().list(
        part='snippet',
        mine=True,
        maxResults=50,  # Adjust the number of results per page as desired
        pageToken=next_page_token
    ).execute()

    playlists.extend(response['items'])
    next_page_token = response.get('nextPageToken')

    if not next_page_token:
        break

# Process the retrieved playlists
for playlist in playlists:
    playlist_title = playlist['snippet']['title']
    print(playlist_title)
