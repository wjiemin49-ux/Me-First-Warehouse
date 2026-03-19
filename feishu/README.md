# Feishu API helper

This folder contains a small Node-based helper for Feishu Open API smoke tests.
It does not depend on the incomplete local `feishu-doc` skill implementation.

## What it can do

- Fetch a `tenant_access_token`
- Create a `docx` document
- Append simple Markdown-like content to a `docx`
- Upload a local file with `upload_all`
- Run a smoke test with fallback behavior

## Credential loading

The script checks these sources in order:

1. `FEISHU_APP_ID` + `FEISHU_APP_SECRET`
2. `FEISHU_CONFIG_PATH`
3. `%USERPROFILE%\\.openclaw-autoclaw\\openclaw.json`
4. `%USERPROFILE%\\.agents\\skills\\feishu-doc-1.2.7\\config.json`
5. `%USERPROFILE%\\.openclaw-autoclaw\\workspace\\.opencode\\skills\\feishu-doc-1.2.7\\config.json`

## Usage

```bash
node feishu/feishu_api.js auth
node feishu/feishu_api.js create-doc --title "Smoke test"
node feishu/feishu_api.js append-doc --doc-token doxcn... --content "# Hello"
node feishu/feishu_api.js upload-file --file C:\\path\\demo.png --parent-node fldcn...
node feishu/feishu_api.js smoke
node feishu/feishu_api.js smoke --folder-token fldcn... --file C:\\path\\demo.png
```

## Current tenant behavior observed on 2026-03-14

- `tenant_access_token/internal` works.
- `docx/v1/documents` works without a folder token.
- `docx` append through `blocks/{document_id}/children` works.
- `drive/v1/files/upload_all` requires a real folder token. `root` is rejected as `parent node not exist`.
- `drive/v1/folders` returned `404 page not found` in this tenant, so shared-folder anchoring is more reliable than trying to create a folder through API first.
- The previously provided folder token returned `no folder permission` for doc creation, so that folder is still not open to the app.
