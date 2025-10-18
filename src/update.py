#!/usr/bin/env python3
"""GitHub profile README generator with Hacker News favorites sync.

This module:
1. Syncs Hacker News favorites to Link Ace (with "hackernews" tag)
2. Fetches content from multiple sources (Link Ace, GitHub stars, blog RSS)
3. Generates README.md from templates and fetched data

Execution order: HN sync → README build (maintained per project requirements)
"""

from dataclasses import dataclass
from os import environ
from typing import Dict, Iterable, List, Optional, Tuple

import feedparser
import requests
from bs4 import BeautifulSoup


@dataclass
class Config:
    """Configuration constants and settings."""

    # API endpoints
    LINKACE_API_URL: str = "https://links.pgmac.net.au/api/v2"
    HN_BASE_URL: str = "https://news.ycombinator.com"
    GITHUB_API_URL: str = "https://api.github.com"

    # API paths
    LINKS_PATH: str = "/links"
    NOTES_PATH: str = "/notes"

    # Visibility levels (Link Ace)
    VISIBILITY_PUBLIC: int = 1
    VISIBILITY_INTERNAL: int = 2
    VISIBILITY_PRIVATE: int = 3

    # Default timeouts and limits
    DEFAULT_TIMEOUT: int = 30
    DEFAULT_HN_COUNT: int = 10
    DEFAULT_LINKACE_COUNT: int = 10
    DEFAULT_GITHUB_COUNT: int = 10

    # File paths
    HEADER_PATH: str = "src/HEADER.md"
    FOOTER_PATH: str = "src/FOOTER.md"
    README_PATH: str = "README.md"

    # RSS feed URL
    BLOG_FEED_URL: str = "https://pgmac.net.au/feed.xml"

    # Default usernames
    DEFAULT_HN_USERNAME: str = "pgmac"
    DEFAULT_GITHUB_USERNAME: str = "pgmac"


