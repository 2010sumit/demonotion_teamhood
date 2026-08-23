# KNIGHTHOOD Engine

KNIGHTHOOD Engine converts video and audio into structured technical notes. It can accept a YouTube URL or a local media upload, transcribe speech, inspect video keyframes, generate Markdown with an AI provider, and expose the result through a browser UI.

## What It Does

- Accepts YouTube URLs, including Shorts, and local audio/video files.
- Reuses available YouTube captions before downloading media for transcription.
- Extracts a small set of keyframes for visual analysis.
- Uses Gemini, OpenRouter, or Groq credentials according to the configured fallback path.
- Returns structured Markdown with a deterministic fallback when credentials are unavailable.
- Runs locally with Flask and deploys as a Vercel Python function.

> **Current integration status:** the API currently skips live Notion page creation by design. It returns generated Markdown and an offline/sandbox status when mock mode is active. See [API.md](API.md) and [ARCHITECTURE.md](ARCHITECTURE.md).

## Quick Start

### Prerequisites

- Python 3.10 or newer
- `pip`
- `ffmpeg` on `PATH` for the most reliable local audio extraction
- API credentials only when live AI processing is required

### Install and run

```powershell
python -m pip install -r requirements.txt
python api/index.py
```

Open <http://127.0.0.1:5000> in a browser. Do not open `index.html` directly because the page expects the Flask API.

### Environment

Create a root-level `.env` file. The complete variable list and Notion preparation steps are in [IMPORTANT_NOTE.md](IMPORTANT_NOTE.md).

```env
GEMINI_API_KEY=
OPENROUTER_API_KEY=
GROQ_API_KEY=
NOTION_TOKEN=
NOTION_DATABASE_ID=
GOOGLE_PROJECT_ID=
```

At least one AI key is needed for live AI processing. Missing or placeholder credentials intentionally activate sandbox mode.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Serves the web application. |
| `POST` | `/api/index` | Processes a URL or uploaded media. |
| `GET` | `/api/config-status` | Reports whether credentials are configured without exposing them. |

Request and response examples are documented in [API.md](API.md).

## Project Layout

```text
api/index.py              Flask routes and Vercel entry point
local_video_processor.py  ingestion, transcription, keyframes, and Markdown generation
config.py                 root .env loader and configuration access
index.html                browser client
requirements.txt          Python dependencies
test_*.py                 focused diagnostic scripts
```

## Verification

Run the lightweight checks first:

```powershell
python -m pytest
```

Some diagnostic tests contact YouTube or external AI services and therefore require network access and valid credentials. See [CONTRIBUTING.md](CONTRIBUTING.md) for the expected test workflow.

## Documentation

- [Architecture](ARCHITECTURE.md)
- [API reference](API.md)
- [Deployment](DEPLOYMENT.md)
- [Security](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)
- [Important local setup note](IMPORTANT_NOTE.md)

## License

No license has been declared for this project yet. Do not redistribute or reuse the code until the project owner adds a license.