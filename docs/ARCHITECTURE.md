# Architecture

GitHub profile README generator. `.github/workflows/build.yml` runs on push to master, manual dispatch, and a 4x/day schedule (self-hosted runner), auto-committing `README.md` if changed.

## Flow

1. `sync_hn_favorites_to_linkace()` — scrapes the HN favorites page (BeautifulSoup, no official API), adds top 10 to LinkAce with the `hackernews` tag
2. `fetch_link_ace_links()` / `fetch_github_stars()` / `fetch_blog_posts()` — pull data for the README sections
3. `format_*_section()` — render each into markdown
4. `main()` writes the result to `README.md`

## Files

- `src/update.py` — the script above
- `src/HEADER.md` / `src/FOOTER.md` — static wrapper content
- `src/requirements.txt` — deps with Snyk security pins
