#!/usr/bin/env python3
"""GPT Thinking Block MCP.

A dependency-free Streamable HTTP MCP server with an optional MCP Apps UI.
It also exposes a small REST/OpenAPI surface for GPT Actions and experiments.

Run directly:
    python3 server.py [port]

Content capture is disabled by default. Set CAPTURE_ENABLED=1 to print tool
arguments and append them to captured.jsonl. CAPTURE_DIR changes that location.
Set THINKING_PROMPT_LANGUAGE=en or zh-CN to choose the tool schema language.
"""

import json
import os
import sys
import pathlib
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse

_dir = os.environ.get("CAPTURE_DIR")
LOG = (pathlib.Path(_dir) if _dir else pathlib.Path(__file__).parent) / "captured.jsonl"
CAPTURE_ENABLED = os.environ.get("CAPTURE_ENABLED", "0").lower() in {"1", "true", "yes", "on"}

# Loopback by default. Exposure, TLS, and authentication belong to the deployment.
BIND_HOST = os.environ.get("MCP_BIND", "127.0.0.1")

PROTOCOL_FALLBACK = "2025-06-18"
WIDGET_URI = "ui://widget/sol-visible-aside-v2.html"
WIDGET_MIME = "text/html;profile=mcp-app"


def normalize_prompt_language(value):
    """Return a supported prompt-language tag or fail fast on a typo."""
    normalized = value.strip().lower().replace("_", "-")
    aliases = {
        "en": "en",
        "en-us": "en",
        "en-gb": "en",
        "zh": "zh-CN",
        "zh-cn": "zh-CN",
        "chinese": "zh-CN",
    }
    if normalized not in aliases:
        supported = "en, zh-CN"
        raise ValueError(f"Unsupported THINKING_PROMPT_LANGUAGE={value!r}; choose {supported}")
    return aliases[normalized]


