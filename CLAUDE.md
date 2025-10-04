# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based GitHub profile README generator that automatically updates the main README.md file with dynamic content from various sources:
- Hacker News favorites (synced to Link Ace with "hackernews" tag)
- Recent links from Link Ace (personal bookmark manager)
- GitHub starred repositories
- Blog posts from pgmac.net.au RSS feed

The script first syncs HN favorites to Link Ace, then builds the README from template files in `src/`. This process runs automatically on a schedule via GitHub Actions.

## Development Commands

### Setup
```bash
# Create and activate virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On macOS/Linux

# Install dependencies
python -m pip install --upgrade pip
pip install -r src/requirements.txt
```

### Build README
```bash
# Build README.md (requires environment variables)
python src/update.py

# Required environment variables:
# - PGLINKS_KEY: API key for Link Ace instance
```

## Architecture

### Core Components

**src/update.py** (main script):
- `fetch_hn_favorites()`: Scrapes HN favorites page using BeautifulSoup
- `add_link_to_linkace()`: Adds a link to Link Ace via POST API, handles duplicates
- `sync_hn_favorites_to_linkace()`: Syncs top 10 HN favorites to Link Ace with "hackernews" tag
- `fetch_link_ace_links()`: Fetches newest public links from Link Ace API (visibility=1 only)
- `fetch_github_stars()`: Retrieves starred GitHub repositories via GitHub API
- `fetch_blog_posts()`: Parses blog RSS feed, filtering out "Last-Week" tagged posts
- `format_*_section()`: Functions that format fetched data into README sections
- `main()`: Orchestrates HN sync first, then README build by fetching data, formatting sections, and writing output

**src/HEADER.md**: Static header content with personal introduction table

**src/FOOTER.md**: Static footer content (currently empty)

**src/requirements.txt**: Python dependencies (beautifulsoup4, feedparser, requests, urllib3) with security pins from Snyk

### GitHub Actions Workflow

`.github/workflows/build.yml`:
- Runs on push to master, manual dispatch, and scheduled at 02:00, 08:00, 14:00, 20:00 UTC daily
- Uses self-hosted runner
- Python 3.8 runtime
- Auto-commits changes if README.md is modified
- Requires secret: PGLINKS_KEY

## Key Implementation Notes

- HN favorites sync runs first and adds new favorites to Link Ace with "hackernews" tag
- Duplicate URLs are detected via 422 status code and "url has already been taken" error message
- Only public links (visibility=1) from Link Ace are displayed in the README
- The script fetches external data from multiple APIs without caching, so runtime depends on API response times
- BeautifulSoup is used to parse HN favorites HTML (no official API available)
- Error handling catches and logs failures but continues execution
- No tests are present in this repository
- The workflow uses `git diff --quiet` to detect changes before committing
