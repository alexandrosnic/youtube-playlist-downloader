# YouTube Playlist Downloader

Downloads tracks from your YouTube playlists, organizes files by artist, and updates local m3u8 playlists.

## Entrypoint
- main.py

## Run
```pwsh
python3 main.py
```

## Setup
```pwsh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

# create local config from templates
cp config/google_api_config.json.example config/google_api_config.json
cp config/playlist_path.json.example config/playlist_path.json
cp config/ytdlp_config.json.example config/ytdlp_config.json
cp config/skipped_playlists.json.example config/skipped_playlists.json
```

## OAuth on headless Linux
When running in a terminal-only environment, the app does not auto-open a browser.
It prints a Google authorization URL in the terminal.

1. Copy the printed URL and open it in any browser (local machine or another device).
2. Sign in and approve access.
3. Keep the Python process running while completing auth so the localhost callback can finish.

If you stop the process manually, you may see exit code `130` (interrupted run).

Create local config files (already scaffolded) and fill your values:
- config/google_api_config.json
- config/playlist_path.json
- config/ytdlp_config.json
- config/skipped_playlists.json

Keep these local and uncommitted. Use the `*.example` files as shareable templates.

## Useful options
- --only-playlist "Playlist Name"
- --dry-run
- --use-cache

## Project structure
- app/
- utils/
- config/
- data/

The `data/` folder only stores runtime cache/output JSON files. Those files are created lazily during runs and should stay local and uncommitted.

This folder is self-contained and can be published as its own repository.

## Related repositories
- Rekordbox sync: `git@github.com:alexandrosnic/rekordbox-playlist-sync.git`
- Orchestration suite: `git@github.com:alexandrosnic/playlist-sync-suite.git`

If you want to run all projects together from a clean workspace:

```pwsh
mkdir playlist-sync-workspace
cd playlist-sync-workspace
git clone git@github.com:alexandrosnic/youtube-playlist-downloader.git youtube
git clone git@github.com:alexandrosnic/rekordbox-playlist-sync.git rekordbox
git clone git@github.com:alexandrosnic/playlist-sync-suite.git playlist_sync_suite
```

## Public safety checklist
- Never commit `config/client_secret_*.json`, local `config/*.json` runtime config, or `cookies*.txt`.
- Ensure only `config/*.example` template files are committed.
- If credentials were ever exposed, rotate them in Google Cloud before publishing.
