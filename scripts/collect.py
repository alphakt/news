#!/usr/bin/env python3
"""固定源池（sources.json の feeds）を一括取得し、直近 N 時間の記事を lens 別に Markdown で出力する。
依存なし（標準ライブラリのみ）。HTTPS_PROXY / CA 設定は環境変数から自動で拾う。

使い方:
  python3 scripts/collect.py                 # 直近 48h, 標準出力（compact）
  python3 scripts/collect.py --hours 24 --out /path/to/collected.md
  python3 scripts/collect.py --health        # 各 feed の取得可否のみ表示
  python3 scripts/collect.py --no-pages      # pages（feed のないページ）の差分検出を省略

トークン節約のための設計:
  - seen.json にある URL は出力しない（既収録の再提示を防ぐ）。
  - 要約は 110 字まで。タイトル・日付・URL が主。
  - sources.json の pages はリンク一覧を state/page-snapshots.json と比較し、新規リンクだけを出す。
    変化のないページは 1 行で済み、モデルが WebFetch する必要がない。
"""
import argparse, json, re, sys, html, time, urllib.request, concurrent.futures as cf
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (X11; Linux x86_64) alphakt-news-collector/1.0"
NS = {"atom": "http://www.w3.org/2005/Atom", "dc": "http://purl.org/dc/elements/1.1/",
      "rss1": "http://purl.org/rss/1.0/", "content": "http://purl.org/rss/1.0/modules/content/"}

def fetch(url, timeout=30, retries=2):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"})
    for i in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception:
            if i == retries: raise
            time.sleep(2 * (i + 1))

def parse_date(s):
    if not s: return None
    s = s.strip()
    for f in (lambda x: parsedate_to_datetime(x), lambda x: datetime.fromisoformat(x.replace("Z", "+00:00"))):
        try:
            d = f(s)
            if d.tzinfo is None: d = d.replace(tzinfo=timezone.utc)
            return d
        except Exception: pass
    return None

def text(el, *paths):
    for p in paths:
        x = el.find(p, NS)
        if x is not None:
            if p.endswith("link") and x.get("href"): return x.get("href")
            if x.text: return x.text.strip()
    return ""

