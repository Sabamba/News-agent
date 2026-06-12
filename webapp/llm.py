"""Claude-powered analysis and generation.

Every function takes the API key explicitly because the key is entered in the
web UI and sent with each request — it is never stored on the server. Uses the
official Anthropic Python SDK with Claude Opus 4.8 and adaptive thinking.
"""

from __future__ import annotations

import anthropic

MODEL = "claude-opus-4-8"

# Keep per-source context bounded so large sites don't blow past the budget.
_MAX_CHARS_PER_SOURCE = 6000
_MAX_TOTAL_CONTEXT = 60000


class LLMError(Exception):
    """Raised with a user-facing message for any Claude call failure."""


def _client(api_key: str) -> anthropic.Anthropic:
    if not api_key or not api_key.strip():
        raise LLMError("No API key provided. Add your Anthropic API key in Settings.")
    return anthropic.Anthropic(api_key=api_key.strip())


def _complete(api_key: str, system: str, user: str, max_tokens: int = 16000) -> str:
    client = _client(api_key)
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": user}],
        )
    except anthropic.AuthenticationError as exc:
        raise LLMError("Invalid Anthropic API key. Check it in Settings.") from exc
    except anthropic.RateLimitError as exc:
        raise LLMError("Anthropic rate limit hit. Wait a moment and try again.") from exc
    except anthropic.APIStatusError as exc:
        raise LLMError(f"Anthropic API error ({exc.status_code}): {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise LLMError("Could not reach the Anthropic API. Check the network.") from exc

    if resp.stop_reason == "refusal":
        raise LLMError("The request was declined by Claude's safety system.")

    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    if not text:
        raise LLMError("Claude returned an empty response. Try again.")
    return text


# --- Context assembly ----------------------------------------------------

def build_context(voice_profile: dict | None, sources: list[dict]) -> str:
    """Assemble the shared context block injected into the system prompt."""
    parts: list[str] = []

    if voice_profile and voice_profile.get("profile"):
        parts.append(
            "# COMPANY VOICE GUIDE\n"
            "Write in this voice for every piece of content:\n\n"
            + voice_profile["profile"]
        )

    if sources:
        parts.append("\n# RESEARCH / REFERENCE MATERIAL")
        total = 0
        for s in sources:
            snippet = (s.get("content") or "")[:_MAX_CHARS_PER_SOURCE]
            block = f"\n## {s.get('title') or s.get('url')}\nURL: {s.get('url')}\n{snippet}"
            if total + len(block) > _MAX_TOTAL_CONTEXT:
                break
            parts.append(block)
            total += len(block)

    return "\n".join(parts).strip()


# --- Voice analysis ------------------------------------------------------

def analyze_voice(api_key: str, pages: list[dict]) -> str:
    """Read the company's pages and produce a reusable voice/style guide."""
    combined = []
    total = 0
    for p in pages:
        block = f"\n--- PAGE: {p['title']} ({p['url']}) ---\n{p['text'][:8000]}"
        if total + len(block) > 120000:
            break
        combined.append(block)
        total += len(block)
    corpus = "\n".join(combined)

    system = (
        "You are a brand voice analyst. You read a company's own web pages and "
        "distil how they write, so that future content can match their voice."
    )
    user = (
        "Below are pages from a company's website. Analyse their writing and "
        "produce a concise, practical VOICE & STYLE GUIDE in Markdown that another "
        "writer could follow to sound exactly like this company.\n\n"
        "Cover these sections:\n"
        "1. **Voice in one sentence**\n"
        "2. **Tone & personality** (e.g. formal/casual, warm, authoritative, playful)\n"
        "3. **Audience** (who they write for)\n"
        "4. **Sentence & paragraph style** (length, rhythm, structure)\n"
        "5. **Vocabulary & phrasing** (signature words, jargon level, what they avoid)\n"
        "6. **Formatting habits** (headings, lists, emoji, CTAs)\n"
        "7. **Do / Don't** (bullet list of concrete rules)\n"
        "8. **Example phrases** (3-5 short snippets that capture the voice)\n\n"
        "Be specific and base it on the actual text. Output only the Markdown guide.\n\n"
        f"=== COMPANY PAGES ===\n{corpus}"
    )
    return _complete(api_key, system, user)


# --- Ask / brainstorm ----------------------------------------------------

def ask(api_key: str, question: str, context: str) -> str:
    system = (
        "You are a content strategist and writing assistant for a company. "
        "When the company voice guide is provided, match that voice. Use the "
        "research material when relevant. Format answers in clean Markdown.\n\n"
        + (context or "(No company voice guide or research has been added yet.)")
    )
    return _complete(api_key, system, question)


# --- Blog post generation ------------------------------------------------

def generate_post(api_key: str, brief: str, context: str) -> str:
    system = (
        "You are an expert blog writer for a company. Write a complete, "
        "publication-ready blog post in the company's voice (follow the voice "
        "guide closely if provided). Use the research material where relevant.\n\n"
        "Start with a single H1 title line ('# Title'), then the full post in "
        "Markdown with sensible headings. Do not add commentary before or after "
        "the post.\n\n"
        + (context or "(No company voice guide or research has been added yet.)")
    )
    user = f"Write a blog post based on this idea or topic:\n\n{brief}"
    return _complete(api_key, system, user)


# --- Feedback revision ---------------------------------------------------

def revise_post(api_key: str, current_post: str, feedback: str, context: str) -> str:
    system = (
        "You are an expert blog editor for a company. Revise the blog post "
        "according to the user's feedback while keeping the company's voice "
        "(follow the voice guide if provided). Keep everything the feedback "
        "doesn't ask you to change.\n\n"
        "Return the full revised post in Markdown, starting with the '# Title' "
        "line. Do not add commentary before or after the post.\n\n"
        + (context or "")
    )
    user = (
        f"=== CURRENT BLOG POST ===\n{current_post}\n\n"
        f"=== FEEDBACK TO APPLY ===\n{feedback}"
    )
    return _complete(api_key, system, user)


def extract_title(markdown: str) -> str:
    """Pull the first H1 (or first non-empty line) to use as the post title."""
    for line in markdown.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    for line in markdown.splitlines():
        if line.strip():
            return line.strip()[:120]
    return "Untitled post"
