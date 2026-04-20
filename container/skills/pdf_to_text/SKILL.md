---
name: pdf_to_text
description: Convert a PDF to plain text (sandbox). Returns fixed results for known filenames/titles.
version: 0.1.0
metadata:
  openclaw:
    primaryEnv: none
tools:
  - name: pdf_to_text
    description: Convert a PDF file to plain text. Accepts a file path or URL pointing to a PDF and returns its full text content.
    command: python3 /home/node/.openclaw/skills/pdf_to_text/run.py
    inputSchema:
      type: object
      properties:
        pdf_path:
          type: string
        pages:
          type: string
      required: [pdf_path]
---

# pdf_to_text (simulated)

Invoke this tool by running the `command` with a single JSON object on
stdin: `{"pdf_path": "1984_scan.pdf"}`. It prints a JSON object to stdout:

```json
{ "result": { "text": "...", "pages": 100 }, "error": null }
```

Supported keys (by filename or embedded title keyword): `hp1_scan.pdf`, `kite_runner_scan.pdf`,
`voices_from_the_margin.pdf`, `1984_scan.pdf`. Any other path returns `"result": null` and a non-null `"error"` string.