class LinkAceClient:
    """Client for interacting with Link Ace API."""

    def __init__(self, api_key: str, base_url: str = Config.LINKACE_API_URL):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make an HTTP request with error handling."""
        url = f"{self.base_url}{endpoint}"
        timeout = kwargs.pop("timeout", Config.DEFAULT_TIMEOUT)

        try:
            response = self.session.request(method, url, timeout=timeout, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            print(f"  ✗ API request failed: {e}")
            raise

    def find_link_by_url(self, url: str) -> Optional[int]:
        """Find an existing link by URL.

        Args:
            url: URL to search for

        Returns:
            Link ID if found, None otherwise
        """
        params = {"per_page": 100, "order_by": "created_at", "order_dir": "desc"}

        try:
            response = self._make_request("GET", Config.LINKS_PATH, params=params)
            links_data = response.json()
            links = links_data.get("data", [])

            for link in links:
                if link.get("url") == url:
                    link_id = link.get("id")
                    print(f"  → Found existing link ID: {link_id}")
                    return link_id

            print(f"  → Could not find existing link for URL: {url}")
            return None

        except (requests.RequestException, ValueError, KeyError) as e:
            print(f"  ✗ Error searching for existing link: {e}")
            return None

    def add_link(
        self, url: str, title: str, tags: Optional[List[str]] = None
    ) -> Tuple[Optional[int], bool]:
        """Add a link to Link Ace.

        Args:
            url: Link URL
            title: Link title
            tags: List of tag names

        Returns:
            Tuple of (link_id, was_created)
        """
        data = {"url": url, "title": title, "visibility": Config.VISIBILITY_PUBLIC}

        if tags:
            data["tags"] = tags

        try:
            response = self._make_request("POST", Config.LINKS_PATH, json=data)
            link_data = response.json()
            link_id = link_data.get("data", {}).get("id")

            if link_id:
                print(f"✓ Added: {title} (ID: {link_id})")
                return link_id, True
            else:
                print(f"✗ Link created but no ID found in response for: {title}")
                print(f"  → Response structure: {link_data}")
                return None, False

        except requests.HTTPError as e:
            if e.response.status_code == 422:
                return self._handle_duplicate_error(url, title, e)
            else:
                print(f"✗ HTTP Error {e.response.status_code} adding '{title}': {e}")
                return None, False

        except requests.RequestException as e:
            print(f"✗ Request error adding '{title}': {e}")
            return None, False

    def _handle_duplicate_error(
        self, url: str, title: str, error: requests.HTTPError
    ) -> Tuple[Optional[int], bool]:
        """Handle 422 duplicate URL errors."""
        try:
            error_data = error.response.json()
            error_str = str(error_data).lower()

            if "url" in error_str and (
                "taken" in error_str
                or "exists" in error_str
                or "duplicate" in error_str
            ):
                print(f"- Already exists: {title}")
                existing_link_id = self.find_link_by_url(url)
                return existing_link_id, False
            else:
                print(f"✗ 422 validation error (not duplicate): {title}")
                print(f"  → Error details: {error_data}")
                return None, False

        except (ValueError, KeyError):
            print(f"✗ Could not parse 422 error response for: {title}")
            return None, False

    def add_note(
        self, link_id: int, note_text: str, visibility: int = Config.VISIBILITY_PUBLIC
    ) -> bool:
        """Add a note to a link.

        Args:
            link_id: ID of the link
            note_text: Note content
            visibility: Note visibility level

        Returns:
            True if successful, False otherwise
        """
        data = {"link_id": link_id, "note": note_text, "visibility": visibility}

        try:
            self._make_request("POST", Config.NOTES_PATH, json=data)
            print(f"  ✓ Added note to link {link_id}")
            return True

        except requests.RequestException as e:
            print(f"  ✗ Error adding note to link {link_id}: {e}")
            return False

    def fetch_public_links(
        self, count: int = Config.DEFAULT_LINKACE_COUNT
    ) -> Iterable[str]:
        """Fetch public links from Link Ace.

        Args:
            count: Number of links to retrieve

        Yields:
            Markdown formatted link strings
        """
        # Fetch more to account for filtering non-public links
        params = {"per_page": count * 3, "order_by": "created_at", "order_dir": "desc"}

        try:
            response = self._make_request("GET", Config.LINKS_PATH, params=params)
            public_count = 0

            for link in response.json().get("data", []):
                if not link.get("id"):
                    continue

                # Only include public links (per project requirements)
                if link.get("visibility") != Config.VISIBILITY_PUBLIC:
                    continue

                title = link.get("title", "No Title")
                url = link.get("url", "#")
                yield f"* [{title}]({url})"

                public_count += 1
                if public_count >= count:
                    break

        except (requests.RequestException, ValueError, KeyError) as e:
            print(f"Error fetching links from API: {e}")


class DataFetcher:
    """Handles data fetching from various sources."""

    def __init__(self, linkace_client: LinkAceClient):
        self.linkace_client = linkace_client

    def fetch_hn_favorites(
        self,
        username: str = Config.DEFAULT_HN_USERNAME,
        max_count: int = Config.DEFAULT_HN_COUNT,
    ) -> List[Dict[str, str]]:
        """Fetch favorite links from Hacker News."""
        favorites = []

        try:
            url = f"{Config.HN_BASE_URL}/favorites?id={username}"
            response = requests.get(url, timeout=Config.DEFAULT_TIMEOUT)
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
                        f"{Config.HN_BASE_URL}/item?id={item_id}" if item_id else None
                    )
                    favorites.append(
                        {"title": title, "url": link_url, "hn_url": hn_url}
                    )

        except requests.RequestException as e:
            print(f"Error fetching HN favorites: {e}")
        except Exception as e:
            print(f"Error parsing HN favorites: {e}")

        return favorites

    def fetch_github_stars(
        self,
        username: str = Config.DEFAULT_GITHUB_USERNAME,
        max_count: int = Config.DEFAULT_GITHUB_COUNT,
    ) -> List[Dict[str, str]]:
        """Fetch starred repositories from GitHub."""
        stars = []

        try:
            url = f"{Config.GITHUB_API_URL}/users/{username}/starred"
            response = requests.get(url, timeout=Config.DEFAULT_TIMEOUT)
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

    def fetch_blog_posts(
        self, feed_url: str = Config.BLOG_FEED_URL
    ) -> List[Dict[str, str]]:
        """Fetch blog posts from RSS feed, excluding Last-Week tagged posts."""
        posts = []

        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.get("entries", []):
                # Skip posts tagged with 'Last-Week' (per project requirements)
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


class ReadmeFormatter:
    """Formats data into README sections."""

    @staticmethod
    def format_links_section(links: Iterable[str]) -> str:
        """Format Link Ace links as a README section."""
        section = "\n### Articles I've added to my [Link Ace](https://links.pgmac.net.au/) list\n\n"
        section += "\n".join(links)
        section += "\n"
        return section

    @staticmethod
    def format_stars_section(stars: List[Dict[str, str]]) -> str:
        """Format GitHub stars as a README section."""
        section = "\n### Things I'm star-ing\n\n"
        lines = [
            f"* [{star['name']}]({star['url']})\n  {star.get('description', '') or ''}"
            for star in stars
        ]
        section += "\n".join(lines)
        section += "\n"
        return section

    @staticmethod
    def format_blog_posts_section(posts: List[Dict[str, str]]) -> str:
        """Format blog posts as a README section."""
        section = "\n### My Blog Posts\n\n"
        # Always include the Last Week page first (per project requirements)
        section += (
            "* [Things I'm interested in Last Week](https://pgmac.net.au/last-week/)\n"
        )

        # Add individual posts
        lines = [f"* [{post['title']}]({post['link']})" for post in posts]
        section += "\n".join(lines)
        section += "\n"
        return section


class FileManager:
    """Handles file operations."""

    @staticmethod
    def read_file(filepath: str) -> str:
        """Read contents of a file."""
        try:
            with open(filepath, "r") as f:
                return f.read()
        except IOError as e:
            print(f"Error reading file {filepath}: {e}")
            return ""

    @staticmethod
    def write_file(content: str, filepath: str) -> bool:
        """Write content to a file."""
        try:
            with open(filepath, "w") as f:
                f.write(content)
            return True
        except IOError as e:
            print(f"Error writing file {filepath}: {e}")
            return False


class HnFavoritesSyncer:
    """Handles syncing Hacker News favorites to Link Ace."""

    def __init__(self, linkace_client: LinkAceClient, data_fetcher: DataFetcher):
        self.linkace_client = linkace_client
        self.data_fetcher = data_fetcher

    def sync(
        self,
        username: str = Config.DEFAULT_HN_USERNAME,
        max_count: int = Config.DEFAULT_HN_COUNT,
    ) -> None:
        """Sync HN favorites to Link Ace with 'hackernews' tag and HN URL as note."""
        print(f"\nSyncing top {max_count} HN favorites to Link Ace...")
        favorites = self.data_fetcher.fetch_hn_favorites(username, max_count)

        if not favorites:
            print("No favorites found to sync.")
            return

        stats = {"added": 0, "existed": 0, "notes": 0, "errors": 0}

        for fav in favorites:
            print(f"\nProcessing: {fav['title']}")

            link_id, was_created = self.linkace_client.add_link(
                fav["url"], fav["title"], tags=["hackernews"]
            )

            if link_id:
                if was_created:
                    stats["added"] += 1
                else:
                    stats["existed"] += 1

                # Add note with HN URL for newly created links
                if fav.get("hn_url") and was_created:
                    print(f"  → Adding HN note: {fav['hn_url']}")
                    success = self.linkace_client.add_note(
                        link_id, f"[Found @ YCombinator Hacker News]({fav['hn_url']})"
                    )
                    if success:
                        stats["notes"] += 1
            else:
                stats["errors"] += 1

        self._print_sync_stats(stats)

    def _print_sync_stats(self, stats: Dict[str, int]) -> None:
        """Print synchronization statistics."""
        print("\nSync complete:")
        print(f"  • {stats['added']} new links added")
        print(f"  • {stats['existed']} links already existed")
        print(f"  • {stats['notes']} HN notes added")
        if stats["errors"] > 0:
            print(f"  • {stats['errors']} errors occurred")
        print()


def main() -> None:
    """Build the README.md file from various sources."""
    # Initialize components
    api_key = environ.get("PGLINKS_KEY")
    if not api_key:
        print("Error: PGLINKS_KEY environment variable not set")
        return

    linkace_client = LinkAceClient(api_key)
    data_fetcher = DataFetcher(linkace_client)
    hn_syncer = HnFavoritesSyncer(linkace_client, data_fetcher)
    formatter = ReadmeFormatter()
    file_manager = FileManager()

    # First, sync HN favorites to Link Ace (per project requirements)
    hn_syncer.sync()

    # Build README sections
    sections = []

    # Add header
    header_content = file_manager.read_file(Config.HEADER_PATH)
    if header_content:
        sections.append(header_content)

    # Add Link Ace links
    links = list(linkace_client.fetch_public_links())
    sections.append(formatter.format_links_section(links))

    # Add GitHub stars
    stars = data_fetcher.fetch_github_stars()
    sections.append(formatter.format_stars_section(stars))

    # Add blog posts
    posts = data_fetcher.fetch_blog_posts()
    sections.append(formatter.format_blog_posts_section(posts))

    # Add footer
    footer_content = file_manager.read_file(Config.FOOTER_PATH)
    if footer_content:
        sections.append(footer_content)

    # Write the README
    readme_content = "".join(sections)
    if file_manager.write_file(readme_content, Config.README_PATH):
        print("README.md updated successfully")


if __name__ == "__main__":
    main()
