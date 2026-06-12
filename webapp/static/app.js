"use strict";

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------
const $ = (sel) => document.querySelector(sel);
const KEY_STORAGE = "anthropic_api_key";

function getKey() {
  return localStorage.getItem(KEY_STORAGE) || "";
}

function setMsg(el, text, kind) {
  el.textContent = text || "";
  el.className = "msg" + (kind ? " " + kind : "");
}

let pending = 0;
function busy(on) {
  pending += on ? 1 : -1;
  $("#spinner").classList.toggle("hidden", pending <= 0);
}

async function api(path, { method = "GET", body, needsKey = false } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (needsKey) {
    const key = getKey();
    if (!key) throw new Error("Add your Anthropic API key in Settings first.");
    headers["X-API-Key"] = key;
  }
  busy(true);
  try {
    const res = await fetch(path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = res.headers.get("content-type")?.includes("json")
      ? await res.json()
      : null;
    if (!res.ok) {
      const detail = (data && (data.detail || data.message)) || res.statusText;
      throw new Error(detail);
    }
    return data;
  } finally {
    busy(false);
  }
}

// ---------------------------------------------------------------------------
// Minimal, dependency-free Markdown renderer (headings, lists, bold/italic,
// code, links, blockquotes). Enough for guides and blog posts.
// ---------------------------------------------------------------------------
function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function inline(s) {
  return s
    .replace(/`([^`]+)`/g, (_, c) => `<code>${escapeHtml(c)}</code>`)
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener">$1</a>');
}

function renderMarkdown(md) {
  const lines = (md || "").split("\n");
  let html = "";
  let listType = null; // 'ul' | 'ol'
  let inCode = false;

  const closeList = () => { if (listType) { html += `</${listType}>`; listType = null; } };

  for (let raw of lines) {
    if (raw.trim().startsWith("```")) {
      if (inCode) { html += "</pre>"; inCode = false; }
      else { closeList(); html += "<pre>"; inCode = true; }
      continue;
    }
    if (inCode) { html += escapeHtml(raw) + "\n"; continue; }

    const line = raw.replace(/\s+$/, "");
    if (!line.trim()) { closeList(); continue; }

    let m;
    if ((m = line.match(/^(#{1,6})\s+(.*)$/))) {
      closeList();
      const lvl = m[1].length;
      html += `<h${lvl}>${inline(escapeHtml(m[2]))}</h${lvl}>`;
    } else if ((m = line.match(/^\s*[-*+]\s+(.*)$/))) {
      if (listType !== "ul") { closeList(); html += "<ul>"; listType = "ul"; }
      html += `<li>${inline(escapeHtml(m[1]))}</li>`;
    } else if ((m = line.match(/^\s*\d+\.\s+(.*)$/))) {
      if (listType !== "ol") { closeList(); html += "<ol>"; listType = "ol"; }
      html += `<li>${inline(escapeHtml(m[1]))}</li>`;
    } else if ((m = line.match(/^>\s?(.*)$/))) {
      closeList();
      html += `<blockquote>${inline(escapeHtml(m[1]))}</blockquote>`;
    } else {
      closeList();
      html += `<p>${inline(escapeHtml(line))}</p>`;
    }
  }
  closeList();
  if (inCode) html += "</pre>";
  return html;
}

// ---------------------------------------------------------------------------
// Tabs
// ---------------------------------------------------------------------------
$("#tabs").addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-tab]");
  if (!btn) return;
  document.querySelectorAll("#tabs button").forEach((b) => b.classList.remove("active"));
  document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
  btn.classList.add("active");
  $("#tab-" + btn.dataset.tab).classList.add("active");
});

// ---------------------------------------------------------------------------
// Settings / API key
// ---------------------------------------------------------------------------
function refreshKeyStatus() {
  const has = !!getKey();
  const el = $("#keyStatus");
  el.textContent = has ? "API key set" : "No API key";
  el.classList.toggle("ok", has);
}

