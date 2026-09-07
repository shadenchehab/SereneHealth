#!/usr/bin/env python3
"""Backfill DevRev article Content (devrev/rt) for articles with failed/skipped extraction.

The Agent reads the Content editor body (content_artifact / devrev/rt), not
description alone. When URL extraction is skipped, we scrape the source page
(or fall back to the article description) and upload a content_artifact.

Usage:
  python3 backfill_skipped_extractions.py --token-file /tmp/cabrillo_devrev_pat
  python3 backfill_skipped_extractions.py --token-file ... --all
  python3 backfill_skipped_extractions.py --token-file ... --only ART-7,ART-50
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

BASE = "https://api.devrev.ai"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


def load_token(token_file: Optional[str]) -> str:
    token = (os.environ.get("DEVREV_PAT") or os.environ.get("DEVREV_API_TOKEN") or "").strip()
    if not token and token_file:
        token = Path(token_file).read_text(encoding="utf-8").strip()
    if not token:
        raise SystemExit("Set DEVREV_PAT or --token-file")
    return token


def api(token: str, method: str, path: str, body: Optional[dict] = None) -> Tuple[int, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"message": raw}
        return e.code, parsed


class HTMLToText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []
        self._skip = 0
        self._href: Optional[str] = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if self._skip:
            self._skip += 1
            return
        attrs_d = dict(attrs)
        if tag in {"script", "style", "noscript", "svg", "nav", "footer", "header"}:
            self._skip = 1
            return
        if tag in {"h1", "h2", "h3", "h4"}:
            level = int(tag[1])
            self.parts.append("\n\n" + ("#" * level) + " ")
        elif tag == "p":
            self.parts.append("\n\n")
        elif tag == "br":
            self.parts.append("\n")
        elif tag in {"li"}:
            self.parts.append("\n- ")
        elif tag == "a":
            self._href = attrs_d.get("href")
            self.parts.append("[")

    def handle_endtag(self, tag: str) -> None:
        if self._skip:
            self._skip -= 1
            return
        if tag == "a":
            href = self._href or ""
            self.parts.append(f"]({href})" if href else "]")
            self._href = None
        elif tag in {"h1", "h2", "h3", "h4", "p"}:
            self.parts.append("\n\n")

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        self.parts.append(re.sub(r"\s+", " ", data))

    def output(self) -> str:
        text = html.unescape("".join(self.parts))
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Drop common Cabrillo chrome
        text = re.sub(
            r"Recognized as one of America's Best.*?Plant-A Insights Group",
            "",
            text,
            flags=re.I | re.S,
        )
        return text.strip()


def fetch_page_markdown(url: str) -> Optional[str]:
    if not url or not url.startswith("http"):
        return None
    # Strip fragment used for unique resource URLs
    clean = url.split("#")[0]
    req = urllib.request.Request(clean, headers={"User-Agent": UA, "Accept": "text/html"})
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None
    # Prefer main content-ish chunks
    parser = HTMLToText()
    try:
        parser.feed(raw)
        md = parser.output()
    except Exception:
        return None
    if len(md) < 80:
        return None
    # Cap size
    if len(md) > 50000:
        md = md[:50000].rstrip() + "\n\n[Content truncated.]"
    return md


def text_node(text: str, marks: Optional[List[dict]] = None) -> dict:
    node: Dict[str, Any] = {"type": "text", "text": text}
    if marks:
        node["marks"] = marks
    return node


def paragraph(text: str = "") -> dict:
    if not text:
        return {"type": "paragraph"}
    return {"type": "paragraph", "content": [text_node(text)]}


def heading(level: int, text: str) -> dict:
    return {
        "type": "heading",
        "attrs": {"level": max(1, min(level, 6))},
        "content": [text_node(text)],
    }


def bullet_list(items: List[str]) -> dict:
    return {
        "type": "bulletList",
        "content": [
            {"type": "listItem", "content": [paragraph(item)]}
            for item in items
            if item.strip()
        ],
    }


def markdown_to_rt(md: str) -> dict:
    lines = md.replace("\r\n", "\n").split("\n")
    blocks: List[dict] = []
    bullet_buf: List[str] = []

    def flush():
        nonlocal bullet_buf
        if bullet_buf:
            blocks.append(bullet_list(bullet_buf))
            bullet_buf = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        hm = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if hm:
            flush()
            blocks.append(heading(len(hm.group(1)), hm.group(2).strip()))
            continue
        bm = re.match(r"^[-*]\s+(.*)$", stripped)
        if bm:
            bullet_buf.append(bm.group(1).strip())
            continue
        flush()
        # strip simple markdown links to readable text + url
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", stripped)
        blocks.append(paragraph(text))
    flush()
    if not blocks:
        blocks = [paragraph("")]
    return {"type": "doc", "content": blocks}


def prepare_and_upload_rt(token: str, rt_doc: dict, file_name: str = "Article") -> str:
    import requests  # reliable multipart upload

    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {"file_name": file_name, "file_type": "devrev/rt", "configuration_set": "article_media"}
    prep = requests.post(f"{BASE}/artifacts.prepare", json=body, headers=h, timeout=45)
    if prep.status_code >= 400:
        body.pop("configuration_set", None)
        prep = requests.post(f"{BASE}/artifacts.prepare", json=body, headers=h, timeout=45)
    if prep.status_code >= 400:
        raise RuntimeError(f"artifacts.prepare {prep.status_code}: {prep.text[:400]}")
    data = prep.json()
    artifact_id = data.get("id")
    upload_url = data.get("url")
    form_data = {item["key"]: item["value"] for item in data.get("form_data", []) if item.get("key") is not None}
    if not artifact_id or not upload_url:
        raise RuntimeError(f"prepare missing id/url: {data}")

    payload = json.dumps(rt_doc, ensure_ascii=False).encode("utf-8")
    up = requests.post(
        upload_url,
        data=form_data,
        files={"file": (file_name, payload, "devrev/rt")},
        timeout=90,
    )
    if up.status_code not in (200, 201, 204):
        raise RuntimeError(f"upload failed {up.status_code}: {up.text[:400]}")
    return str(artifact_id)


def update_content(token: str, article_id: str, content_artifact_id: str, description: str) -> Tuple[int, Any]:
    for payload in (
        {"id": article_id, "content_artifact": content_artifact_id, "description": description[:1900]},
        {"id": article_id, "resource": {"content_artifact": content_artifact_id}, "description": description[:1900]},
    ):
        code, data = api(token, "POST", "/articles.update", payload)
        if code < 400:
            return code, data
    return code, data


def list_articles(token: str) -> List[dict]:
    arts: List[dict] = []
    cursor = None
    while True:
        body: Dict[str, Any] = {"limit": 100}
        if cursor:
            body["cursor"] = cursor
        code, data = api(token, "POST", "/articles.list", body)
        if code >= 400:
            raise SystemExit(f"articles.list failed: {code} {data}")
        arts.extend(data.get("articles") or [])
        cursor = data.get("next_cursor")
        if not cursor:
            break
        time.sleep(0.15)
    return arts


def needs_backfill(art: dict, force_all: bool) -> bool:
    if force_all:
        return True
    if not art.get("extracted_content"):
        return True
    # Also backfill if extracted artifact is the skip marker — checked by caller when needed
    return False


def build_markdown(art: dict) -> str:
    title = (art.get("title") or "Untitled").strip()
    url = ((art.get("resource") or {}).get("url") or "").split("#")[0]
    desc = (art.get("description") or "").strip()
    scraped = fetch_page_markdown(url) if url else None
    parts = [f"# {title}", ""]
    if url:
        parts.append(f"**Source:** {url}")
        parts.append("")
    if scraped:
        parts.append(scraped)
    elif desc:
        parts.append(desc)
        parts.append("")
        parts.append(
            "_Note: Automatic page extraction was skipped for this URL. "
            "Content below is from the article summary until a full page scrape succeeds._"
        )
    else:
        parts.append("No content available.")
    return "\n".join(parts).strip()


def short_desc(md: str, limit: int = 400) -> str:
    for line in md.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("**Source") or s.startswith("_Note"):
            continue
        s = re.sub(r"[*_`]", "", s)
        return (s[: limit - 1] + "…") if len(s) > limit else s
    return md[:limit]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--token-file", default="/tmp/cabrillo_devrev_pat")
    parser.add_argument("--all", action="store_true", help="Backfill Content for all articles")
    parser.add_argument("--only", default="", help="Comma-separated ART ids")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    token = load_token(args.token_file)
    only = {x.strip() for x in args.only.split(",") if x.strip()}

    arts = list_articles(token)
    if only:
        arts = [a for a in arts if a.get("display_id") in only]
    else:
        arts = [a for a in arts if needs_backfill(a, args.all)]

    # Prefer Cabrillo imported articles (skip probe ART-1/2 unless --only)
    if not only:
        arts = [a for a in arts if (a.get("display_id") or "") not in {"ART-1", "ART-2"}]

    arts = sorted(arts, key=lambda a: a.get("display_id") or "")
    print(f"Backfilling {len(arts)} articles (all={args.all})")

    ok = fail = 0
    results = []
    for i, art in enumerate(arts, 1):
        did = art.get("display_id")
        title = art.get("title")
        print(f"\n[{i}/{len(arts)}] {did} — {title}")
        try:
            md = build_markdown(art)
            print(f"  markdown={len(md)} chars")
            if args.dry_run:
                ok += 1
                results.append({"id": did, "status": "dry-run", "chars": len(md)})
                continue
            rt = markdown_to_rt(md)
            artifact_id = prepare_and_upload_rt(token, rt, file_name="Article")
            print(f"  uploaded {artifact_id}")
            code, data = update_content(token, art["id"], artifact_id, short_desc(md))
            if code >= 400:
                print(f"  ❌ update {code}: {data}")
                fail += 1
                results.append({"id": did, "status": "fail", "error": data})
            else:
                # verify resource artifacts include rt or content set
                code2, got = api(token, "GET", f"/articles.get?id={did}")
                a2 = (got or {}).get("article") or {}
                res = a2.get("resource") or {}
                arts_res = res.get("artifacts") or []
                types = [((x.get("file") or {}).get("type") or "") for x in arts_res]
                has_rt = "devrev/rt" in types
                print(f"  ✓ updated; resource.artifacts types={types}; has_rt={has_rt}; extracted={bool(a2.get('extracted_content'))}")
                ok += 1
                results.append({"id": did, "status": "ok", "has_rt": has_rt})
        except Exception as exc:
            print(f"  ❌ {exc}")
            fail += 1
            results.append({"id": did, "status": "fail", "error": str(exc)})
        time.sleep(0.35)

    Path("backfill_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("\n" + "=" * 40)
    print(f"OK: {ok}  Failed: {fail}")
    print("Wrote backfill_results.json")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
