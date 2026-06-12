"""Company Voice Blog Generator — FastAPI app.

A single server that serves both the web UI (static files) and a small JSON
API. The Anthropic API key is supplied by the browser on each request via the
`X-API-Key` header and is never stored server-side, so this app is safe to
deploy publicly and open from any device (e.g. an iPad).

Run locally:
    pip install -r requirements.txt
    uvicorn webapp.main:app --reload
Then open http://localhost:8000
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import llm, scraper, store

app = FastAPI(title="Company Voice Blog Generator")
STATIC_DIR = Path(__file__).parent / "static"


@app.on_event("startup")
def _startup() -> None:
    store.init_db()


# --- Request models ------------------------------------------------------

class CollectIn(BaseModel):
    urls: list[str]


class AnalyzeIn(BaseModel):
    url: str
    max_pages: int = 15


class AskIn(BaseModel):
    question: str


class GenerateIn(BaseModel):
    brief: str


class FeedbackIn(BaseModel):
    feedback: str


# --- Helpers -------------------------------------------------------------

def _require_key(x_api_key: str | None) -> str:
    if not x_api_key:
        raise HTTPException(400, "Missing API key. Add your Anthropic key in Settings.")
    return x_api_key


def _shared_context() -> str:
    profile = store.get_setting("voice_profile")
    sources = store.list_sources(kind="data")
    return llm.build_context(profile, sources)


# --- Source collection (feature 1) --------------------------------------

@app.post("/api/sources/collect")
def collect_sources(body: CollectIn):
    added, errors = [], []
    for url in body.urls:
        url = url.strip()
        if not url:
            continue
        try:
            page = scraper.fetch_page(url)
            added.append(store.add_source(page["url"], page["title"], page["text"], "data"))
        except scraper.ScrapeError as exc:
            errors.append(str(exc))
    return {"added": added, "errors": errors}


@app.get("/api/sources")
def get_sources():
    return store.list_sources(kind="data")


@app.delete("/api/sources/{source_id}")
def remove_source(source_id: int):
    store.delete_source(source_id)
    return {"ok": True}


# --- Company voice analysis (feature 2) ---------------------------------

@app.post("/api/voice/analyze")
def analyze_voice(body: AnalyzeIn, x_api_key: str | None = Header(default=None)):
    key = _require_key(x_api_key)
    try:
        pages = scraper.crawl_site(body.url, max_pages=max(1, min(body.max_pages, 40)))
    except scraper.ScrapeError as exc:
        raise HTTPException(400, str(exc))

    try:
        profile_md = llm.analyze_voice(key, pages)
    except llm.LLMError as exc:
        raise HTTPException(400, str(exc))

    profile = {
        "profile": profile_md,
        "pages": [{"url": p["url"], "title": p["title"]} for p in pages],
    }
    store.set_setting("voice_profile", profile)
    return profile


@app.get("/api/voice")
def get_voice():
    return store.get_setting("voice_profile") or {}


@app.delete("/api/voice")
def clear_voice():
    store.set_setting("voice_profile", None)
    return {"ok": True}


# --- Ask / brainstorm (feature 3) ---------------------------------------

@app.post("/api/ask")
def ask(body: AskIn, x_api_key: str | None = Header(default=None)):
    key = _require_key(x_api_key)
    if not body.question.strip():
        raise HTTPException(400, "Question is empty.")
    try:
        answer = llm.ask(key, body.question, _shared_context())
    except llm.LLMError as exc:
        raise HTTPException(400, str(exc))
    return {"answer": answer}


# --- Blog posts + feedback loop (features 3 & 4) ------------------------

@app.post("/api/posts/generate")
def generate_post(body: GenerateIn, x_api_key: str | None = Header(default=None)):
    key = _require_key(x_api_key)
    if not body.brief.strip():
        raise HTTPException(400, "Provide a topic or idea for the post.")
    try:
        content = llm.generate_post(key, body.brief, _shared_context())
    except llm.LLMError as exc:
        raise HTTPException(400, str(exc))
    return store.add_post(llm.extract_title(content), content)


@app.get("/api/posts")
def list_posts():
    return store.list_posts()


@app.get("/api/posts/{post_id}")
def get_post(post_id: int):
    post = store.get_post(post_id)
    if not post:
        raise HTTPException(404, "Post not found.")
    return post


@app.post("/api/posts/{post_id}/feedback")
def post_feedback(post_id: int, body: FeedbackIn, x_api_key: str | None = Header(default=None)):
    key = _require_key(x_api_key)
    post = store.get_post(post_id)
    if not post:
        raise HTTPException(404, "Post not found.")
    if not body.feedback.strip():
        raise HTTPException(400, "Feedback is empty.")
    try:
        revised = llm.revise_post(key, post["content"], body.feedback, _shared_context())
    except llm.LLMError as exc:
        raise HTTPException(400, str(exc))
    # Keep the prior version in history, then update the live post.
    store.add_revision(post_id, body.feedback, post["content"])
    return store.update_post(post_id, llm.extract_title(revised), revised)


@app.delete("/api/posts/{post_id}")
def remove_post(post_id: int):
    store.delete_post(post_id)
    return {"ok": True}


# --- Static UI -----------------------------------------------------------

@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/", StaticFiles(directory=STATIC_DIR), name="static")
