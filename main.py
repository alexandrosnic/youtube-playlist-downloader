"""CLI entrypoint for the YouTube downloader sub-project."""

import argparse

from app.download_playlist import download_playlist


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run YouTube playlist downloader/sync only.")
    parser.add_argument(
        "--only-playlist",
        dest="only_playlist",
        help="Only process the playlist with this exact title.",
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Do not download files or write playlists; just log what would happen.",
    )
    parser.add_argument(
        "--use-cache",
        dest="use_cache",
        action="store_true",
        help="Use cached API data when available to avoid quota issues.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    download_playlist(
        only_playlist=args.only_playlist,
        dry_run=args.dry_run,
        use_cache=args.use_cache,
    )


if __name__ == "__main__":
    main()
