"""
YouTube API quota management and error handling.
"""

from googleapiclient.errors import HttpError
import time
import os
from datetime import datetime, timedelta
from utils.utils import read_json, read_json_if_exists, write_to_json


def handle_quota_error(e: HttpError, operation_name: str = "API request"):
    """
    Handle YouTube API quota exceeded errors with helpful messages.
    
    :param e: The HttpError exception
    :param operation_name: Description of what was being done
    :return: True if it's a quota error, False otherwise
    """
    if e.resp.status == 403:
        error_details = e.error_details[0] if e.error_details else {}
        if error_details.get('reason') == 'quotaExceeded':
            print("\n" + "=" * 60)
            print("⚠️  YOUTUBE API QUOTA EXCEEDED")
            print("=" * 60)
            print(f"\nOperation: {operation_name}")
            print("\nSolutions:")
            print("1. Request quota increase:")
            print("   - Go to: https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas")
            print("   - Click 'Edit Quotas' and request an increase")
            print("   - Default is 10,000 units/day")
            print("\n2. Use offline mode (if you have cached data):")
            print("   - Run with --use-cache flag")
            print("   - Or use existing data/*.json files")
            print("\n3. Wait for quota reset:")
            print("   - Quota resets daily at midnight Pacific Time")
            print("   - Current time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            print("\n4. Reduce API calls:")
            print("   - Process fewer playlists at once")
            print("   - Use --only-playlist to process one at a time")
            print("   - Avoid running multiple times per day")
            print("\n5. Check your quota usage:")
            print("   - https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas")
            print("=" * 60 + "\n")
            return True
    return False


def add_rate_limit_delay():
    """
    Add a small delay between API calls to avoid hitting rate limits.
    """
    time.sleep(0.1)  # 100ms delay between calls


def check_cached_data_available(playlist_title: str | None = None) -> bool:
    """
    Check if cached playlist data is available to use instead of API calls.
    
    :param playlist_title: Optional playlist title to check
    :return: True if cached data exists
    """
    cache_files = [
        "data/playlists.json",
        "data/playlist_data_test.json",
        "data/playlists_with_songs_final.json"
    ]
    
    for cache_file in cache_files:
        if os.path.exists(cache_file):
            try:
                data = read_json_if_exists("data", os.path.basename(cache_file))
                if playlist_title:
                    # Check if specific playlist exists in cache
                    if isinstance(data, dict) and "playlists" in data:
                        if playlist_title in data["playlists"]:
                            return True
                else:
                    # Any cached data is good
                    if data:
                        return True
            except:
                pass
    
    return False


def get_quota_usage_info():
    """
    Get information about quota usage (if available from API).
    Note: YouTube API doesn't provide real-time quota usage, but we can estimate.
    """
    # YouTube API doesn't expose quota usage directly
    # But we can track our own usage
    return read_json_if_exists("data", "quota_usage.json")


