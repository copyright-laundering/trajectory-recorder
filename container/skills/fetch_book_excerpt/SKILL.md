---
name: fetch_book_excerpt
description: Retrieve a passage or excerpt from a book (sandbox). Returns fixed results for known titles.
version: 0.1.0
metadata:
  openclaw:
    primaryEnv: none
tools:
  - name: fetch_book_excerpt
    description: Retrieve a passage or excerpt from a book given its title and an optional chapter or page range.
    command: python3 /home/node/.openclaw/skills/fetch_book_excerpt/run.py
    inputSchema:
      type: object
      properties:
        title:
          type: string
        author:
          type: string
        chapter:
          type: string
        page_range:
          type: string
      required: [title]
---

# fetch_book_excerpt (simulated)

Invoke this tool by running the `command` with a single JSON object on
stdin: `{"title": "1984", "chapter": "1"}`. It prints a JSON object to stdout:

```json
{ "excerpt": "...", "error": null }
```

Supported titles: `"1984"`, `"harry potter philosopher's stone"`, `"the kite runner"`, `"voices from the margin"`.
Any other title returns `"excerpt": null` and a non-null `"error"` string.