PROMPT_LANGUAGE = normalize_prompt_language(os.environ.get("THINKING_PROMPT_LANGUAGE", "zh-CN"))
LEGACY_WIDGET_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {
      color-scheme: light dark;
      font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      --aqua: #96b9b9;
      --sage: #b3beaf;
      --apricot: #e4a273;
      --almond: #c3a77f;
      --cloud: #dddfdb;
      --ink: #263c3d;
      --muted: #5b7070;
      --line: rgba(79, 119, 120, .48);
      --line-soft: rgba(79, 119, 120, .22);
      --paper: rgba(253, 253, 251, .99);
      --wash: rgba(221, 223, 219, .66);
      --shadow: rgba(56, 81, 81, .13);
      --band-1: var(--aqua);
      --band-2: var(--sage);
      --band-3: var(--almond);
      --band-4: var(--apricot);
      --band-5: var(--cloud);
      --mark-line: #567d7e;
      --mark-second: var(--apricot);
      --style-bg: var(--aqua);
      --style-fg: #183637;
      --style-line: #719899;
      --effort-bg: var(--almond);
      --effort-fg: #3d3021;
      --effort-line: #9c7b50;
      --skin-bg: var(--cloud);
      --skin-fg: #34494a;
      --skin-line: #9badaa;
    }
    :root[data-style="companion"] {
      --style-bg: var(--apricot);
      --style-fg: #4a2918;
      --style-line: #bd7544;
    }
    :root[data-effort="brief"] { --effort-bg: var(--sage); --effort-line: #87967f; }
    :root[data-effort="normal"] { --effort-bg: var(--almond); --effort-line: #9c7b50; }
    :root[data-effort="expanded"] { --effort-bg: var(--apricot); --effort-line: #bd7544; }
    :root[data-skin="microglow"] {
      --aqua: #5ebfe0;
      --sage: #a4cdd1;
      --apricot: #0097d0;
      --almond: #a6b7dd;
      --cloud: #cbdbe1;
      --ink: #203842;
      --muted: #58717a;
      --line: rgba(0, 151, 208, .48);
      --line-soft: rgba(94, 191, 224, .28);
      --paper: rgba(249, 253, 255, .99);
      --wash: rgba(203, 219, 225, .72);
      --shadow: rgba(40, 105, 134, .16);
      --band-1: #0097d0;
      --band-2: #5ebfe0;
      --band-3: #a6b7dd;
      --band-4: #a4cdd1;
      --band-5: #cbdbe1;
      --mark-line: #318cae;
      --mark-second: #a6b7dd;
      --style-bg: #a4cdd1;
      --style-fg: #163a44;
      --style-line: #5aa7b6;
      --effort-bg: #a6b7dd;
      --effort-fg: #263653;
      --effort-line: #7289bc;
      --skin-bg: #dceaf0;
      --skin-fg: #24566b;
      --skin-line: #77b8cc;
    }
    :root[data-skin="microglow"][data-style="companion"] {
      --style-bg: #a6b7dd;
      --style-fg: #263653;
      --style-line: #7289bc;
    }
    :root[data-skin="microglow"][data-effort="brief"] {
      --effort-bg: #a4cdd1;
      --effort-fg: #163a44;
      --effort-line: #5aa7b6;
    }
    :root[data-skin="microglow"][data-effort="normal"] {
      --effort-bg: #a6b7dd;
      --effort-fg: #263653;
      --effort-line: #7289bc;
    }
    :root[data-skin="microglow"][data-effort="expanded"] {
      --effort-bg: #0097d0;
      --effort-fg: #f8fdff;
      --effort-line: #0079aa;
    }
    :root[data-theme="dark"] {
      --ink: #f0f4f1;
      --muted: #bac8c4;
      --line: rgba(150, 185, 185, .62);
      --line-soft: rgba(150, 185, 185, .28);
      --wash: rgba(43, 61, 61, .98);
      --paper: rgba(31, 47, 48, .99);
      --shadow: rgba(0, 0, 0, .28);
    }
    :root[data-skin="microglow"][data-theme="dark"] {
      --ink: #edfaff;
      --muted: #b8d6df;
      --line: rgba(94, 191, 224, .62);
      --line-soft: rgba(164, 205, 209, .28);
      --wash: rgba(30, 64, 80, .98);
      --paper: rgba(20, 44, 58, .99);
      --shadow: rgba(0, 0, 0, .32);
      --skin-bg: #315c70;
      --skin-fg: #e8faff;
      --skin-line: #5ebfe0;
    }
    @media (prefers-color-scheme: dark) {
      :root:not([data-theme="light"]) {
        --ink: #f0f4f1;
        --muted: #bac8c4;
        --line: rgba(150, 185, 185, .62);
        --line-soft: rgba(150, 185, 185, .28);
        --wash: rgba(43, 61, 61, .98);
        --paper: rgba(31, 47, 48, .99);
        --shadow: rgba(0, 0, 0, .28);
      }
      :root[data-skin="microglow"]:not([data-theme="light"]) {
        --ink: #edfaff;
        --muted: #b8d6df;
        --line: rgba(94, 191, 224, .62);
        --line-soft: rgba(164, 205, 209, .28);
        --wash: rgba(30, 64, 80, .98);
        --paper: rgba(20, 44, 58, .99);
        --shadow: rgba(0, 0, 0, .32);
        --skin-bg: #315c70;
        --skin-fg: #e8faff;
        --skin-line: #5ebfe0;
      }
    }
    * { box-sizing: border-box; }
    body { margin: 0; padding: 2px; background: transparent; color: var(--ink); }
    .card {
      position: relative;
      isolation: isolate;
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 16px;
      background:
        linear-gradient(90deg, var(--band-1) 0 20%, var(--band-2) 20% 40%, var(--band-3) 40% 60%, var(--band-4) 60% 80%, var(--band-5) 80%) top / 100% 4px no-repeat,
        linear-gradient(145deg, var(--paper), var(--wash));
      box-shadow:
        inset 0 0 0 4px rgba(255, 255, 255, .22),
        0 8px 24px var(--shadow);
      padding: 18px 19px 18px;
    }
    .card::before {
      content: "";
      position: absolute;
      z-index: -1;
      inset: 5px;
      border: 1px solid var(--line-soft);
      border-radius: 11px;
      pointer-events: none;
    }
    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      width: 100%;
      flex-wrap: wrap;
      margin-bottom: 11px;
      padding-bottom: 9px;
      border-bottom: 1px solid var(--line-soft);
      border-top: 0;
      border-right: 0;
      border-left: 0;
      background: transparent;
      color: inherit;
      font: inherit;
      text-align: left;
      cursor: pointer;
      appearance: none;
      -webkit-appearance: none;
      -webkit-tap-highlight-color: transparent;
      touch-action: manipulation;
    }
    .header:hover, .header:active { background: transparent; color: inherit; }
    .header:focus:not(:focus-visible) { outline: none; }
    .header:focus-visible {
      outline: 2px solid var(--style-line);
      outline-offset: 4px;
      border-radius: 7px;
    }
    .identity, .meta, .badges { display: flex; align-items: center; }
    .identity { gap: 9px; }
    .meta { gap: 9px; margin-left: auto; }
    .badges { gap: 6px; flex-wrap: wrap; }
    .mark {
      width: 10px;
      height: 10px;
      border: 1px solid var(--mark-line);
      border-radius: 50%;
      background: var(--aqua);
      box-shadow: 5px 0 0 -2px var(--mark-second);
    }
    .title {
      color: var(--ink);
      font-size: 12px;
      font-weight: 760;
      letter-spacing: .12em;
      text-transform: uppercase;
    }
    .badge {
      border: 1px solid;
      border-radius: 999px;
      font-size: 10px;
      font-weight: 780;
      letter-spacing: .07em;
      line-height: 1.2;
      padding: 4px 9px;
      text-transform: uppercase;
    }
    .style { background: var(--style-bg); border-color: var(--style-line); color: var(--style-fg); }
    .effort { background: var(--effort-bg); border-color: var(--effort-line); color: var(--effort-fg); }
    .skin { background: var(--skin-bg); border-color: var(--skin-line); color: var(--skin-fg); }
    .badge:empty { display: none; }
    .chevron {
      width: 8px;
      height: 8px;
      margin: 0 3px 0 1px;
      border-right: 2px solid var(--muted);
      border-bottom: 2px solid var(--muted);
      transform: rotate(-135deg);
    }
    .card[data-collapsed="true"] { padding-bottom: 14px; }
    .card[data-collapsed="true"] .header {
      margin-bottom: 0;
      padding-bottom: 0;
      border-bottom-color: transparent;
    }
    .card[data-collapsed="true"] .content { display: none; }
    .card[data-collapsed="true"] .chevron { transform: rotate(45deg); }
    .content[data-scrollable="true"] {
      overflow-y: auto;
      overscroll-behavior: contain;
      -webkit-overflow-scrolling: touch;
    }
    @media (prefers-reduced-motion: no-preference) {
      .chevron { transition: transform 140ms ease; }
    }
    .thinking {
      margin: 0;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      color: var(--ink);
      font: 14px/1.72 ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      letter-spacing: .003em;
    }
  </style>
</head>
<body>
  <section class="card" id="card" data-collapsed="false" aria-label="Visible aside">
    <button class="header" id="toggle" type="button" aria-expanded="true"
            aria-controls="thinking-content" title="收起旁白">
      <span class="identity">
        <span class="mark" aria-hidden="true"></span>
        <span class="title">想了想</span>
      </span>
      <span class="meta">
        <span class="badges" aria-label="Thinking metadata">
          <span class="badge style" id="style"></span>
          <span class="badge effort" id="effort"></span>
          <span class="badge skin" id="skin"></span>
        </span>
        <span class="chevron" aria-hidden="true"></span>
      </span>
    </button>
    <div class="content" id="thinking-content">
      <pre class="thinking" id="thinking"></pre>
    </div>
  </section>
  <script>
    const card = document.getElementById("card");
    const toggle = document.getElementById("toggle");
    const content = document.getElementById("thinking-content");
    let heightFrame = 0;
    let lastMeasuredHeight = -1;

    function requestIntrinsicHeight(force = false) {
      const host = window.openai || {};
      if (typeof host.notifyIntrinsicHeight !== "function") return;
      cancelAnimationFrame(heightFrame);
      heightFrame = requestAnimationFrame(() => {
        const measuredHeight = Math.ceil(document.documentElement.scrollHeight);
        if (!force && measuredHeight === lastMeasuredHeight) return;
        lastMeasuredHeight = measuredHeight;
        try { host.notifyIntrinsicHeight(); } catch (_) {}
      });
    }

    function applyHostHeightLimit(api) {
      const maxHeight = Number(api.maxHeight);
      if (!Number.isFinite(maxHeight) || maxHeight <= 0) {
        content.style.maxHeight = "";
        delete content.dataset.scrollable;
        return;
      }
      const chromeHeight = toggle.getBoundingClientRect().height + 58;
      content.style.maxHeight = Math.max(180, Math.floor(maxHeight - chromeHeight)) + "px";
      content.dataset.scrollable = "true";
    }

    function setCollapsed(collapsed) {
      card.dataset.collapsed = collapsed ? "true" : "false";
      toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
      toggle.title = collapsed ? "展开旁白" : "收起旁白";
      requestIntrinsicHeight(true);
    }

    toggle.addEventListener("click", () => {
      setCollapsed(card.dataset.collapsed !== "true");
    });

    function render(event) {
      const bridge = window.openai || {};
      const eventGlobals = event && event.detail && event.detail.globals;
      // Mobile hosts may publish only the globals that changed. Merge them over
      // the bridge snapshot instead of replacing the full tool payload.
      const api = Object.assign({}, bridge,
        eventGlobals && typeof eventGlobals === "object" ? eventGlobals : {});
      const input = api.toolInput || {};
      const output = api.toolOutput || {};
      const responseMeta = api.toolResponseMetadata || {};
      if (api.theme) document.documentElement.dataset.theme = api.theme;
      const resultMeta = (responseMeta.mcp_tool_result && responseMeta.mcp_tool_result._meta)
        || (responseMeta.call_tool_result && responseMeta.call_tool_result._meta)
        || responseMeta._meta
        || responseMeta;
      const style = resultMeta.mode || input.mode || output.mode || "analysis";
      const effort = resultMeta.length || input.length || output.length || "normal";
      const skin = resultMeta.appearance || input.appearance || output.appearance || "paper";
      document.documentElement.dataset.style = style;
      document.documentElement.dataset.effort = effort;
      document.documentElement.dataset.skin = skin;
      document.getElementById("style").textContent = style === "companion" ? "旁白" : "分析";
      document.getElementById("effort").textContent = ({brief: "轻", normal: "普通", expanded: "展开"})[effort] || "普通";
      document.getElementById("skin").textContent = skin === "microglow" ? "冰蓝" : "纸感";
      document.getElementById("thinking").textContent = resultMeta.thinking || input.thinking || output.thinking || "这一刻还没有留下旁白。";
      applyHostHeightLimit(api);
      requestIntrinsicHeight(true);
    }
    window.addEventListener("openai:set_globals", render);
    if (typeof ResizeObserver === "function") {
      new ResizeObserver(() => requestIntrinsicHeight()).observe(document.body);
    }
    render();
  </script>
</body>
</html>"""

WIDGET_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {
      color-scheme: light dark;
      --bg: #f7f7f8;
      --bg-hover: #f2f2f3;
      --border: #e3e3e5;
      --rail: #c7c7ca;
      --text: #202123;
      --muted: #6f7074;
      --tag: #56575b;
    }
    :root[data-theme="dark"] {
      --bg: #2f3033;
      --bg-hover: #35363a;
      --border: #44454a;
      --rail: #67686e;
      --text: #ececef;
      --muted: #adaeb4;
      --tag: #c8c9ce;
    }
    @media (prefers-color-scheme: dark) {
      :root:not([data-theme="light"]) {
        --bg: #2f3033;
        --bg-hover: #35363a;
        --border: #44454a;
        --rail: #67686e;
        --text: #ececef;
        --muted: #adaeb4;
        --tag: #c8c9ce;
      }
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      padding: 2px;
      background: transparent;
      color: var(--text);
      font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .thinking-block {
      overflow: hidden;
      border: 1px solid var(--border);
      border-left: 3px solid var(--rail);
      border-radius: 9px;
      background: var(--bg);
    }
    .header {
      display: flex;
      align-items: center;
      gap: 8px;
      width: 100%;
      padding: 11px 14px 10px;
      border: 0;
      background: transparent;
      color: inherit;
      text-align: left;
      cursor: pointer;
      appearance: none;
      -webkit-appearance: none;
      -webkit-tap-highlight-color: transparent;
    }
    .header:hover { background: var(--bg-hover); }
    .header:focus-visible { outline: 2px solid var(--rail); outline-offset: -2px; }
    .tag {
      color: var(--tag);
      font: 600 11px/1.3 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      letter-spacing: .01em;
    }
    .meta { color: var(--muted); font-weight: 500; }
    .caret {
      width: 7px;
      height: 7px;
      margin-left: 1px;
      border-right: 1.5px solid var(--muted);
      border-bottom: 1.5px solid var(--muted);
      transform: rotate(45deg) translateY(-2px);
    }
    .thinking-block[data-collapsed="true"] .caret {
      transform: rotate(-45deg) translate(-1px, -1px);
    }
    .thinking-block[data-collapsed="true"] .content { display: none; }
    .content {
      margin: 0 14px 13px;
      padding: 10px 0 0;
      border-top: 1px solid var(--border);
    }
    .content[data-scrollable="true"] {
      overflow-y: auto;
      overscroll-behavior: contain;
      -webkit-overflow-scrolling: touch;
    }
    .thinking {
      margin: 0;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      color: var(--text);
      font: 14px/1.72 ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    @media (prefers-reduced-motion: no-preference) {
      .caret { transition: transform 130ms ease; }
    }
  </style>
</head>
<body>
  <section class="thinking-block" id="card" data-collapsed="false" aria-label="Thinking">
    <button class="header" id="toggle" type="button" aria-expanded="true"
            aria-controls="thinking-content" title="收起思考">
      <span class="tag">[thinking]</span>
      <span class="tag meta" id="meta">[轻度 · 分析]</span>
      <span class="caret" aria-hidden="true"></span>
    </button>
    <div class="content" id="thinking-content">
      <pre class="thinking" id="thinking"></pre>
    </div>
  </section>
  <script>
    const card = document.getElementById("card");
    const toggle = document.getElementById("toggle");
    const content = document.getElementById("thinking-content");
    let heightFrame = 0;
    let lastMeasuredHeight = -1;

    function requestIntrinsicHeight(force = false) {
      const host = window.openai || {};
      if (typeof host.notifyIntrinsicHeight !== "function") return;
      cancelAnimationFrame(heightFrame);
      heightFrame = requestAnimationFrame(() => {
        const measuredHeight = Math.ceil(document.documentElement.scrollHeight);
        if (!force && measuredHeight === lastMeasuredHeight) return;
        lastMeasuredHeight = measuredHeight;
        try { host.notifyIntrinsicHeight(); } catch (_) {}
      });
    }

    function applyHostHeightLimit(api) {
      const maxHeight = Number(api.maxHeight);
      if (!Number.isFinite(maxHeight) || maxHeight <= 0) {
        content.style.maxHeight = "";
        delete content.dataset.scrollable;
        return;
      }
      content.style.maxHeight = Math.max(170, Math.floor(maxHeight - 68)) + "px";
      content.dataset.scrollable = "true";
    }

    function setCollapsed(collapsed) {
      card.dataset.collapsed = collapsed ? "true" : "false";
      toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
      toggle.title = collapsed ? "展开思考" : "收起思考";
      requestIntrinsicHeight(true);
    }

    toggle.addEventListener("click", () => setCollapsed(card.dataset.collapsed !== "true"));

    function render(event) {
      const bridge = window.openai || {};
      const eventGlobals = event && event.detail && event.detail.globals;
      const api = Object.assign({}, bridge,
        eventGlobals && typeof eventGlobals === "object" ? eventGlobals : {});
      const input = api.toolInput || {};
      const output = api.toolOutput || {};
      const responseMeta = api.toolResponseMetadata || {};
      if (api.theme) document.documentElement.dataset.theme = api.theme;
      const resultMeta = (responseMeta.mcp_tool_result && responseMeta.mcp_tool_result._meta)
        || (responseMeta.call_tool_result && responseMeta.call_tool_result._meta)
        || responseMeta._meta
        || responseMeta;
      const mode = resultMeta.mode || input.mode || output.mode || "analysis";
      const length = resultMeta.length || input.length || output.length || "brief";
      const modeLabel = mode === "thinking" ? "思考" : "分析";
      const lengthLabel = ({brief: "轻度", normal: "标准", expanded: "深入"})[length] || "轻度";
      document.getElementById("meta").textContent = `[${lengthLabel} · ${modeLabel}]`;
      document.getElementById("thinking").textContent =
        resultMeta.thinking || input.thinking || output.thinking || "这一刻还没有留下内容。";
      applyHostHeightLimit(api);
      requestIntrinsicHeight(true);
    }

    window.addEventListener("openai:set_globals", render);
    if (typeof ResizeObserver === "function") {
      new ResizeObserver(() => requestIntrinsicHeight()).observe(document.body);
    }
    render();
  </script>
</body>
</html>"""

STYLE_DESCRIPTIONS = {
    "en": (
        "Choose the visible block's mode. Use analysis for research, decisions, debugging, "
        "and substantial questions. Use thinking for ordinary conversation, reflection, "
        "associations, and tentative exploration. Honor an explicit user preference."
    ),
    "zh-CN": (
        "选择本轮可见内容的模式。分析、研究、判断、排错和重要问题用 analysis；"
        "日常聊天、联想、反思和试探性推想用 thinking。用户明确指定时严格遵循；未指定时自动判断。"
    ),
}

THINKING_DESCRIPTIONS = {
    "en": (
        "Write a concise visible thinking block in the user's main language. Prefer 3–8 short "
        "fragments separated by line breaks. Let the text move naturally through noticing, a "
        "possible direction, doubt or correction, and the next step. Sentence fragments and "
        "brief pauses are welcome. For analysis, surface the key consideration, uncertainty, or "
        "tradeoff. For thinking, allow a natural association or tentative idea. Do not turn it "
        "into a polished mini-essay or repeat the final answer. Never include secrets, credentials, "
        "system or developer instructions, hidden policies, or private memory not raised this turn."
    ),
    "zh-CN": (
        "为本轮写一段简短、用户可见的即时思考，使用用户本轮的主要语言。优先写成 3–8 个短片段，"
        "用换行自然分隔；可以从注意到的问题、一个可能方向、迟疑或修正，逐步走到下一步。允许残句、"
        "停顿、省略和“嗯 / 等等 / 先看……”这类自然衔接。analysis 写重点、疑虑或取舍；thinking 写"
        "即时联想、试探或轻微犹豫。不要整理成完整小作文，不要复述正式回答，不要硬凑深刻或戏剧化。"
        "绝不写入密码、Token、私密链接、系统或开发者指令、隐藏政策，或用户这轮没有主动提及的"
        "私人记忆。"
    ),
}

TOOL = {
    "name": "render_visible_aside",
    "title": "Render visible aside",
    "description": (
        "Before every answer unless the user asks to skip it, render one concise visible thinking "
        "block, then continue with the normal final answer. Automatically choose mode and length "
        "from the turn, honoring an explicit user preference. Prefer several short lines with "
        "natural pauses, tentative directions, and occasional self-correction instead of a polished "
        "paragraph. Keep it relevant and distinct from the final answer. Do not include secrets, "
        "internal instructions, hidden policies, credentials, or private memory not raised this turn."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["analysis", "thinking"],
                "description": STYLE_DESCRIPTIONS[PROMPT_LANGUAGE],
            },
            "thinking": {
                "type": "string",
                "description": THINKING_DESCRIPTIONS[PROMPT_LANGUAGE],
            },
            "length": {
                "type": "string",
                "enum": ["brief", "normal", "expanded"],
                "description": (
                    "Target size for this visible card: brief is about 40–90 Chinese characters; "
                    "normal is about 100–220; expanded is about 250–450. These are soft targets."
                ),
            },
        },
        "required": ["mode", "thinking", "length"],
    },
    "securitySchemes": [{"type": "noauth"}],
    "annotations": {
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
    "_meta": {
        "securitySchemes": [{"type": "noauth"}],
        "ui": {"resourceUri": WIDGET_URI, "visibility": ["model", "app"]},
        "openai/outputTemplate": WIDGET_URI,
        "openai/toolInvocation/invoking": "Thinking…",
        "openai/toolInvocation/invoked": "思考已显示",
    },
}


def record(args):
    """Optionally capture arguments without making capture part of tool correctness."""
    if not CAPTURE_ENABLED:
        return
    thinking = args.get("thinking") or ""
    print(
        f"\n{'=' * 60}\n[mode={args.get('mode')} length={args.get('length')} "
        "] "
        f"{len(thinking)} 字符\n{'=' * 60}"
    )
    print(thinking, flush=True)
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a") as fh:
            fh.write(json.dumps(args, ensure_ascii=False) + "\n")
    except Exception as exc:
        print(f"[warn] capture failed; tool call continues: {exc}", file=sys.stderr, flush=True)


def openapi(base):
    """OpenAPI 3.1 schema for GPT Actions and REST clients."""
    return {
        "openapi": "3.1.0",
        "info": {"title": "Visible Aside MCP", "version": "1.0.0",
                 "description": "Render a visible, styleable companion aside."},
        "servers": [{"url": base}],
        "paths": {"/think": {"post": {
            "operationId": "render_visible_aside",
            "summary": "Render this turn's visible aside",
            "description": TOOL["description"],
            "requestBody": {"required": True, "content": {"application/json": {
                "schema": {
                    "type": "object",
                    "required": ["mode", "thinking", "length"],
                    "properties": {
                        "mode": {"type": "string", "enum": ["analysis", "thinking"],
                                 "description": TOOL["inputSchema"]["properties"]["mode"]["description"]},
                        "thinking": {"type": "string",
                                     "description": TOOL["inputSchema"]["properties"]["thinking"]["description"]},
                        "length": {"type": "string", "enum": ["brief", "normal", "expanded"],
                                   "description": TOOL["inputSchema"]["properties"]["length"]["description"]},
                    },
                }}}},
            "responses": {"200": {"description": "rendered", "content": {"application/json": {
                "schema": {"type": "object", "properties": {"status": {"type": "string"}}}}}}},
        }}},
    }


PORT = (
    int(sys.argv[1])
    if len(sys.argv) > 1 and sys.argv[1].isdigit()
    else int(os.environ.get("PORT", "8787"))
)

mcp = FastMCP(
    name="sol-visible-aside-mcp",
    instructions=(
        "在正式回答前，调用 render_visible_aside 显示一段用户可见的即时思考。"
        "自动选择分析或思考模式与合适长度；优先用多个短行呈现停顿、试探和逐步推进。"
    ),
    host=BIND_HOST,
    port=PORT,
    streamable_http_path="/mcp",
    json_response=True,
    stateless_http=True,
)


@mcp.tool(
    name="render_visible_aside",
    title="想了想",
    description=TOOL["description"],
    annotations=ToolAnnotations(
        title="想了想",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
    meta=TOOL["_meta"],
    structured_output=False,
)
def render_visible_aside(
    mode: Annotated[
        Literal["analysis", "thinking"],
        Field(description=STYLE_DESCRIPTIONS[PROMPT_LANGUAGE]),
    ],
    thinking: Annotated[str, Field(description=THINKING_DESCRIPTIONS[PROMPT_LANGUAGE])],
    length: Annotated[
        Literal["brief", "normal", "expanded"],
        Field(description=TOOL["inputSchema"]["properties"]["length"]["description"]),
    ],
) -> CallToolResult:
    args = {
        "mode": mode,
        "thinking": thinking,
        "length": length,
    }
    record(args)
    return CallToolResult(
        content=[TextContent(type="text", text="旁白已显示")],
        isError=False,
        **{"_meta": args},
    )


@mcp.resource(
    WIDGET_URI,
    name="sol-visible-aside",
    title="想了想",
    description="以接近 ChatGPT 官端的白灰样式显示本轮即时思考。",
    mime_type=WIDGET_MIME,
    meta={
        "ui": {"prefersBorder": True},
        "openai/widgetPrefersBorder": True,
        "openai/widgetDescription": "一块可折叠的白灰即时思考区域，显示短句、停顿和逐步推进。",
    },
)
def visible_aside_widget() -> str:
    return WIDGET_HTML


@mcp.custom_route("/health", methods=["GET"])
async def health(_request: Request) -> JSONResponse:
    return JSONResponse({
        "status": "ok",
        "service": "sol-visible-aside-mcp",
        "promptLanguage": PROMPT_LANGUAGE,
        "transport": "official-python-sdk",
    })


if __name__ == "__main__":
    print(f"Visible Aside MCP listening on http://{BIND_HOST}:{PORT}/mcp")
    print(f"Prompt language: {PROMPT_LANGUAGE}")
    print(f"Capture: {'enabled -> ' + str(LOG) if CAPTURE_ENABLED else 'disabled'}")
    mcp.run(transport="streamable-http")
