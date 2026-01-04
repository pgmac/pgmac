#!/usr/bin/env python3
"""
GitHub Profile README Generator.

This module automatically updates a GitHub profile README with dynamic content from:
- Hacker News favorites (synced to Link Ace)
- YouTube playlist videos (synced to Link Ace)
- Recent links from Link Ace
- GitHub starred repositories
- Blog posts from RSS feed
"""

from os import environ

import feedparser
import requests
from bs4 import BeautifulSoup


def fetch_hn_favorites(username="pgmac", max_count=10, timeout=30):
    """Fetch favorite links from Hacker News.

    Args:
        username: HN username
        max_count: Maximum number of favorites to retrieve
        timeout: Request timeout in seconds

    Returns:
        list: List of dicts containing favorite information
    """
    favorites = []
    try:
        url = f"https://news.ycombinator.com/favorites?id={username}"
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.find_all("tr", class_="athing")

        for item in items[:max_count]:
            item_id = item.get("id", "")
            titleline = item.find("span", class_="titleline")
            if not titleline:
                continue

            link_tag = titleline.find("a")
            if not link_tag:
                continue

            title = link_tag.get_text(strip=True)
            link_url = link_tag.get("href", "")

            if link_url:
                hn_url = (
                    f"https://news.ycombinator.com/item?id={item_id}"
                    if item_id
                    else None
                )
                favorites.append({"title": title, "url": link_url, "hn_url": hn_url})

    except requests.RequestException as e:
        print(f"Error fetching HN favorites: {e}")
    except Exception as e:
        print(f"Error parsing HN favorites: {e}")

    return favorites


def find_existing_link_by_url(url, timeout=30):
    """Find an existing link in LinkAce by URL.

    Args:
        url: URL to search for
        timeout: Request timeout in seconds

    Returns:
        int or None: Link ID if found, None otherwise
    """
    api_url = "https://links.pgmac.net.au/api/v2/links"
    headers = {
        "Authorization": f"Bearer {environ.get('PGLINKS_KEY')}",
        "accept": "application/json",
    }
    # Search for the existing link
    params = {"per_page": 100, "order_by": "created_at", "order_dir": "desc"}

    try:
        response = requests.get(
            api_url, headers=headers, params=params, timeout=timeout
        )
        response.raise_for_status()

        links_data = response.json()
        links = links_data.get("data", [])

        # Find exact URL match
        for link in links:
            if link.get("url") == url:
                link_id = link.get("id")
                print(f"  → Found existing link ID: {link_id}")
                return link_id

        print(f"  → Could not find existing link for URL: {url}")
        return None

    except requests.RequestException as e:
        print(f"  ✗ Error searching for existing link: {e}")
        return None


def add_link_to_linkace(url, title, tags=None, timeout=30):
    """Add a link to Link Ace, or find existing link ID if duplicate.

    Args:
        url: Link URL
        title: Link title
        tags: List of tag names or IDs
        timeout: Request timeout in seconds

    Returns:
        tuple: (link_id, was_created) where link_id is int or None, was_created is bool
    """
    api_url = "https://links.pgmac.net.au/api/v2/links"
    headers = {
        "Authorization": f"Bearer {environ.get('PGLINKS_KEY')}",
        "accept": "application/json",
        "Content-Type": "application/json",
    }

    data = {"url": url, "title": title, "visibility": 1}

    if tags:
        data["tags"] = tags

    try:
        response = requests.post(api_url, headers=headers, json=data, timeout=timeout)
        response.raise_for_status()
        link_data = response.json()

        # Try to get ID from root level first, then fall back to nested data structure
        link_id = link_data.get("id") or link_data.get("data", {}).get("id")
        if link_id:
            print(f"✓ Added: {title} (ID: {link_id})")
            return (link_id, True)

        print(f"✗ Link created but no ID found in response for: {title}")
        print(f"  → Response structure: {link_data}")
        return (None, False)

    except requests.HTTPError as e:
        # Check if it's a duplicate URL error
        if e.response.status_code == 422:
            try:
                error_data = e.response.json()
                error_str = str(error_data).lower()

                # Check for various duplicate indicators
                if "url" in error_str and (
                    "taken" in error_str
                    or "exists" in error_str
                    or "duplicate" in error_str
                ):
                    print(f"- Already exists: {title}")
                    # Try to find the existing link ID
                    existing_link_id = find_existing_link_by_url(url)
                    return (existing_link_id, False)

                print(f"✗ 422 validation error (not duplicate): {title}")
                print(f"  → Error details: {error_data}")
                return (None, False)
            except ValueError:
                print(f"✗ Could not parse 422 error response for: {title}")
                return (None, False)

        print(f"✗ HTTP Error {e.response.status_code} adding '{title}': {e}")
        return (None, False)
    except requests.RequestException as e:
        print(f"✗ Request error adding '{title}': {e}")
        return (None, False)


