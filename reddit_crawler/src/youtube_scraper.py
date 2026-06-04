"""
YouTube scraper for insurance-related videos and comments.
Dual mode: uses official API with key, falls back to youtube-search library without key.
"""
import hashlib
import logging
import time
from datetime import datetime
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

BASE_URL = "https://www.youtube.com"


class YouTubeScraper:
    def __init__(self, config: dict):
        yt_config = config.get("youtube", {})
        self.enabled = yt_config.get("enabled", True)
        self.api_key = yt_config.get("api_key", "")
        self.spanish_keywords = yt_config.get("spanish_keywords", [])
        self.english_keywords = yt_config.get("english_keywords", [])
        self.max_videos = yt_config.get("max_videos_per_keyword", 10)
        self.max_comments = yt_config.get("max_comments_per_video", 50)
        self.proxy = config.get("proxy", {}).get("socks5", "")

        self.use_api = bool(self.api_key)
        if self.use_api:
            self._init_api_client()

    def _init_api_client(self):
        from googleapiclient.discovery import build
        import httplib2

        http_kwargs = {}
        if self.proxy:
            # Google API client uses httplib2 — configure SOCKS5 proxy
            http_kwargs["proxy_info"] = httplib2.ProxyInfo(
                proxy_type=httplib2.socks.PROXY_TYPE_SOCKS5,
                proxy_host="127.0.0.1",
                proxy_port=1080,
            )

        http = httplib2.Http(**http_kwargs, timeout=30)
        self.youtube = build("youtube", "v3", developerKey=self.api_key, http=http)
        logger.info("YouTube Data API v3 initialized" + (" (with proxy)" if self.proxy else ""))

    def search_videos(self, keyword: str, lang: str = None) -> list:
        """Search YouTube for videos matching a keyword. Returns list of video dicts."""
        if self.use_api:
            return self._search_api(keyword, lang)
        else:
            return self._search_library(keyword)

    def _search_api(self, keyword: str, lang: str = None) -> list:
        """Use official YouTube Data API v3 to search videos."""
        params = {
            "q": keyword,
            "part": "snippet",
            "type": "video",
            "maxResults": self.max_videos,
            "order": "relevance",
        }
        if lang:
            params["relevanceLanguage"] = lang
            params["regionCode"] = "US"

        try:
            resp = self.youtube.search().list(**params).execute()
        except Exception as e:
            logger.error(f"YouTube API search failed for '{keyword}': {e}")
            return []

        videos = []
        for item in resp.get("items", []):
            snippet = item.get("snippet", {})
            video_id = item["id"]["videoId"]
            videos.append({
                "id": video_id,
                "title": snippet.get("title", ""),
                "description": snippet.get("description", "")[:500],
                "channel": snippet.get("channelTitle", ""),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "published_at": snippet.get("publishedAt", ""),
                "thumbnail": snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
                "matched_keyword": keyword,
                "lang": lang or "unknown",
            })

        logger.info(f"  API search '{keyword}': {len(videos)} videos")
        return videos

    def _search_library(self, keyword: str) -> list:
        """Use youtube-search-python (no API key needed)."""
        try:
            from youtubesearchpython import VideosSearch
            search = VideosSearch(keyword, limit=self.max_videos)
            results = search.result()
        except Exception as e:
            logger.error(f"YouTube search failed for '{keyword}': {e}")
            return []

        videos = []
        for item in results.get("result", []):
            video_id = item.get("id", "")
            videos.append({
                "id": video_id,
                "title": item.get("title", ""),
                "description": item.get("descriptionSnippet", [{}])[0].get("text", "")[:500] if item.get("descriptionSnippet") else "",
                "channel": item.get("channel", {}).get("name", ""),
                "url": item.get("link", f"https://www.youtube.com/watch?v={video_id}"),
                "published_at": item.get("publishedTime", ""),
                "thumbnail": item.get("thumbnails", [{}])[0].get("url", ""),
                "matched_keyword": keyword,
                "lang": self._detect_lang(keyword),
                # Extra fields from youtube-search library
                "duration": item.get("duration", ""),
                "view_count": item.get("viewCount", {}).get("text", ""),
            })

        logger.info(f"  Search '{keyword}': {len(videos)} videos")
        time.sleep(1)  # Rate limit for the library
        return videos

    def _detect_lang(self, keyword: str) -> str:
        """Detect language of keyword heuristically."""
        es_indicators = ["seguro", "aseguranza", "cuanto", "como", "para", "español", "espanol",
                         "medico", "mascotas", "vida", "casa", "auto", "inmigrantes", "comparativa"]
        if any(w in keyword.lower() for w in es_indicators):
            return "es"
        return "en"

    def get_comments(self, video_id: str) -> list:
        """Extract comments for a video. Requires API key."""
        if not self.use_api:
            logger.debug(f"  Skipping comments for {video_id} (no API key)")
            return []

        comments = []
        try:
            resp = self.youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=min(self.max_comments, 100),
                order="relevance",
                textFormat="plainText",
            ).execute()
        except Exception as e:
            # Comments might be disabled
            logger.debug(f"  Comments fetch failed for {video_id}: {e}")
            return []

        for item in resp.get("items", []):
            snippet = item["snippet"]["topLevelComment"]["snippet"]
            comments.append({
                "id": item["id"],
                "author": snippet.get("authorDisplayName", ""),
                "text": snippet.get("textDisplay", ""),
                "likes": snippet.get("likeCount", 0),
                "published_at": snippet.get("publishedAt", ""),
            })

        logger.info(f"  {video_id}: {len(comments)} comments")
        return comments

    def get_video_details(self, video_id: str) -> dict:
        """Get video statistics. Requires API key."""
        if not self.use_api:
            return {}
        try:
            resp = self.youtube.videos().list(
                part="statistics,snippet",
                id=video_id,
            ).execute()
            if resp.get("items"):
                stats = resp["items"][0].get("statistics", {})
                snippet = resp["items"][0].get("snippet", {})
                return {
                    "view_count": int(stats.get("viewCount", 0)),
                    "like_count": int(stats.get("likeCount", 0)),
                    "comment_count": int(stats.get("commentCount", 0)),
                    "tags": snippet.get("tags", []),
                }
        except Exception as e:
            logger.debug(f"  Details fetch failed for {video_id}: {e}")
        return {}

    def run_all_searches(self) -> list:
        """Run all configured keyword searches and return combined results."""
        all_videos = []
        seen_ids = set()

        # Spanish keywords
        for kw in self.spanish_keywords:
            videos = self.search_videos(kw, lang="es")
            for v in videos:
                if v["id"] not in seen_ids:
                    seen_ids.add(v["id"])
                    all_videos.append(v)

        # English keywords
        for kw in self.english_keywords:
            videos = self.search_videos(kw, lang="en")
            for v in videos:
                if v["id"] not in seen_ids:
                    seen_ids.add(v["id"])
                    all_videos.append(v)

        logger.info(f"YouTube search complete: {len(all_videos)} unique videos")
        return all_videos

    def enrich_with_comments(self, videos: list) -> list:
        """Add comments to video dicts."""
        for v in videos:
            v["comments"] = self.get_comments(v["id"])
            time.sleep(0.3)
        return videos
