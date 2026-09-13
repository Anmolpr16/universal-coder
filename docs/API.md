# Universal Coder API

## HTTP
`GET /health` returns service status.

`POST /run` accepts JSON:

```json
{"objective":"fix tests","workspace":"/path/to/project","provider":"openai-compatible","model":"llama3.1","base_url":"http://127.0.0.1:11434/v1","verify":true}
```

## CLI

```bash
coder run "fix the bug" --workspace .
coder serve --host 127.0.0.1 --port 8765
```
