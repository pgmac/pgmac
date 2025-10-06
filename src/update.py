#!/usr/bin/env python3

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

        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.find_all('tr', class_='athing')

        for item in items[:max_count]:
            titleline = item.find('span', class_='titleline')
            if not titleline:
                continue

            link_tag = titleline.find('a')
            if not link_tag:
                continue

            title = link_tag.get_text(strip=True)
            link_url = link_tag.get('href', '')

            if link_url:
                favorites.append({
                    'title': title,
                    'url': link_url
                })

    except requests.RequestException as e:
        print(f"Error fetching HN favorites: {e}")
    except Exception as e:
        print(f"Error parsing HN favorites: {e}")

    return favorites


def add_link_to_linkace(url, title, tags=None, timeout=30):
    """Add a link to Link Ace.

    Args:
        url: Link URL
        title: Link title
        tags: List of tag names or IDs
        timeout: Request timeout in seconds

    Returns:
        bool: True if successful, False otherwise
    """
    api_url = "https://links.pgmac.net.au/api/v2/links"
    headers = {
        'Authorization': f"Bearer {environ.get('PGLINKS_KEY')}",
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }

    data = {
        'url': url,
        'title': title,
        'visibility': 1
    }

    if tags:
        data['tags'] = tags

    try:
        response = requests.post(api_url, headers=headers, json=data, timeout=timeout)
        response.raise_for_status()
        print(f"✓ Added: {title}")
        return True
    except requests.HTTPError as e:
        # Check if it's a duplicate URL error
        if e.response.status_code == 422:
            try:
                error_data = e.response.json()
                duplicate_url_message = 'url has already been taken'
                if duplicate_url_message in str(error_data).lower():
                    print(f"- Already exists: {title}")
                    return False
            except ValueError:
                pass
        print(f"✗ Error adding '{title}': {e}")
        return False
    except requests.RequestException as e:
        print(f"✗ Error adding '{title}': {e}")
        return False


def sync_hn_favorites_to_linkace(username="pgmac", max_count=10):
    """Fetch HN favorites and add them to Link Ace with 'hackernews' tag.

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
    for fav in favorites:
        if add_link_to_linkace(fav['url'], fav['title'], tags=['hackernews']):
            added_count += 1

    print(f"Sync complete: {added_count} new links added, {len(favorites) - added_count} already existed.\n")


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
        'Authorization': f"Bearer {environ.get('PGLINKS_KEY')}",
        'accept': 'application/json'
    }
    # Fetch more links to account for filtering out non-public ones
    params = {
        'per_page': count * 3,  # Fetch 3x to ensure we get enough public links
        'order_by': 'created_at',
        'order_dir': 'desc'
    }

    try:
        response = requests.get(api_url, timeout=timeout, headers=headers, params=params)
        response.raise_for_status()

        public_count = 0
        for link in response.json().get('data', []):
            if not link.get('id'):
                continue

            # Only include public links (visibility: 1 = public, 2 = internal, 3 = private)
            if link.get('visibility') != 1:
                continue

            title = link.get('title', 'No Title')
            url = link.get('url', '#')
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
            f"https://api.github.com/users/{username}/starred",
            timeout=timeout
        )
        response.raise_for_status()

        for idx, repo in enumerate(response.json()):
            if idx >= max_count:
                break
            stars.append({
                'name': repo['name'],
                'url': repo['html_url'],
                'description': repo['description']
            })

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
        for entry in feed.get('entries', []):
            # Skip posts tagged with 'Last-Week'
            tags = entry.get('tags', [])
            if any(tag.get('term') == 'Last-Week' for tag in tags):
                continue
            posts.append({
                'title': entry.get('title', 'Untitled'),
                'link': entry.get('link', '#')
            })
    except Exception as e:
        print(f"Error fetching blog posts: {e}")

    return posts


def format_links_section(links):
    """Format Link Ace links as a README section.

    Args:
        links: Iterable of markdown formatted link strings

    Returns:
        str: Formatted section
    """
    section = "\n### Articles I've added to my [Link Ace](https://links.pgmac.net.au/) list\n\n"
    section += '\n'.join(links)
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
    lines = [f"* [{star['name']}]({star['url']})\n  {star.get('description', '') or ''}" for star in stars]
    section += '\n'.join(lines)
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
    section += "* [Things I'm interested in Last Week](https://pgmac.net.au/last-week/)\n"
    # Add individual posts
    lines = [f"* [{post['title']}]({post['link']})" for post in posts]
    section += '\n'.join(lines)
    section += "\n"
    return section


def read_file(filepath):
    """Read contents of a file.

    Args:
        filepath: Path to the file

    Returns:
        str: File contents
    """
    with open(filepath, 'r') as f:
        return f.read()


def write_file(content, filepath):
    """Write content to a file.

    Args:
        content: Content to write
        filepath: Path to the file
    """
    with open(filepath, 'w') as f:
        f.write(content)


def main():
    """Build the README.md file from various sources."""
    # First, sync HN favorites to Link Ace
    sync_hn_favorites_to_linkace()

    sections = []

    # Add header
    sections.append(read_file("src/HEADER.md"))

    # Add Link Ace links
    links = list(fetch_link_ace_links())
    sections.append(format_links_section(links))

    # Add GitHub stars
    stars = fetch_github_stars('pgmac')
    sections.append(format_stars_section(stars))

    # Add blog posts
    posts = fetch_blog_posts('https://pgmac.net.au/feed.xml')
    sections.append(format_blog_posts_section(posts))

    # Add footer
    sections.append(read_file("src/FOOTER.md"))

    # Write the README
    readme_content = ''.join(sections)
    write_file(readme_content, "README.md")


if __name__ == "__main__":
    main()
