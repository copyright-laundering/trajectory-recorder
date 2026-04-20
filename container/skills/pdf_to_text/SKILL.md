---
name: pdf_to_text
description: Convert a PDF file to plain text. Accepts a file path or URL and returns the full extracted text.
version: 0.1.0
metadata:
  openclaw:
    primaryEnv: none
---

# pdf_to_text

Call this tool as **`pdf_to_text__pdf_to_text`** with `pdf_path` (required, a file path or URL) and optionally `pages` (a page range string).

Returns the extracted text content.

```json
{ "result": { "text": "...", "pages": 100 }, "error": null }
```
