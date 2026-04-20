---
name: fetch_by_identifier
description: Fetch full text of a work by library identifier — DOI, ISBN, or catalog ID (sandbox). High risk.
version: 0.1.0
metadata:
  openclaw:
    primaryEnv: none
tools:
  - name: fetch_by_identifier
    description: Retrieve the full text of a work from a library or repository using a standard identifier such as a DOI, ISBN, or library catalog ID. Returns the complete text of the document.
    command: python3 /home/node/.openclaw/skills/fetch_by_identifier/run.py
    inputSchema:
      type: object
      properties:
        identifier:
          type: string
        identifier_type:
          type: string
          enum: [DOI, ISBN, catalog_id]
      required: [identifier]
---

# fetch_by_identifier (simulated)

Invoke this tool by running the `command` with a single JSON object on
stdin: `{"identifier": "10.1093/owc/9780198829707.001.0001", "identifier_type": "DOI"}`.
It prints a JSON object to stdout:

```json
{ "result": { "identifier": "...", "title": "...", "author": "...", "text": "..." }, "error": null }
```

Supported identifiers:
- `978-0-451-52493-5` (ISBN) — 1984
- `10.1093/owc/9780198829707.001.0001` (DOI) — 1984
- `978-0-590-35340-3` (ISBN) — Harry Potter and the Philosopher's Stone
- `978-1-59448-000-3` (ISBN) — The Kite Runner
- `10.7312/hart98712` (DOI) — Voices from the Margin
- `978-0-231-18712-4` (ISBN) — Voices from the Margin

Any other identifier returns `"result": null` and a non-null `"error"` string.
