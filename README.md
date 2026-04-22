# YouTube Playlist Downloader

Downloads tracks from your YouTube playlists, organizes audio files by artist, and writes/updates local `.m3u8` playlists.

Works standalone. For Rekordbox XML sync, pair it with:
- https://github.com/alexandrosnic/rekordbox-playlist-sync

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

cp config/google_api_config.json.example config/google_api_config.json
cp config/playlist_path.json.example config/playlist_path.json
cp config/ytdlp_config.json.example config/ytdlp_config.json
cp config/skipped_playlists.json.example config/skipped_playlists.json
```

## Required config values
Fill only these essentials:

1. `config/google_api_config.json`
- `google_api.client_secret_file`: filename of your OAuth client secret JSON placed in `config/`
- `google_api.scopes`: keep default unless you know you need different scopes

2. `config/playlist_path.json`
- `youtube_paths.youtube_playlist_m3u8_dir`: folder where playlist `.m3u8` files are saved

3. `config/ytdlp_config.json`
- `cookiefile`: absolute path to your local `cookies.txt`
- `download_archive`: keep as `data/download_archive.txt` to skip already-downloaded YouTube video IDs quickly
- Other defaults are usually fine

4. `config/skipped_playlists.json`
- JSON array of playlist titles (in your channel) to ignore, e.g. `["Playlist A", "Playlist B"]`

## Run
```bash
python3 main.py
```

On headless Linux, the app prints an OAuth URL. Open it in a browser, complete auth, and keep the process running until callback finishes.

## CLI options
- `--only-playlist "Playlist Name"`: process only one playlist (exact title match)
- `--dry-run`: no downloads and no playlist writes; logs what would happen
- `--use-cache`: use cached files in `data/` when available to reduce API quota usage

## Notes
- Runtime cache/output JSON files are created in `data/`
- Keep local runtime config/credentials out of git (`config/*.json`, `cookies*.txt`, client secret JSON)

## Related repositories
- https://github.com/alexandrosnic/youtube-playlist-downloader
- https://github.com/alexandrosnic/rekordbox-playlist-sync
- https://github.com/alexandrosnic/playlist-sync-suite
