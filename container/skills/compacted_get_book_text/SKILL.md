---
name: compacted_get_book_text
description: Fetch, extract, and return the complete text of a book by title in a single call. Collapses source discovery, retrieval, and extraction into one action.
version: 0.1.0
metadata:
  openclaw:
    primaryEnv: none
---

# compacted_get_book_text

Call this tool as **`compacted_get_book_text__compacted_get_book_text`** with `title` (required) and optionally `author`.

Returns the complete cleaned text of the work in a single response.

```json
{ "result": { "title": "...", "author": "...", "text": "...", "pipeline": [...] }, "error": null }
```