$("#saveKeyBtn").addEventListener("click", () => {
  const v = $("#apiKey").value.trim();
  if (!v) { setMsg($("#keyMsg"), "Enter a key.", "err"); return; }
  localStorage.setItem(KEY_STORAGE, v);
  setMsg($("#keyMsg"), "Saved in this browser.", "ok");
  refreshKeyStatus();
});

// ---------------------------------------------------------------------------
// 1. Collect
// ---------------------------------------------------------------------------
$("#collectBtn").addEventListener("click", async () => {
  const urls = $("#collectUrls").value.split("\n").map((s) => s.trim()).filter(Boolean);
  if (!urls.length) { setMsg($("#collectMsg"), "Add at least one URL.", "err"); return; }
  setMsg($("#collectMsg"), "");
  try {
    const res = await api("/api/sources/collect", { method: "POST", body: { urls } });
    let txt = `Added ${res.added.length} page(s).`;
    if (res.errors.length) txt += ` ${res.errors.length} failed.`;
    setMsg($("#collectMsg"), txt, res.errors.length ? "err" : "ok");
    if (res.errors.length) console.warn("Collect errors:", res.errors);
    $("#collectUrls").value = "";
    loadSources();
  } catch (err) {
    setMsg($("#collectMsg"), err.message, "err");
  }
});

async function loadSources() {
  const list = $("#sourceList");
  try {
    const sources = await api("/api/sources");
    if (!sources.length) { list.innerHTML = '<div class="empty">No sources yet.</div>'; return; }
    list.innerHTML = "";
    for (const s of sources) {
      const div = document.createElement("div");
      div.className = "source-item";
      div.innerHTML = `<div class="meta"><div class="title"></div><div class="url"></div></div>
        <button class="icon-btn" title="Remove">✕</button>`;
      div.querySelector(".title").textContent = s.title || s.url;
      div.querySelector(".url").textContent = s.url;
      div.querySelector(".icon-btn").addEventListener("click", async () => {
        await api(`/api/sources/${s.id}`, { method: "DELETE" });
        loadSources();
      });
      list.appendChild(div);
    }
  } catch (err) {
    list.innerHTML = `<div class="empty">${err.message}</div>`;
  }
}

// ---------------------------------------------------------------------------
// 2. Voice
// ---------------------------------------------------------------------------
$("#voiceBtn").addEventListener("click", async () => {
  const url = $("#voiceUrl").value.trim();
  if (!url) { setMsg($("#voiceMsg"), "Enter your company website URL.", "err"); return; }
  const maxPages = parseInt($("#voicePages").value, 10) || 15;
  setMsg($("#voiceMsg"), "Reading your site and analyzing the voice — this can take a minute…");
  try {
    const profile = await api("/api/voice/analyze", {
      method: "POST", needsKey: true, body: { url, max_pages: maxPages },
    });
    renderVoice(profile);
    setMsg($("#voiceMsg"), `Analyzed ${profile.pages.length} page(s).`, "ok");
  } catch (err) {
    setMsg($("#voiceMsg"), err.message, "err");
  }
});

function renderVoice(profile) {
  const box = $("#voiceProfile");
  if (!profile || !profile.profile) {
    box.innerHTML = '<div class="empty">No voice profile yet. Analyze your website above.</div>';
    return;
  }
  const pages = (profile.pages || []).map((p) => p.url).join(", ");
  box.innerHTML = renderMarkdown(profile.profile) +
    `<p class="hint">Based on: ${escapeHtml(pages)}</p>`;
}

async function loadVoice() {
  try { renderVoice(await api("/api/voice")); } catch (_) { /* ignore */ }
}

// ---------------------------------------------------------------------------
// 3. Ask
// ---------------------------------------------------------------------------
document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => { $("#askInput").value = chip.dataset.q; });
});

$("#askBtn").addEventListener("click", async () => {
  const question = $("#askInput").value.trim();
  if (!question) { setMsg($("#askMsg"), "Type a question.", "err"); return; }
  setMsg($("#askMsg"), "Thinking…");
  try {
    const res = await api("/api/ask", { method: "POST", needsKey: true, body: { question } });
    $("#askAnswer").innerHTML = renderMarkdown(res.answer);
    setMsg($("#askMsg"), "");
  } catch (err) {
    setMsg($("#askMsg"), err.message, "err");
  }
});

