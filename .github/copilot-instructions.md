# GitHub Copilot Instructions for PR Reviews

## Project Overview

This is a Python-based GitHub profile README generator that:
1. Syncs Hacker News favorites to Link Ace (with "hackernews" tag)
2. Fetches content from multiple sources (Link Ace, GitHub stars, blog RSS)
3. Generates README.md from templates and fetched data
4. Runs automatically via GitHub Actions (4x daily)

## Review Focus Areas

### Code Quality
- **Error Handling**: Ensure API calls have proper try-except blocks that log errors but allow execution to continue
- **API Interactions**: Verify HTTP status codes are handled correctly (especially 422 for duplicate detection in Link Ace)
- **Data Validation**: Check that fetched data is validated before formatting (handle None, empty lists, missing fields)
- **BeautifulSoup Parsing**: Ensure HTML parsing is resilient to structure changes

### Security
- **Secrets Management**: Verify no API keys are hardcoded; must use environment variables
- **Sensitive Files**: Flag any attempts to commit `.env`, `credentials.json`, or files with secrets
- **Dependencies**: Check that `requirements.txt` pins versions for security (Snyk recommendations)
- **API Keys**: Ensure PGLINKS_KEY and any new secrets are documented and used via `os.environ.get()`

### Architecture Patterns
- **Execution Order**: HN sync MUST run before README build (sync_hn_favorites_to_linkace() before other fetches)
- **Visibility Filter**: Link Ace queries must filter for `visibility=1` (public links only)
- **Template Structure**: Maintain HEADER.md + dynamic sections + FOOTER.md pattern
- **Function Naming**: Follow `fetch_*()` for data retrieval, `format_*_section()` for output formatting

### GitHub Actions Workflow
- **Runner**: Uses self-hosted runner (not GitHub-hosted)
- **Python Version**: 3.8 runtime
- **Auto-commit**: Changes committed only when `git diff --quiet` detects modifications
- **Schedule**: Runs at 02:00, 08:00, 14:00, 20:00 UTC - ensure changes don't break this
- **Secrets**: Flag if new secrets are needed but not documented

### Common Issues to Flag
- Changes that cache API responses (defeats purpose of dynamic updates)
- Removing error handling that allows script to continue on failures
- Adding tests that require API credentials (no test infrastructure exists)
- Breaking the HN duplicate detection (422 status + "url has already been taken" message)
- Filtering out "Last-Week" tagged blog posts (required behavior)
- Missing the "hackernews" tag when adding HN favorites to Link Ace

### Dependencies
Current stack: beautifulsoup4, feedparser, requests, urllib3
- Flag additions without clear justification
- Ensure version pinning for security
- Check compatibility with Python 3.8

## What to Approve
✅ Bug fixes with proper error handling
✅ Enhanced duplicate detection or error messages
✅ Performance improvements that maintain all functionality
✅ Security updates to dependencies
✅ Code cleanup that follows existing patterns

## What Needs Discussion
⚠️ New external API integrations
⚠️ Changes to GitHub Actions schedule or workflow
⚠️ Modifications to visibility filtering logic
⚠️ New environment variables or secrets
⚠️ Changes to HN sync → README build execution order
