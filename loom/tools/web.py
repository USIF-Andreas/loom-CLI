"""Web tools: search the web and fetch URLs.

``web_search`` uses the DuckDuckGo HTML endpoint (no API key required) and
falls back to a clear error if the network is unavailable. ``fetch_url``
downloads and returns the text/content of a web page. Both require network
access; failures are returned as plain strings so the agent loop keeps going.
"""

from __future__ import annotations

import re

import requests

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

_TIMEOUT = 20
_MAX_CHARS = 12000


def web_search(query: str, max_results: int = 5) -> str:
    """Search the web via DuckDuckGo and return a list of result snippets.

    Returns formatted ``title — url`` lines plus a short snippet per result.
    No API key needed.
    """
    try:
        resp = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
    except Exception as exc:  # network issue — don't crash the agent
        return f"Error: web search failed: {type(exc).__name__}: {exc}"

    html = resp.text
    results = _parse_ddg(html, max_results)
    if not results:
        return f"No results found for: {query}"

    lines = [f"Web search results for: {query}"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}")
        lines.append(f"   {r['url']}")
        if r.get("snippet"):
            lines.append(f"   {r['snippet']}")
    return "\n".join(lines)


def _parse_ddg(html: str, max_results: int) -> list[dict]:
    # Each result is wrapped in a class="result__a" link and a snippet in
    # class="result__snippet". Parse with regex (no html parser dependency).
    links = re.findall(
        r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.S
    )
    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.S)
    out: list[dict] = []
    for i, (href, title) in enumerate(links[:max_results]):
        # DuckDuckGo wraps the real URL in a redirect; decode uddg param.
        url = href
        m = re.search(r"uddg=([^&]+)", href)
        if m:
            from urllib.parse import unquote

            url = unquote(m.group(1))
        snippet = ""
        if i < len(snippets):
            snippet = re.sub(r"<[^>]+>", "", snippets[i])
            snippet = re.sub(r"\s+", " ", snippet).strip()
        out.append(
            {
                "title": re.sub(r"<[^>]+>", "", title).strip(),
                "url": url,
                "snippet": snippet,
            }
        )
    return out


def fetch_url(url: str, max_chars: int = _MAX_CHARS) -> str:
    """Download a URL and return its readable text content (best-effort).

    Strips HTML tags for readability. Returns an error string on failure.
    """
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
    except Exception as exc:
        return f"Error: failed to fetch {url}: {type(exc).__name__}: {exc}"

    ctype = resp.headers.get("Content-Type", "")
    text = resp.text
    if "html" in ctype or "<" in text[:200]:
        text = _html_to_text(text)
    if len(text) > max_chars:
        text = text[:max_chars] + f"\n... [truncated to {max_chars} chars] ..."
    return f"--- {url} ({ctype}) ---\n{text}"


def _html_to_text(html: str) -> str:
    # Lightweight tag stripping; keep line breaks for links/titles.
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    html = re.sub(r"</(p|div|li|h[1-6])>", "\n", html, flags=re.I)
    html = re.sub(r"<[^>]+>", "", html)
    html = re.sub(r"&nbsp;", " ", html)
    html = re.sub(r"&amp;", "&", html)
    html = re.sub(r"&lt;", "<", html)
    html = re.sub(r"&gt;", ">", html)
    html = re.sub(r"[ \t]+", " ", html)
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html.strip()
