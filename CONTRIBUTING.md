# Contributing

## Development Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Keep credentials in a local root `.env` file. Never add real secrets to tests or fixtures.

## Before Opening a Change

Run the focused checks relevant to your change:

```powershell
python -m pytest
python -m py_compile api/index.py local_video_processor.py config.py
```

The integration-style scripts may contact YouTube or AI providers. Run them only when network access and suitable test credentials are available, and do not commit generated `*log.txt` files.

## Change Guidelines

- Keep route contracts backward compatible unless the change includes updated API documentation.
- Preserve sandbox behavior so the UI can run without credentials.
- Clean up temporary media files on every exit path.
- Keep provider-specific code behind the existing processing helpers.
- Add or update a focused test for behavior changes.
- Update the relevant Markdown documentation when setup, API, deployment, or security behavior changes.

## Pull Requests

Describe the user-visible change, test commands and results, configuration changes, and any provider or deployment limitations. Keep unrelated formatting and generated files out of the change.