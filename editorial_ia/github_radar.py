#!/usr/bin/env python3
"""Recopilador editorial gratuito: SOLO BORRADORES; jamás publica ni modifica Spotify."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

FEEDS = {
    "OpenAI": "https://openai.com/news/rss.xml",
    "Google AI": "https://blog.google/technology/ai/rss/",
    "Google DeepMind": "https://deepmind.google/blog/rss.xml",
    "Hugging Face": "https://huggingface.co/blog/feed.xml",
    "TechCrunch IA": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "The Verge IA": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "MIT Technology Review": "https://www.technologyreview.com/feed/",
}
try:
    TZ = ZoneInfo("Europe/Madrid")
except ZoneInfoNotFoundError:
    # Windows sin base IANA instalada: el PC del podcast usa horario de Madrid.
    # En GitHub Actions Ubuntu la base IANA sí está disponible.
    TZ = datetime.now().astimezone().tzinfo
STOP = set("the and this that have with for from into their what about latest says said model models ai more new how of at is to on are was by it a an one two your our as using reports".split())
HYPE = ("the download:", "opinion:", "sponsored:", "podcast:", "weekly recap:")
BRANDS = {
    "openai": ("openai", "chatgpt", "codex"),
    "google": ("google", "gemini", "deepmind", "alphabet"),
    "anthropic": ("anthropic", "claude"),
    "nvidia": ("nvidia", "nemotron"),
    "meta": ("meta", "llama", "facebook", "instagram"),
    "microsoft": ("microsoft", "copilot"),
    "apple": ("apple", "siri"),
    "amazon": ("amazon", "aws"),
    "alibaba": ("alibaba", "qwen"),
}

class Plain(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

def clean(value, limit=300):
    parser = Plain()
    parser.feed(html.unescape(str(value or "")))
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()[:limit]

def norm(value):
    import unicodedata
    plain = "".join(ch for ch in unicodedata.normalize("NFD", str(value).lower()) if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", plain).strip()

def terms(title):
    return {w for w in norm(title).split() if len(w) > 3 and w not in STOP}

def parse_date(value):
    if not value:
        return None
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            date = parsedate_to_datetime(value)
        except (ValueError, TypeError, IndexError):
            return None
    return date.replace(tzinfo=timezone.utc) if date.tzinfo is None else date.astimezone(timezone.utc)

def field(item, name):
    node = item.find(name)
    return "" if node is None else "".join(node.itertext()).strip()

def parse_feed(raw, source):
    if len(raw) > 2_000_000:
        raise ValueError("Feed muy grande")
    root = ET.fromstring(raw)
    atom = root.tag.rsplit("}", 1)[-1] == "feed"
    entries = root.findall("{*}entry") if atom else root.findall(".//item")
    result = []
    for item in entries[:50]:
        title = clean(field(item, "{*}title") if atom else field(item, "title"), 190)
        if atom:
            links = item.findall("{*}link")
            link = next((x.get("href", "") for x in links if x.get("rel", "alternate") == "alternate"), "")
            pubdate = field(item, "{*}published") or field(item, "{*}updated")
            description = field(item, "{*}summary") or field(item, "{*}content")
        else:
            link = field(item, "link")
            pubdate = field(item, "pubDate") or field(item, "{*}date")
            description = field(item, "description") or field(item, "{*}encoded")
        u = urlparse(link)
        date = parse_date(pubdate)
        if not title or u.scheme != "https" or not u.netloc or not date:
            continue
        result.append({
            "headline_original": title,
            "url": link.split("#", 1)[0],
            "source": source,
            "published_at": date.isoformat(),
            "summary_original": clean(description, 330),
        })
    return result

def fetch(url):
    req = Request(url, headers={"User-Agent": "IAAlDia-Editorial-Radar/1.1 (public RSS; no image copying)"})
    with urlopen(req, timeout=12) as response:
        if response.status != 200:
            raise ValueError("Feed HTTP error")
        data = response.read(2_000_001)
        if len(data) > 2_000_000:
            raise ValueError("Feed demasiado grande")
        return data

def brand(title):
    phrase = " " + norm(title) + " "
    for company, markers in BRANDS.items():
        if any(" " + norm(m) + " " in phrase for m in markers):
            return company
    return "otro"

def overlaps_episode(title, episode):
    intro = re.split(r"Fuentes\s*:", clean(episode.get("descripcion", ""), 4500), flags=re.I)[0]
    news = [re.sub(r"^.*?\b\d\s*\.\s*", "", s) for s in re.split(r"\s*\|\s*", intro)]
    current = terms(title)
    for n in news:
        old = terms(n)
        shared = len(current & old)
        if shared >= 3 and shared / max(1, min(len(current), len(old))) >= .46:
            return True
    return False

def select(pool, episodes, now):
    latest = max(episodes, key=lambda e: int(e.get("numero", 0)), default={})
    cutoff = now - timedelta(days=7)
    unique = set()
    valid = []
    for story in pool:
        stamp = parse_date(story.get("published_at", ""))
        if not stamp or stamp < cutoff or stamp > now + timedelta(minutes=3):
            continue
        title = story["headline_original"]
        if title.lower().startswith(HYPE) or overlaps_episode(title, latest):
            continue
        fp = " ".join(sorted(terms(title)))
        if not fp or fp in unique:
            continue
        unique.add(fp)
        valid.append({
            **story,
            "brand": brand(title),
            "dedup_key": fp,
            "status": "CANDIDATO_SIN_VERIFICAR",
            "media_rights_verified": False,
            "noticia_verificada": False,
            "published": False,
            "es_title": None,
            "rank": (now - stamp).total_seconds() / 86400,
        })
    valid.sort(key=lambda s: s["rank"])
    chosen, company_ct, source_ct = [], {}, {}
    for max_count in (1, 2):
        for story in valid:
            if story in chosen:
                continue
            company, origin = story["brand"], story["source"]
            if source_ct.get(origin, 0) >= max_count + 1:
                continue
            if company != "otro" and company_ct.get(company, 0) >= max_count:
                continue
            chosen.append(story)
            company_ct[company] = company_ct.get(company, 0) + 1
            source_ct[origin] = source_ct.get(origin, 0) + 1
            if len(chosen) == 5:
                break
        if len(chosen) == 5:
            break
    for story in chosen:
        story.pop("rank", None)
    return chosen

def build(feeds, episodes, now, opener=fetch):
    news, failures = [], {}
    for name, url in feeds.items():
        try:
            news.extend(parse_feed(opener(url), name))
        except Exception as error:
            failures[name] = type(error).__name__
    if len(failures) == len(feeds):
        raise RuntimeError("Ninguna fuente RSS disponible")
    return {
        "project": "Inteligencia Artificial al Día",
        "account": "inteligenciaartificialaldia",
        "date_madrid": now.astimezone(TZ).date().isoformat(),
        "generated_at_utc": now.isoformat(),
        "state": "BORRADOR_SIN_PUBLICAR",
        "sources_ok": len(feeds) - len(failures),
        "sources_failed": failures,
        "candidates_found": len(news),
        "news": select(news, episodes, now),
        "published": False,
        "media_licensing_verified": False,
        "requires": [
            "Comprobar cada hecho con fuentes primarias",
            "Traducción y redacción en español peninsular",
            "Imagen o vídeo real con licencia reutilizable documentada",
            "Contrastar con publicaciones previas y episodio actual",
        ],
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=Path, default=Path("episodios.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("editorial_ia/output"))
    args = parser.parse_args()
    episodes = json.loads(args.episodes.read_text(encoding="utf-8-sig"))
    report = build(FEEDS, episodes, datetime.now(timezone.utc))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    dest = args.output_dir / ("candidatos_" + report["date_madrid"] + ".json")
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"file": str(dest), "sources_ok": report["sources_ok"], "candidates": len(report["news"]), "published": False}))

if __name__ == "__main__":
    main()