def strip_html(s, n=90):
    s = re.sub(r"<[^>]+>", " ", html.unescape(s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n] + ("…" if len(s) > n else "")

def parse_feed(raw):
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        # 未エスケープの & や制御文字を含む feed を救済
        fixed = re.sub(rb"&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", b"&amp;", raw)
        fixed = re.sub(rb"[\x00-\x08\x0b\x0c\x0e-\x1f]", b"", fixed)
        root = ET.fromstring(fixed)
    tag = root.tag.lower()
    items = []
    if tag.endswith("feed"):  # Atom
        for e in root.findall("atom:entry", NS):
            link = ""
            for l in e.findall("atom:link", NS):
                if l.get("rel") in (None, "alternate"): link = l.get("href") or ""; break
            items.append({"title": text(e, "atom:title"), "link": link,
                          "date": parse_date(text(e, "atom:published", "atom:updated")),
                          "summary": strip_html(text(e, "atom:summary", "atom:content"))})
    elif tag.endswith("rdf"):  # RSS 1.0
        for e in root.findall("rss1:item", NS):
            items.append({"title": text(e, "rss1:title"), "link": text(e, "rss1:link"),
                          "date": parse_date(text(e, "dc:date")), "summary": strip_html(text(e, "rss1:description"))})
    else:  # RSS 2.0
        for e in root.iter("item"):
            items.append({"title": text(e, "title"), "link": text(e, "link"),
                          "date": parse_date(text(e, "pubDate", "dc:date")),
                          "summary": strip_html(text(e, "description", "content:encoded"))})
    return items

def page_links(raw, base):
    """ページ内の <a> を (text, href) で返す。同一ホストで、テキスト 12 字以上のものだけ。"""
    from urllib.parse import urljoin, urlparse
    out = []
    host = urlparse(base).netloc
    for m in re.finditer(r'<a\s[^>]*href="([^"#]+)"[^>]*>(.*?)</a>', raw, re.S | re.I):
        href = urljoin(base, html.unescape(m.group(1)))
        text = strip_html(m.group(2), 160)
        if urlparse(href).netloc != host or len(text) < 12: continue
        out.append((text, href))
    seen = set(); uniq = []
    for t, h in out:
        if h in seen: continue
        seen.add(h); uniq.append((t, h))
    return uniq

def diff_pages(pages, snap_path):
    snap = json.loads(snap_path.read_text(encoding="utf-8")) if snap_path.exists() else {}
    report = []
    for pg in pages:
        url = pg["url"]
        try:
            raw = fetch(url).decode("utf-8", "ignore")
            links = page_links(raw, url)
        except Exception as e:
            report.append((pg, None, f"{type(e).__name__}: {e}"[:100])); continue
        old = set(snap.get(url, {}).get("links", []))
        new = [(t, h) for t, h in links if h not in old]
        first = url not in snap
        snap[url] = {"links": [h for _, h in links][:3000], "checked": datetime.now(timezone.utc).isoformat()}
        report.append((pg, [] if first else new[:15], "baseline" if first else None))
    snap_path.parent.mkdir(exist_ok=True)
    snap_path.write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    return report

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=48)
    ap.add_argument("--out")
    ap.add_argument("--health", action="store_true")
    ap.add_argument("--sources", default=str(ROOT / "sources.json"))
    ap.add_argument("--no-pages", action="store_true")
    a = ap.parse_args()
    src = json.loads(Path(a.sources).read_text(encoding="utf-8"))
    feeds = src["feeds"]
    since = datetime.now(timezone.utc) - timedelta(hours=a.hours)
    seen_path = ROOT / "seen.json"
    seen_urls = {i["url"].rstrip("/") for i in json.loads(seen_path.read_text(encoding="utf-8"))["items"]} if seen_path.exists() else set()

    def work(f):
        try:
            items = parse_feed(fetch(f["url"]))
            recent = [i for i in items if i["date"] and i["date"] >= since]
            if f.get("filter"):
                rx = re.compile(f["filter"], re.I)
                recent = [i for i in recent if rx.search(i["title"] + " " + i["summary"])]
            recent = [i for i in recent if i["link"].rstrip("/") not in seen_urls]
            recent = sorted(recent, key=lambda x: x["date"], reverse=True)[: f.get("max", 60)]
            return f, items, recent, None
        except Exception as e:
            return f, [], [], f"{type(e).__name__}: {e}"[:120]

    with cf.ThreadPoolExecutor(8) as ex:
        results = list(ex.map(work, feeds))

    if a.health:
        for f, items, recent, err in results:
            print(f"{'OK ' if not err else 'NG '} {len(items):4d} items / {len(recent):3d} recent  {f['lens']:8s} {f['name']}  {err or ''}")
        return

    out = [f"# 収集結果  window={a.hours}h  generated={datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M JST')}", ""]
    errs = [(f, e) for f, _, _, e in results if e]
    if errs:
        out.append("## 取得失敗"); out += [f"- {f['name']}: {e}" for f, e in errs]; out.append("")
    for lens in ("DEV", "CONSULT", "PM"):
        out.append(f"## {lens}")
        for f, _, recent, err in results:
            if f["lens"] != lens or not recent: continue
            out.append(f"### {f['name']} ({len(recent)})")
            for i in sorted(recent, key=lambda x: x["date"], reverse=True):
                d = i["date"].astimezone(timezone(timedelta(hours=9))).strftime("%m-%d %H:%M")
                out.append(f"- [{d}] {i['title']} — {i['link']}" + (f"\n  {i['summary']}" if i["summary"] else ""))
            out.append("")
    if not a.no_pages and src.get("pages"):
        out.append("## PAGES（feed なし。新規リンクのみ。変化なし＝WebFetch 不要）")
        for pg, new, err in diff_pages(src["pages"], ROOT / "state" / "page-snapshots.json"):
            if err == "baseline": out.append(f"- {pg['name']}: 初回スナップショット作成（次回から差分）")
            elif err: out.append(f"- {pg['name']}: 取得失敗 {err}")
            elif not new: out.append(f"- {pg['name']}: 変化なし")
            else:
                out.append(f"- {pg['name']}: 新規 {len(new)} 件")
                out += [f"    - {t} — {h}" for t, h in new]
        out.append("")
    s = "\n".join(out)
    if a.out: Path(a.out).write_text(s, encoding="utf-8"); print(f"wrote {a.out} ({len(s)} chars)")
    else: print(s)

if __name__ == "__main__":
    main()
