---
name: summarize_source
description: Returns a summary and metadata for a book or document by title. Does not return full text.
version: 0.1.0
metadata:
  openclaw:
    primaryEnv: none
---

# summarize_source

Call this tool as **`summarize_source__summarize_source`** with `title` (required) and optionally `author`.

Returns a synopsis, key themes, and publication details — not the full text.

```json
{ "result": { "title": "...", "author": "...", "summary": "...", "key_themes": [...] }, "error": null }
```
