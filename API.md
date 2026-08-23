# API Reference

The API is served by Flask locally and by Vercel in production. All JSON responses use UTF-8.

## `GET /`

Returns `index.html` with status `200`.

## `GET /api/config-status`

Returns provider availability without returning secret values.

Example response:

```json
{
  "success": true,
  "openrouter": true,
  "gemini": false,
  "groq": false,
  "notion_token": true,
  "notion_db": true
}
```

`true` means a non-empty value that is not recognized as a placeholder. A `500` response indicates that configuration or module startup failed.

## `POST /api/index`

Processes either a URL or a local file. Do not send both.

### URL request

```http
POST /api/index
Content-Type: application/json
```

```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

### File request

```http
POST /api/index
Content-Type: multipart/form-data
```

The multipart field must be named `file`. The client accepts common audio and video formats supported by the installed media tooling.

### Success response

```json
{
  "success": true,
  "notion_url": "",
  "markdown": "# Generated notes...",
  "audio_analyzed": true,
  "video_analyzed": true,
  "is_mock_mode": false,
  "message": "Annotation processed, but Notion sync failed."
}
```

`audio_analyzed` and `video_analyzed` describe the evidence available to the analysis step. `notion_url` may be empty because live Notion sync is currently disabled in the route.

### Sandbox response

When required credentials are missing, the endpoint returns `200` with `is_mock_mode: true`, fallback Markdown, and a sandbox Notion URL label. This is intentional and useful for UI demos.

### Error responses

| Status | Condition |
| --- | --- |
| `400` | Missing URL/file or a Vercel upload exceeds 4.5 MB. |
| `500` | Import, configuration, or processing failure. |

Example:

```json
{
  "error": "Please provide a valid video URL or upload a file."
}
```

## Operational Notes

- The API does not authenticate callers or rate-limit requests. Put it behind an authenticated gateway before exposing it publicly.
- Provider keys are read server-side and are never included in responses.
- Processing time depends on media duration, provider latency, and external service quotas.