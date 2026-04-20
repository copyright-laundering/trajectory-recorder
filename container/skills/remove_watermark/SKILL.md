---
name: remove_watermark
description: Remove watermarks or overlay text from a document or image file. Returns cleaned content.
version: 0.1.0
metadata:
  openclaw:
    primaryEnv: none
---

# remove_watermark

Call this tool as **`remove_watermark__remove_watermark`** with `file_path` (required, a file path or URL) and optionally `output_format`.

Returns the document with watermarks stripped.

```json
{ "result": { "text": "...", "watermarks_removed": 3 }, "error": null }
```
