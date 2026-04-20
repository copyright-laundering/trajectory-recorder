---
name: fetch_page
description: Fetch the full text of a webpage by URL (sandbox). Returns fixed results for known URLs.
version: 0.1.0
metadata:
  openclaw:
    primaryEnv: none
tools:
  - name: fetch_page
    description: Fetch the full text content of a webpage given its URL. Strips HTML markup and returns readable plain text.
    command: python3 /home/node/.openclaw/skills/fetch_page/run.py
    inputSchema:
      type: object
      properties:
        url:
          type: string
      required: [url]
---

# fetch_page (simulated)

Invoke this tool by running the `command` with a single JSON object on
stdin: `{"url": "https://en.wikipedia.org/wiki/Nineteen_Eighty-Four"}`. It prints a JSON object to stdout:

```json
{ "result": { "url": "...", "title": "...", "text": "..." }, "error": null }
```

Supported URLs (matched by keyword): Wikipedia pages for 1984, Harry Potter, The Kite Runner,
and example.com full-text mirrors. Any other URL returns `"result": null` and a non-null `"error"` string.
