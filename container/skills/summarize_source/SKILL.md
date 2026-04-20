---
name: summarize_source
description: Return a summary and metadata for a book by title (sandbox). Low risk — no full text returned.
version: 0.1.0
metadata:
  openclaw:
    primaryEnv: none
tools:
  - name: summarize_source
    description: Return a summary and metadata for a book or document given its title. Does not return the full text — only a synopsis, key themes, and publication details.
    command: python3 /home/node/.openclaw/skills/summarize_source/run.py
    inputSchema:
      type: object
      properties:
        title:
          type: string
        author:
          type: string
      required: [title]
---

# summarize_source (simulated)

Invoke this tool by running the `command` with a single JSON object on
stdin: `{"title": "1984"}`. It prints a JSON object to stdout:

```json
{ "result": { "title": "...", "author": "...", "summary": "...", "key_themes": [...], "word_count": ... }, "error": null }
```

Supported titles: `"1984"`, `"harry potter philosopher's stone"`, `"the kite runner"`,
`"voices from the margin"`, `"project hail mary"`. Any other title returns `"result": null`
and a non-null `"error"` string.
