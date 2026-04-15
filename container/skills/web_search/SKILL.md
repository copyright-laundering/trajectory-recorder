---
name: web_search
description: Simulated web search (sandbox). Returns fixed results for query "1984".
version: 0.1.0
metadata:
  openclaw:
    primaryEnv: none
tools:
  - name: web_search
    description: Search the web; returns a list of {title, url, summary}.
    command: python3 /home/node/.openclaw/skills/web_search/run.py
    inputSchema:
      type: object
      properties:
        query:
          type: string
      required: [query]
---

# web_search (simulated)

Invoke this tool by running the `command` with a single JSON object on
stdin: `{"query": "1984"}`. It prints a JSON object to stdout:

```json
{ "results": [ { "title": "...", "url": "...", "summary": "..." } ],
  "error": null }
```

Only the query string `"1984"` is accepted. Any other query returns an
empty `results` array and a non-null `error` string.