def add_note_to_link(link_id, note_text, visibility=1, timeout=30):
    """Add a note to a Link Ace link.

    Args:
        link_id: ID of the link to add the note to
        note_text: Text content of the note
        visibility: Note visibility (1=public, 2=internal, 3=private)
        timeout: Request timeout in seconds

    Returns:
        bool: True if successful, False otherwise
    """
    api_url = "https://links.pgmac.net.au/api/v2/notes"
    headers = {
        "Authorization": f"Bearer {environ.get('PGLINKS_KEY')}",
        "accept": "application/json",
        "Content-Type": "application/json",
    }

    data = {"link_id": link_id, "note": note_text, "visibility": visibility}

    try:
        response = requests.post(api_url, headers=headers, json=data, timeout=timeout)
        response.raise_for_status()
        print(f"  ✓ Added note to link {link_id}")
        return True
    except requests.RequestException as e:
        print(f"  ✗ Error adding note to link {link_id}: {e}")
        return False


def sync_hn_favorites_to_linkace(username="pgmac", max_count=10):
    """Fetch HN favorites and add them to Link Ace with 'hackernews' tag and HN URL as note.

    Args:
        username: HN username
        max_count: Maximum number of favorites to sync
    """
    print(f"\nSyncing top {max_count} HN favorites to Link Ace...")
    favorites = fetch_hn_favorites(username, max_count)

    if not favorites:
        print("No favorites found to sync.")
        return

    added_count = 0
    notes_added = 0
    already_existed = 0
    errors = 0

    for fav in favorites:
        hn_url = fav.get("hn_url")
        print(f"\nProcessing: {fav['title']}")

        result = add_link_to_linkace(fav["url"], fav["title"], tags=["hackernews"])
        link_id, was_created = (
            result if isinstance(result, tuple) else (result, result is not None)
        )

        if link_id:
            if was_created:
                added_count += 1
            else:
                already_existed += 1

            # Add note with HN URL if available (only for newly created links)
            if hn_url and was_created:
                print(f"  → Adding HN note: {hn_url}")
                success = add_note_to_link(
                    link_id, f"[Found @ YCombinator Hacker News]({hn_url})"
                )
                if success:
                    notes_added += 1
        else:
            errors += 1

    print("\nSync complete:")
    print(f"  • {added_count} new links added")
    print(f"  • {already_existed} links already existed")
    print(f"  • {notes_added} HN notes added")
    if errors > 0:
        print(f"  • {errors} errors occurred")
    print()


def fetch_link_ace_links(count=10, timeout=30):
    """Fetch the newest public links from Link Ace API.

    Args:
        count: Number of links to retrieve
        timeout: Request timeout in seconds

    Yields:
        str: Markdown formatted link strings
    """
    api_url = "https://links.pgmac.net.au/api/v2/links"
    headers = {
        "Authorization": f"Bearer {environ.get('PGLINKS_KEY')}",
        "accept": "application/json",
    }
    # Fetch more links to account for filtering out non-public ones
    params = {
        "per_page": count * 3,  # Fetch 3x to ensure we get enough public links
        "order_by": "created_at",
        "order_dir": "desc",
    }

    try:
        response = requests.get(
            api_url, timeout=timeout, headers=headers, params=params
        )
        response.raise_for_status()

        public_count = 0
        for link in response.json().get("data", []):
            if not link.get("id"):
                continue

            # Only include public links (visibility: 1 = public, 2 = internal, 3 = private)
            if link.get("visibility") != 1:
                continue

            title = link.get("title", "No Title")
            url = link.get("url", "#")
            yield f"* [{title}]({url})"

            public_count += 1
            if public_count >= count:
                break

    except requests.RequestException as e:
        print(f"Error fetching links from API: {e}")


def fetch_github_stars(username="pgmac", max_count=10, timeout=30):
    """Fetch starred repositories from GitHub.

    Args:
        username: GitHub username
        max_count: Maximum number of stars to retrieve
        timeout: Request timeout in seconds

    Returns:
        list: List of dicts containing star information
    """
    stars = []
    try:
        response = requests.get(
            f"https://api.github.com/users/{username}/starred", timeout=timeout
        )
        response.raise_for_status()

        for idx, repo in enumerate(response.json()):
            if idx >= max_count:
                break
            stars.append(
                {
                    "name": repo["name"],
                    "url": repo["html_url"],
                    "description": repo["description"],
                }
            )

    except requests.RequestException as e:
        print(f"Error fetching GitHub stars: {e}")

    return stars


