"""
Instagram scraper for Simchaspot engagement announcements.

Supports two modes:
1. Meta Graph API (requires access token) - preferred, compliant
2. Public web scraping fallback (no auth needed) - for development/testing
"""

import re
import json
import urllib.request
import urllib.error
from datetime import datetime
from database import get_db


def parse_engagement_caption(caption: str) -> dict | None:
    """
    Parse an engagement announcement caption from Simchaspot.
    Common formats:
        "Engagement of Moshe Cohen and Sarah Levy"
        "Engagement of Moshe and Sarah #simchaspot"
        "Engagement of Moshe Cohen & Sarah Levy! #simchaspot"
    """
    if not caption:
        return None

    # Normalize
    text = caption.strip()

    # Match "Engagement of X and/& Y"
    pattern = r'[Ee]ngagement\s+of\s+(.+?)\s+(?:and|&)\s+(.+?)(?:\s*[#!.\n]|$)'
    match = re.search(pattern, text)
    if not match:
        return None

    chatan_raw = match.group(1).strip()
    kallah_raw = match.group(2).strip()

    # Clean up trailing punctuation
    chatan_raw = re.sub(r'[!.,;:]+$', '', chatan_raw).strip()
    kallah_raw = re.sub(r'[!.,;:]+$', '', kallah_raw).strip()

    # Split into first/last name
    chatan_parts = chatan_raw.split()
    kallah_parts = kallah_raw.split()

    return {
        'chatan_first': chatan_parts[0] if chatan_parts else chatan_raw,
        'chatan_last': ' '.join(chatan_parts[1:]) if len(chatan_parts) > 1 else None,
        'kallah_first': kallah_parts[0] if kallah_parts else kallah_raw,
        'kallah_last': ' '.join(kallah_parts[1:]) if len(kallah_parts) > 1 else None,
    }


def fetch_via_graph_api(access_token: str, ig_user_id: str, limit: int = 20) -> list[dict]:
    """
    Fetch recent posts from Simchaspot via Meta Graph API.
    Requires an Instagram Business/Creator account access token.
    """
    url = (
        f"https://graph.facebook.com/v19.0/{ig_user_id}/media"
        f"?fields=id,caption,timestamp,permalink"
        f"&limit={limit}"
        f"&access_token={access_token}"
    )

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Graph API error: {e.code} - {e.read().decode()}")
        return []

    posts = []
    for item in data.get('data', []):
        caption = item.get('caption', '')
        parsed = parse_engagement_caption(caption)
        if parsed:
            parsed['source_url'] = item.get('permalink', '')
            parsed['source_caption'] = caption
            parsed['post_date'] = item.get('timestamp', '')
            posts.append(parsed)

    return posts


def fetch_via_web(username: str = 'simchaspot', limit: int = 20) -> list[dict]:
    """
    Fallback: fetch posts via Instagram's public web interface.
    Note: Instagram may block automated requests. Use Graph API for production.
    """
    url = f"https://www.instagram.com/{username}/?__a=1&__d=dis"

    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
        })
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"Web fetch error: {e}")
        return []

    posts = []
    edges = (
        data.get('graphql', {})
        .get('user', {})
        .get('edge_owner_to_timeline_media', {})
        .get('edges', [])
    )

    for edge in edges[:limit]:
        node = edge.get('node', {})
        caption_edges = node.get('edge_media_to_caption', {}).get('edges', [])
        caption = caption_edges[0]['node']['text'] if caption_edges else ''

        parsed = parse_engagement_caption(caption)
        if parsed:
            shortcode = node.get('shortcode', '')
            parsed['source_url'] = f"https://www.instagram.com/p/{shortcode}/" if shortcode else ''
            parsed['source_caption'] = caption
            parsed['post_date'] = datetime.fromtimestamp(
                node.get('taken_at_timestamp', 0)
            ).isoformat() if node.get('taken_at_timestamp') else ''
            posts.append(parsed)

    return posts


def save_engagements(engagements: list[dict]) -> int:
    """Save parsed engagements to database. Returns count of new entries."""
    conn = get_db()
    cursor = conn.cursor()
    new_count = 0

    for eng in engagements:
        # Check for duplicates (same names + same source URL)
        cursor.execute("""
            SELECT id FROM engagements
            WHERE chatan_first = ? AND kallah_first = ?
            AND (source_url = ? OR (chatan_last = ? AND kallah_last = ?))
        """, (
            eng['chatan_first'], eng['kallah_first'],
            eng.get('source_url', ''),
            eng.get('chatan_last', ''), eng.get('kallah_last', '')
        ))

        if cursor.fetchone() is None:
            cursor.execute("""
                INSERT INTO engagements
                (chatan_first, chatan_last, kallah_first, kallah_last,
                 source_url, source_caption, post_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                eng['chatan_first'], eng.get('chatan_last'),
                eng['kallah_first'], eng.get('kallah_last'),
                eng.get('source_url', ''), eng.get('source_caption', ''),
                eng.get('post_date', '')
            ))
            new_count += 1

    conn.commit()
    conn.close()
    return new_count


def scrape_and_save(access_token: str = None, ig_user_id: str = None) -> dict:
    """
    Main entry point: scrape Simchaspot and save new engagements.
    Uses Graph API if credentials provided, otherwise falls back to web scraping.
    """
    if access_token and ig_user_id:
        print("Fetching via Meta Graph API...")
        engagements = fetch_via_graph_api(access_token, ig_user_id)
    else:
        print("No API credentials - using web fallback...")
        engagements = fetch_via_web()

    new_count = save_engagements(engagements)

    return {
        'total_found': len(engagements),
        'new_saved': new_count,
        'scraped_at': datetime.now().isoformat()
    }


# Manual entry support
def add_engagement_manual(chatan_first, chatan_last, kallah_first, kallah_last,
                          source_url='', post_date=''):
    """Add an engagement manually (e.g., from visual inspection of Instagram)."""
    engagements = [{
        'chatan_first': chatan_first,
        'chatan_last': chatan_last,
        'kallah_first': kallah_first,
        'kallah_last': kallah_last,
        'source_url': source_url,
        'source_caption': 'Manual entry',
        'post_date': post_date or datetime.now().isoformat(),
    }]
    return save_engagements(engagements)
