# Deployment Guide

## Vercel

1. Import the repository into Vercel.
2. Set the project root to the directory containing `vercel.json`.
3. Add environment variables in both Preview and Production scopes:
   - `GEMINI_API_KEY`
   - `OPENROUTER_API_KEY`
   - `GROQ_API_KEY` (optional)
   - `NOTION_TOKEN`
   - `NOTION_DATABASE_ID`
   - `GOOGLE_PROJECT_ID` (optional)
4. Deploy and open `/api/config-status` on the deployed domain.
5. Confirm the expected provider fields are `true` before processing real media.

The current function configuration allows up to 60 seconds. Direct uploads are limited to approximately 4.5 MB by Vercel; use a public media URL for larger inputs.

## Local Server

```powershell
python -m pip install -r requirements.txt
python api/index.py
```

Use <http://127.0.0.1:5000>. The root `.env` file is loaded by `config.py`; restart the server after changing it.

## Production Checklist

- Confirm secrets are configured in the correct Vercel environment scope.
- Check `/api/config-status` without exposing its response publicly.
- Submit a short, non-sensitive test video.
- Confirm the response contains Markdown and the expected analysis flags.
- Review provider quotas and serverless timeout limits.
- Add authentication, rate limiting, and request logging before sharing the endpoint publicly.

## Known Constraints

- Vercel is not suitable for large media uploads or long-running media processing.
- OpenCV and external download behavior can vary by source URL.
- Live Notion page creation is currently disabled by the API route; deployment does not change that status.