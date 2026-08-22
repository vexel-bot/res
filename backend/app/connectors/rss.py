import socket
from calendar import timegm
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
from ipaddress import ip_address
from urllib.parse import urlparse

import feedparser
import httpx

from .base import NormalizedSignal, SourceConnector


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def plain_text(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value)
    return " ".join(" ".join(parser.parts).split())


def validate_public_http_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("RSS URL must be a public HTTP or HTTPS URL")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if port not in {80, 443}:
        raise ValueError("RSS URL must use port 80 or 443")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        raise ValueError("RSS hostname could not be resolved") from error
    if not addresses or any(not ip_address(address[4][0]).is_global for address in addresses):
        raise ValueError("RSS hostname must resolve only to public addresses")


class RSSConnector(SourceConnector):
    def __init__(
        self,
        source_name: str,
        feed_url: str,
        region: str = "BR",
        language: str = "pt-BR",
        category: str = "general",
    ) -> None:
        validate_public_http_url(feed_url)
        self.source_name = source_name[:120]
        self.feed_url = feed_url
        self.region = region
        self.language = language
        self.category = category

    def collect(self) -> list[NormalizedSignal]:
        with httpx.Client(timeout=20, follow_redirects=False) as client:
            with client.stream("GET", self.feed_url, headers={"User-Agent": "NexusRadar/1.0"}) as response:
                response.raise_for_status()
                payload = bytearray()
                for chunk in response.iter_bytes():
                    if len(payload) + len(chunk) > 2_000_000:
                        raise ValueError("RSS feed exceeds the 2 MB safety limit")
                    payload.extend(chunk)
        feed = feedparser.parse(bytes(payload))
        collected: list[NormalizedSignal] = []
        now = datetime.now(UTC)
        for entry in feed.entries[:100]:
            parsed_time = entry.get("published_parsed") or entry.get("updated_parsed")
            published = datetime.fromtimestamp(timegm(parsed_time), UTC) if parsed_time else now
            title = str(entry.get("title", "")).strip()[:500]
            url = str(entry.get("link", "")).strip()[:4000]
            if not title or not url:
                continue
            summary = plain_text(str(entry.get("summary", "")))[:5000]
            tags = [str(item.get("term", ""))[:80] for item in entry.get("tags", [])[:20]]
            collected.append(
                NormalizedSignal(
                    source=self.source_name,
                    url=url,
                    title=title,
                    summary=summary,
                    raw_text=summary[:20_000],
                    published_at=published,
                    expires_at=published + timedelta(days=7),
                    language=self.language,
                    region=self.region,
                    category=tags[0] if tags else self.category,
                    topics=tags,
                )
            )
        return collected
