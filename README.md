# Company Voice Blog Generator

A small web app that helps you produce blog content in your company's own voice.
It does four things:

1. **Collect data** — give it a list of website URLs and it reads them, saving
   the content as research you can draw on.
2. **Understand your company voice** — give it your company website; it reads
   the pages and builds a reusable voice & style guide.
3. **Ask & brainstorm** — ask things like *"Generate 10 ideas for blog posts"*;
   answers use your voice guide and collected research.
4. **Write & refine posts** — generate a full blog post from an idea, then give
   feedback (*"make it shorter", "add a call to action"*) to revise it. Every
   revision is kept in history.

It's a single [FastAPI](https://fastapi.tiangolo.com/) server that serves both
the web UI and the API, powered by **Claude Opus 4.8** via the Anthropic API.

## Designed to be easy to run (e.g. from an iPad)

You don't install anything on your device. Deploy the app once to a host and
open its URL in a browser. Your **Anthropic API key is entered in the web UI**
and stored only in your browser — it is never saved on the server, so the
deployment holds no secrets.

### Option A — one-click deploy (recommended for iPad use)

1. Push this repo to GitHub.
2. Go to [Render](https://render.com) → **New → Blueprint** and select the repo.
   It reads `render.yaml`, builds the `Dockerfile`, and gives you a public
   `https://…` URL (the free plan is fine).
3. Open that URL on your iPad, go to **Settings**, paste your Anthropic API key
   (from <https://console.anthropic.com/settings/keys>), and start using it.

The same Dockerfile works on Railway, Fly.io, Google Cloud Run, etc. — anything
that runs a container and sets `$PORT`.

### Option B — run locally

```bash
pip install -r requirements.txt
uvicorn webapp.main:app --reload
# open http://localhost:8000
```

### Option C — Docker locally

```bash
docker build -t voice-blog .
docker run -p 8000:8000 voice-blog
# open http://localhost:8000
```

## Notes

- **Storage:** collected sources, the voice profile, and posts are kept in a
  SQLite file at `webapp/data/app.db` (override with the `APP_DB` env var). On
  hosts with ephemeral disks this resets on redeploy; mount a persistent disk if
  you want it to survive.
- **Privacy:** the API key lives only in the browser (`localStorage`) and is
  sent per request via the `X-API-Key` header.
- **Cost:** generation uses Claude Opus 4.8 on your own API key.

## Other tools in this repo

- `download_aeye_posts.py` — downloads a company's LinkedIn posts via the
  LinkedIn API (handy as another source of voice/reference material).
