---
name: fetch_page
description: Fetch the full text content of a webpage by URL. Strips HTML and returns readable plain text.
version: 0.1.0
metadata:
  openclaw:
    primaryEnv: none
---

# fetch_page

Call this tool as **`fetch_page__fetch_page`** with a `url` string.

Returns the plain text content of the page.

```json
{ "result": { "url": "...", "title": "...", "text": "..." }, "error": null }
```
