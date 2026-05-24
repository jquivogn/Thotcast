import logging
from datetime import datetime

import feedparser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Article, Config
from app.services.cleaner import extract_article_text

logger = logging.getLogger(__name__)


async def fetch_and_store_articles(db: AsyncSession) -> int:
    result = await db.execute(select(Config).order_by(Config.id.desc()).limit(1))
    config = result.scalar_one_or_none()
    if not config:
        logger.warning("No config found — skipping RSS fetch")
        return 0

    keywords = [kw.lower() for kw in config.keywords]
    new_count = 0

    for feed_url in config.rss_feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                url = entry.get("link", "").strip()
                if not url:
                    continue

                existing = await db.execute(select(Article).where(Article.url == url))
                if existing.scalar_one_or_none():
                    continue

                title = entry.get("title", "").strip()
                raw = (
                    entry.get("summary", "")
                    or (entry.get("content") or [{}])[0].get("value", "")
                )
                content = extract_article_text(raw) or title

                if keywords:
                    haystack = (title + " " + content).lower()
                    if not any(kw in haystack for kw in keywords):
                        continue

                published = None
                if getattr(entry, "published_parsed", None):
                    try:
                        published = datetime(*entry.published_parsed[:6])
                    except Exception:
                        pass

                db.add(Article(
                    url=url,
                    title=title,
                    content=content,
                    source=feed_url,
                    published_at=published,
                ))
                new_count += 1

        except Exception as exc:
            logger.error("Error fetching feed %s: %s", feed_url, exc)

    await db.commit()
    return new_count
