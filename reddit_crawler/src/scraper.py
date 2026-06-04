"""
Reddit scraper using old.reddit.com HTML parsing.
No API credentials needed — parses public HTML pages.
"""
import re
import time
import logging
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)

BASE_URL = "https://old.reddit.com"


class RedditScraper:
    def __init__(self, config: dict):
        self.post_limit = config["reddit"].get("post_limit",
            config["reddit"].get("core_post_limit", 25))
        self.sort = config["reddit"]["sort"]
        self.request_delay = config["reddit"]["request_delay"]
        self.search_keywords = config["reddit"]["search_keywords"]
        self.user_agent = config["user_agent"]

        self.session = requests.Session()

        # Manually construct headers for each request to avoid
        # requests library appending its default User-Agent.
        self._base_headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        }
        self.session.headers.clear()

        if config.get("proxy", {}).get("enabled"):
            socks5 = config["proxy"]["socks5"]
            self.session.proxies = {
                "http": socks5,
                "https": socks5,
            }

    def _fetch(self, url: str, params: dict = None) -> BeautifulSoup:
        """Fetch a URL and return parsed HTML."""
        try:
            resp = self.session.get(
                url, params=params, timeout=15,
                headers=self._base_headers,  # Explicit headers to avoid requests defaults
            )
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return BeautifulSoup("", "lxml")

    def scrape_subreddit(self, subreddit: str, limit: int = None) -> list:
        """Scrape posts from a single subreddit."""
        if limit is None:
            limit = self.post_limit
        posts = []
        url = f"{BASE_URL}/r/{subreddit}/{self.sort}/"

        logger.info(f"Scraping r/{subreddit} ({self.sort}, limit={limit})...")

        soup = self._fetch(url)
        if not soup:
            return posts

        # Parse each post entry
        entries = soup.select("div.thing[data-type='link']")
        for entry in entries[:limit]:
            post = self._parse_post_entry(entry, subreddit)
            if post:
                posts.append(post)

        logger.info(f"  r/{subreddit}: found {len(posts)} posts")
        time.sleep(self.request_delay)
        return posts

    def _parse_post_entry(self, entry, subreddit: str) -> dict | None:
        """Parse a single post div into a structured dict."""
        try:
            post_id = entry.get("data-fullname", "")
            if not post_id:
                return None

            # Title and link
            title_el = entry.select_one("a.title")
            if not title_el:
                return None
            title = title_el.text.strip()
            href = title_el.get("href", "")
            if href.startswith("/"):
                url = urljoin(BASE_URL, href)
            else:
                url = href

            # Score
            score_el = entry.select_one("div.score.unvoted")
            score = int(score_el.get("title", "0")) if score_el else 0

            # Author
            author_el = entry.select_one("a.author")
            author = author_el.text.strip() if author_el else "[deleted]"

            # Comments link
            comments_el = entry.select_one("a.comments")
            comment_count = 0
            if comments_el:
                cc_text = comments_el.text.strip()
                cc_match = re.search(r"(\d+)", cc_text)
                if cc_match:
                    comment_count = int(cc_match.group(1))

            # Timestamp
            time_el = entry.select_one("time")
            created_utc = None
            if time_el and time_el.get("datetime"):
                try:
                    created_utc = datetime.fromisoformat(
                        time_el["datetime"].replace("Z", "+00:00")
                    ).timestamp()
                except (ValueError, TypeError):
                    pass

            # Permalink
            permalink = ""
            if comments_el:
                permalink = urljoin(BASE_URL, comments_el.get("href", ""))

            return {
                "id": post_id,
                "subreddit": subreddit,
                "title": title,
                "url": url,
                "author": author,
                "score": score,
                "comment_count": comment_count,
                "created_utc": created_utc,
                "selftext": "",
                "permalink": permalink,
            }
        except Exception as e:
            logger.debug(f"Failed to parse post entry: {e}")
            return None

    def _parse_search_entry(self, entry, subreddit: str) -> dict | None:
        """Parse a search result entry (different HTML structure from listings)."""
        try:
            # Title
            title_el = entry.select_one("a.search-title")
            if not title_el:
                return None
            title = title_el.text.strip()
            href = title_el.get("href", "")
            url = urljoin(BASE_URL, href) if href.startswith("/") else href

            # Generate a stable ID from the URL
            import hashlib
            post_id = "t3_" + hashlib.md5(url.encode()).hexdigest()[:12]

            # Score
            score_el = entry.select_one(".search-score")
            score = 0
            if score_el:
                score_text = score_el.text.strip()
                score_match = re.search(r"(\d+)", score_text)
                if score_match:
                    score = int(score_match.group(1))

            # Author
            author_el = entry.select_one("a.author")
            author = author_el.text.strip() if author_el else "[deleted]"

            # Comments
            comments_el = entry.select_one("a.search-comments")
            comment_count = 0
            permalink = ""
            if comments_el:
                cc_text = comments_el.text.strip()
                cc_match = re.search(r"(\d+)", cc_text)
                if cc_match:
                    comment_count = int(cc_match.group(1))
                chref = comments_el.get("href", "")
                permalink = urljoin(BASE_URL, chref) if chref.startswith("/") else chref

            # Timestamp
            time_el = entry.select_one("time")
            created_utc = None
            if time_el and time_el.get("datetime"):
                try:
                    created_utc = datetime.fromisoformat(
                        time_el["datetime"].replace("Z", "+00:00")
                    ).timestamp()
                except (ValueError, TypeError):
                    pass

            # Subreddit
            sub_el = entry.select_one("a.search-subreddit-link")
            actual_sub = sub_el.text.strip() if sub_el else subreddit

            return {
                "id": post_id,
                "subreddit": actual_sub,
                "title": title,
                "url": url,
                "author": author,
                "score": score,
                "comment_count": comment_count,
                "created_utc": created_utc,
                "selftext": "",
                "permalink": permalink,
            }
        except Exception as e:
            logger.debug(f"Failed to parse search entry: {e}")
            return None

    def search_subreddit(self, subreddit: str, keywords: list = None, limit: int = 30) -> list:
        """
        Search a subreddit for posts matching insurance keywords.
        Much higher signal-to-noise than scraping hot pages for general subs.
        """
        if keywords is None:
            keywords = self.search_keywords

        posts = []
        seen_ids = set()

        # Search for each keyword to maximize coverage
        for kw in keywords[:5]:  # Top 5 keywords to keep it efficient
            # Build search URL with restrict_sr=on for subreddit-scoped search
            search_url = f"{BASE_URL}/r/{subreddit}/search"
            params = {
                "q": kw,
                "restrict_sr": "on",
                "sort": "new",
                "t": "month",
            }
            soup = self._fetch(search_url, params=params)
            if not soup:
                continue

            entries = soup.select("div.search-result-link")
            for entry in entries:
                post = self._parse_search_entry(entry, subreddit)
                if post and post["id"] not in seen_ids:
                    seen_ids.add(post["id"])
                    posts.append(post)

            if len(posts) >= limit:
                break
            time.sleep(self.request_delay * 0.5)

        logger.info(f"  r/{subreddit}: search found {len(posts)} insurance-related posts")
        time.sleep(self.request_delay)
        return posts[:limit]

    def scrape_comments(self, permalink: str, limit: int = 50) -> list:
        """Scrape comments from a post's permalink page."""
        if not permalink:
            return []

        comments = []
        soup = self._fetch(permalink)
        if not soup:
            return comments

        entries = soup.select("div.thing[data-type='comment']")
        for entry in entries[:limit]:
            try:
                comment = self._parse_comment_entry(entry)
                if comment:
                    comments.append(comment)
            except Exception as e:
                logger.debug(f"Failed to parse comment: {e}")

        time.sleep(self.request_delay)
        return comments

    def _parse_comment_entry(self, entry) -> dict | None:
        """Parse a single comment div."""
        comment_id = entry.get("data-fullname", "")
        if not comment_id:
            return None

        author_el = entry.select_one("a.author")
        author = author_el.text.strip() if author_el else "[deleted]"

        body_el = entry.select_one("div.md")
        body = body_el.text.strip() if body_el else ""

        if not body or body in ("[removed]", "[deleted]"):
            return None

        score_el = entry.select_one("span.score")
        score = 0
        if score_el:
            try:
                score = int(score_el.text.strip().rstrip(" points"))
            except ValueError:
                pass

        return {
            "id": comment_id,
            "author": author,
            "body": body,
            "score": score,
            "created_utc": None,
        }

    def filter_insurance_posts(self, posts: list) -> list:
        """Filter posts for insurance-relevant content using keyword matching."""
        keywords_lower = [k.lower() for k in self.search_keywords]
        filtered = []
        for post in posts:
            text = (post["title"] + " " + post.get("selftext", "")).lower()
            if any(kw in text for kw in keywords_lower):
                filtered.append(post)
        return filtered