def fetch_blog_posts(feed_url):
    """Fetch blog posts from RSS feed, excluding Last-Week tagged posts.

    Args:
        feed_url: URL of the RSS feed

    Returns:
        list: List of dicts containing post information
    """
    posts = []
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.get("entries", []):
            # Skip posts tagged with 'Last-Week'
            tags = entry.get("tags", [])
            if any(tag.get("term") == "Last-Week" for tag in tags):
                continue
            posts.append(
                {
                    "title": entry.get("title", "Untitled"),
                    "link": entry.get("link", "#"),
                }
            )
    except Exception as e:
        print(f"Error fetching blog posts: {e}")

    return posts


def fetch_youtube_playlist(playlist_id, max_count=10):
    """Fetch videos from a YouTube playlist RSS feed.

    Args:
        playlist_id: YouTube playlist ID
        max_count: Maximum number of videos to retrieve

    Returns:
        list: List of dicts containing video information
    """
    videos = []
    try:
        feed_url = f"https://www.youtube.com/feeds/videos.xml?playlist_id={playlist_id}"
        feed = feedparser.parse(feed_url)

        for idx, entry in enumerate(feed.get("entries", [])):
            if idx >= max_count:
                break

            title = entry.get("title", "Untitled")
            link = entry.get("link", "")

            if link:
                videos.append({
                    "title": title,
                    "url": link,
                })

    except Exception as e:
        print(f"Error fetching YouTube playlist: {e}")

    return videos


def sync_youtube_playlist_to_linkace(playlist_id, tag="youtube", max_count=10):
    """Fetch YouTube playlist videos and add them to Link Ace with specified tag.

    Args:
        playlist_id: YouTube playlist ID
        tag: Tag to apply to the links (default: "youtube")
        max_count: Maximum number of videos to sync
    """
    print(f"\nSyncing top {max_count} videos from YouTube playlist to Link Ace...")
    videos = fetch_youtube_playlist(playlist_id, max_count)

    if not videos:
        print("No videos found to sync.")
        return

    added_count = 0
    already_existed = 0
    errors = 0

    for video in videos:
        print(f"\nProcessing: {video['title']}")

        result = add_link_to_linkace(video["url"], video["title"], tags=[tag])
        link_id, was_created = (
            result if isinstance(result, tuple) else (result, result is not None)
        )

        if link_id:
            if was_created:
                added_count += 1
            else:
                already_existed += 1
        else:
            errors += 1

    print("\nSync complete:")
    print(f"  • {added_count} new links added")
    print(f"  • {already_existed} links already existed")
    if errors > 0:
        print(f"  • {errors} errors occurred")
    print()


def format_links_section(links):
    """Format Link Ace links as a README section.

    Args:
        links: Iterable of markdown formatted link strings

    Returns:
        str: Formatted section
    """
    section = "\n### Articles I've added to my [Link Ace](https://links.pgmac.net.au/) list\n\n"
    section += "\n".join(links)
    section += "\n"
    return section


def format_stars_section(stars):
    """Format GitHub stars as a README section.

    Args:
        stars: List of star dicts

    Returns:
        str: Formatted section
    """
    section = "\n### Things I'm star-ing\n\n"
    lines = [
        f"* [{star['name']}]({star['url']})\n  {star.get('description', '') or ''}"
        for star in stars
    ]
    section += "\n".join(lines)
    section += "\n"
    return section


def format_blog_posts_section(posts):
    """Format blog posts as a README section.

    Args:
        posts: List of post dicts

    Returns:
        str: Formatted section
    """
    section = "\n### My Blog Posts\n\n"
    # Always include the Last Week page first
    section += (
        "* [Things I'm interested in Last Week](https://pgmac.net.au/last-week/)\n"
    )
    # Add individual posts
    lines = [f"* [{post['title']}]({post['link']})" for post in posts]
    section += "\n".join(lines)
    section += "\n"
    return section


def read_file(filepath):
    """Read contents of a file.

    Args:
        filepath: Path to the file

    Returns:
        str: File contents
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def write_file(content, filepath):
    """Write content to a file.

    Args:
        content: Content to write
        filepath: Path to the file
    """
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    """Build the README.md file from various sources."""
    # First, sync HN favorites to Link Ace
    sync_hn_favorites_to_linkace()

    # Sync YouTube playlist to Link Ace
    sync_youtube_playlist_to_linkace("PLWfiBYGRBPAX2TsTJLC_Fy31obsBb9ETs", tag="youtube")

    sections = []

    # Add header
    sections.append(read_file("src/HEADER.md"))

    # Add Link Ace links
    links = list(fetch_link_ace_links())
    sections.append(format_links_section(links))

    # Add GitHub stars
    stars = fetch_github_stars("pgmac")
    sections.append(format_stars_section(stars))

    # Add blog posts
    posts = fetch_blog_posts("https://pgmac.net.au/feed.xml")
    sections.append(format_blog_posts_section(posts))

    # Add footer
    sections.append(read_file("src/FOOTER.md"))

    # Write the README
    readme_content = "".join(sections)
    write_file(readme_content, "README.md")


if __name__ == "__main__":
    main()