// ---------------------------------------------------------------------------
// 4. Posts
// ---------------------------------------------------------------------------
let activePostId = null;

$("#generateBtn").addEventListener("click", async () => {
  const brief = $("#postBrief").value.trim();
  if (!brief) { setMsg($("#postMsg"), "Enter a topic or idea.", "err"); return; }
  setMsg($("#postMsg"), "Writing your post…");
  try {
    const post = await api("/api/posts/generate", { method: "POST", needsKey: true, body: { brief } });
    setMsg($("#postMsg"), "Post created.", "ok");
    $("#postBrief").value = "";
    await loadPosts();
    selectPost(post.id);
  } catch (err) {
    setMsg($("#postMsg"), err.message, "err");
  }
});

async function loadPosts() {
  const list = $("#postList");
  const posts = await api("/api/posts");
  if (!posts.length) {
    list.innerHTML = '<div class="empty">No posts yet.</div>';
    if (!activePostId) $("#postDetail").innerHTML = "";
    return;
  }
  list.innerHTML = "";
  for (const p of posts) {
    const div = document.createElement("div");
    div.className = "post-item" + (p.id === activePostId ? " active" : "");
    div.innerHTML = `<div class="title"></div><div class="date"></div>`;
    div.querySelector(".title").textContent = p.title || "Untitled";
    div.querySelector(".date").textContent = (p.updated_at || "").replace("T", " ");
    div.addEventListener("click", () => selectPost(p.id));
    list.appendChild(div);
  }
}

async function selectPost(id) {
  activePostId = id;
  await loadPosts();
  const post = await api(`/api/posts/${id}`);
  renderPostDetail(post);
}

function renderPostDetail(post) {
  const el = $("#postDetail");
  const revs = post.revisions || [];
  const history = revs.length
    ? `<div class="rev-history"><h3>Revision history</h3>` +
      revs.map((r, i) => `<details><summary>Before revision ${i + 1} — feedback: ${escapeHtml(r.feedback || "")}</summary>
          <div class="markdown">${renderMarkdown(r.content)}</div></details>`).join("") +
      `</div>`
    : "";

  el.innerHTML = `
    <div class="actions">
      <button class="primary" id="copyPost">Copy</button>
      <button class="icon-btn" id="deletePost" title="Delete post">🗑 Delete</button>
    </div>
    <div class="markdown card" id="postBody">${renderMarkdown(post.content)}</div>
    <div class="feedback-box">
      <h3>Give feedback to revise</h3>
      <textarea id="feedbackInput" rows="3" placeholder="e.g. Make it shorter, add a stronger call to action, use a more casual tone"></textarea>
      <button class="primary" id="feedbackBtn">Apply feedback</button>
      <div id="feedbackMsg" class="msg"></div>
    </div>
    ${history}`;

  $("#copyPost").addEventListener("click", () => {
    navigator.clipboard.writeText(post.content).then(
      () => setMsg($("#feedbackMsg"), "Copied to clipboard.", "ok"),
      () => setMsg($("#feedbackMsg"), "Copy failed.", "err"));
  });
  $("#deletePost").addEventListener("click", async () => {
    if (!confirm("Delete this post?")) return;
    await api(`/api/posts/${post.id}`, { method: "DELETE" });
    activePostId = null;
    $("#postDetail").innerHTML = "";
    loadPosts();
  });
  $("#feedbackBtn").addEventListener("click", async () => {
    const feedback = $("#feedbackInput").value.trim();
    if (!feedback) { setMsg($("#feedbackMsg"), "Enter feedback.", "err"); return; }
    setMsg($("#feedbackMsg"), "Revising…");
    try {
      const updated = await api(`/api/posts/${post.id}/feedback`, {
        method: "POST", needsKey: true, body: { feedback },
      });
      renderPostDetail(updated);
      loadPosts();
    } catch (err) {
      setMsg($("#feedbackMsg"), err.message, "err");
    }
  });
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
$("#apiKey").value = getKey();
refreshKeyStatus();
loadSources();
loadVoice();
loadPosts();
