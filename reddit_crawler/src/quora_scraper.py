"""
Quora content discovery via DuckDuckGo search.
Quora itself has Cloudflare anti-bot protection, so we use DuckDuckGo
as a proxy to discover Quora questions and answers by their snippets.
"""
import hashlib
import logging
import time

logger = logging.getLogger(__name__)


class QuoraScraper:
    def __init__(self, config: dict):
        q_config = config.get("quora", {})
        self.enabled = q_config.get("enabled", True)
        self.spanish_keywords = q_config.get("spanish_keywords", [])
        self.english_keywords = q_config.get("english_keywords", [])
        self.max_results = q_config.get("max_results_per_keyword", 10)

    def search(self, keyword: str, max_results: int = None) -> list:
        """Search Quora via DuckDuckGo for insurance-related content."""
        if max_results is None:
            max_results = self.max_results

        query = f"site:quora.com {keyword}"
        results = []

        try:
            from ddgs import DDGS
            with DDGS(
                proxy="socks5://127.0.0.1:1080",
                timeout=20,
            ) as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    title = r.get("title", "")
                    href = r.get("href", "")
                    body = r.get("body", "")

                    # Skip non-Quora results
                    if "quora.com" not in href:
                        continue

                    # Generate stable ID from URL
                    post_id = "qu_" + hashlib.md5(href.encode()).hexdigest()[:12]

                    results.append({
                        "id": post_id,
                        "title": title,
                        "url": href,
                        "snippet": body,
                        "matched_keyword": keyword,
                        "lang": self._detect_lang(keyword),
                    })
        except Exception as e:
            logger.error(f"DuckDuckGo search failed for '{keyword}': {e}")
            return []

        logger.info(f"  Search '{keyword}': {len(results)} Quora results")
        time.sleep(1.5)
        return results

    def _detect_lang(self, keyword: str) -> str:
        es_words = ["seguro", "aseguranza", "cuanto", "como", "para",
                     "medico", "vida", "casa", "auto", "mascotas",
                     "inmigrantes", "comparativa", "español", "espanol"]
        if any(w in keyword.lower() for w in es_words):
            return "es"
        return "en"

    def run_all_searches(self) -> list:
        """Run all configured keyword searches."""
        all_results = []
        seen_ids = set()

        for kw in self.spanish_keywords:
            items = self.search(kw)
            for item in items:
                if item["id"] not in seen_ids:
                    seen_ids.add(item["id"])
                    all_results.append(item)

        for kw in self.english_keywords:
            items = self.search(kw)
            for item in items:
                if item["id"] not in seen_ids:
                    seen_ids.add(item["id"])
                    all_results.append(item)

        logger.info(f"Quora search complete: {len(all_results)} unique results")
        return all_results
