from __future__ import annotations

import asyncio
import logging
import random
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from playwright.async_api import Browser, TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)
SESSION_DIR = Path(__file__).resolve().parent / ".threads-session"


@dataclass
class Post:
    published_at: datetime
    text: str
    url: str
    likes: int = 0
    engagement: int = 0


class ThreadsCrawler:
    def __init__(
        self,
        max_scrolls: int = 5,
        scroll_pause_range: tuple[float, float] = (1.0, 2.5),
    ) -> None:
        self.max_scrolls = max_scrolls
        self.scroll_pause_range = scroll_pause_range

    async def search(
        self,
        keyword: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Post]:
        url = f"https://www.threads.net/search?q={quote_plus(keyword)}"

        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=str(SESSION_DIR),
                headless=True,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/128.0.0.0 Safari/537.36"
                ),
            )
            try:
                return await self._collect_posts(context, url, start_date, end_date)
            finally:
                await context.close()

    async def login_status(self) -> dict[str, str | bool | None]:
        if not SESSION_DIR.exists():
            return {"logged_in": False, "username": None, "profile_url": None}

        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=str(SESSION_DIR),
                headless=True,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/128.0.0.0 Safari/537.36"
                ),
            )
            try:
                page = await context.new_page()
                await page.goto("https://www.threads.net/", wait_until="domcontentloaded", timeout=30_000)
                await page.wait_for_timeout(1_500)
                profile = page.locator('a[href^="/@"]').first
                href = await profile.get_attribute("href") if await profile.count() else None
                if not href:
                    return {"logged_in": False, "username": None, "profile_url": None}
                username = href.removeprefix("/@").split("/")[0]
                return {
                    "logged_in": True,
                    "username": username,
                    "profile_url": f"https://www.threads.net{href}",
                }
            except (PlaywrightTimeoutError, OSError):
                return {"logged_in": False, "username": None, "profile_url": None}
            finally:
                await context.close()

    async def _collect_posts(
        self,
        browser: Browser,
        url: str,
        start_date: date | None,
        end_date: date | None,
    ) -> list[Post]:
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            await page.wait_for_timeout(2_000)
        except PlaywrightTimeoutError:
            logger.warning("Threads page timed out while loading: %s", url)

        posts: dict[str, Post] = {}
        for _ in range(self.max_scrolls + 1):
            for post in await self._extract_posts(page):
                published_date = post.published_at.date()
                if start_date and published_date < start_date:
                    continue
                if end_date and published_date > end_date:
                    continue
                key = f"{post.published_at.isoformat()}:{post.text}"
                posts[key] = post

            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(random.uniform(*self.scroll_pause_range))

        await page.close()
        return list(posts.values())

    async def _extract_posts(self, page) -> list[Post]:
        extracted: list[Post] = []
        timestamps = page.locator("time[datetime]")
        for index in range(await timestamps.count()):
            timestamp_element = timestamps.nth(index)
            try:
                timestamp = await timestamp_element.get_attribute("datetime")
                if not timestamp:
                    continue

                published_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                details = await timestamp_element.evaluate(
                    """element => {
                        let node = element.parentElement;
                        for (let level = 0; node && level < 12; level += 1) {
                            const content = (node.innerText || '').trim();
                            const link = node.querySelector('a[href*="/post/"]');
                            if (link && content.length >= 40 && content.length <= 1000) {
                                return { text: content, href: link.href };
                            }
                            node = node.parentElement;
                        }
                        return { text: '', href: '' };
                    }"""
                )
                text = details["text"].strip()
                if not text:
                    continue

                likes = self._extract_likes(text)
                extracted.append(
                    Post(
                        published_at=published_at,
                        text=text,
                        url=details["href"],
                        likes=likes,
                        engagement=likes,
                    )
                )
            except (ValueError, PlaywrightTimeoutError) as error:
                logger.debug("Skipping an unreadable post: %s", error)
        return extracted

    @staticmethod
    def _extract_likes(text: str) -> int:
        match = re.search(r"([\d,.]+)\s*([KMB])?\s*(?:likes?|個讚)?$", text, re.IGNORECASE)
        if not match:
            matches = re.findall(r"([\d,.]+)\s*([KMB])\b", text, re.IGNORECASE)
            if not matches:
                return 0
            value, suffix = matches[-1]
        else:
            value, suffix = match.group(1), match.group(2) or ""
        try:
            number = float(value.replace(",", ""))
            multiplier = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get(
                suffix.upper(), 1
            )
            return int(number * multiplier)
        except ValueError:
            return 0

async def analyze_keyword(
    keyword: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, list]:
    posts = await ThreadsCrawler().search(keyword, start_date, end_date)
    if not posts:
        return {"dates": [], "counts": [], "posts": [], "top_engagement": [], "top_likes": []}

    frame = pd.DataFrame(
        {
            "published_at": [post.published_at for post in posts],
            "text": [post.text for post in posts],
        }
    )
    frame["date"] = pd.to_datetime(frame["published_at"], utc=True).dt.strftime("%Y-%m-%d")
    daily_counts = frame.groupby("date", as_index=False).size().sort_values("date")

    def serialize(post: Post) -> dict[str, str | int]:
        return {
            "published_at": post.published_at.isoformat(),
            "text": post.text,
            "url": post.url,
            "likes": post.likes,
            "engagement": post.engagement,
        }

    top_engagement = sorted(posts, key=lambda post: post.engagement, reverse=True)[:10]
    top_likes = sorted(posts, key=lambda post: post.likes, reverse=True)[:10]

    return {
        "dates": daily_counts["date"].tolist(),
        "counts": daily_counts["size"].astype(int).tolist(),
        "posts": [serialize(post) for post in posts],
        "top_engagement": [serialize(post) for post in top_engagement],
        "top_likes": [serialize(post) for post in top_likes],
    }
