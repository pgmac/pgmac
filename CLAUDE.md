# CLAUDE.md

Python script that builds this repo's profile README.md from HN favorites, LinkAce links, GitHub stars, and blog posts. Full architecture: `docs/ARCHITECTURE.md`.

## Commands

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r src/requirements.txt
PGLINKS_KEY=<key> python src/update.py
```

## Gotchas

- HN sync must run before the README build — `main()` order matters, not just independent steps
- LinkAce duplicate detection relies on parsing a 422 status + specific error string, not a documented API contract
- Only `visibility=1` LinkAce links are shown
- No tests in this repo
