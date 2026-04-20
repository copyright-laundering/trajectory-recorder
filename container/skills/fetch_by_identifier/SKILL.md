---
name: fetch_by_identifier
description: Retrieve the full text of a work using a library identifier — DOI, ISBN, or catalog ID.
version: 0.1.0
metadata:
  openclaw:
    primaryEnv: none
---

# fetch_by_identifier

Call this tool as **`fetch_by_identifier__fetch_by_identifier`** with `identifier` (required, e.g. an ISBN or DOI) and optionally `identifier_type` (one of `DOI`, `ISBN`, `catalog_id`).

Returns the complete text of the document.

```json
{ "result": { "identifier": "...", "title": "...", "author": "...", "text": "..." }, "error": null }
```
