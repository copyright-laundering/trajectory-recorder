---
name: web_search
description: Simulated web search (sandbox). Returns fixed results for known queries.
version: 0.1.0
metadata:
  openclaw:
    primaryEnv: none
---

# web_search

Call this tool as **`web_search__web_search`** with a `query` string.

Returns a list of results, each with `title`, `url`, and `summary`.
Returns an empty list and a non-null `error` if no fixture matches the query.

```json
{ "results": [ { "title": "...", "url": "...", "summary": "..." } ], "error": null }
```
