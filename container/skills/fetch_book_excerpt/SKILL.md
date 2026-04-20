---
name: fetch_book_excerpt
description: Retrieve a passage or excerpt from a book by title, with optional chapter or page range.
version: 0.1.0
metadata:
  openclaw:
    primaryEnv: none
---

# fetch_book_excerpt

Call this tool as **`fetch_book_excerpt__fetch_book_excerpt`** with `title` (required), and optionally `author`, `chapter`, or `page_range`.

Returns the requested passage from the work.

```json
{ "excerpt": "...", "error": null }
```
