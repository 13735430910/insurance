"""
Google Trends + multi-site search via DuckDuckGo.
pytrends for keyword trends (no API key needed).
DuckDuckGo site: for searching target insurance domains.
"""
import logging
import time
import hashlib

logger = logging.getLogger(__name__)

INSURANCE_DOMAINS = [
    "nerdwallet.com",
    "investopedia.com",
    "policygenius.com",
    "thezebra.com",
    "valuepenguin.com",
    "forbes.com",
    "bankrate.com",
    "insurance.com",
]


class TrendsScraper:
    def __init__(self, config: dict):
        t_config = config.get("trends", {})
        self.enabled = t_config.get("enabled", True)
        self.kw_groups = t_config.get("keyword_groups", {})
        self.geo = t_config.get("geo", "US")
        self.timeframe = t_config.get("timeframe", "today 12-m")

    def get_trends(self, keywords: list, geo: str = None) -> dict:
        """Get Google Trends data for a set of keywords."""
        if geo is None:
            geo = self.geo

        try:
            from pytrends.request import TrendReq
            pytrends = TrendReq(hl="en-US", tz=360, timeout=15)
            pytrends.build_payload(kw_list=keywords[:5], cat=0,
                                    timeframe=self.timeframe, geo=geo, gprop="")
            time.sleep(1)

            interest = pytrends.interest_over_time()
            related = pytrends.related_queries()

            result = {"keywords": keywords, "geo": geo}
            if not interest.empty:
                result["interest_over_time"] = {
                    kw: interest[kw].tolist() for kw in keywords if kw in interest.columns
                }
            result["related_queries"] = {}
            for kw, queries in related.items():
                if queries is not None:
                    top = queries.get("top")
                    rising = queries.get("rising")
                    result["related_queries"][kw] = {
                        "top": top.head(10).to_dict("records") if top is not None and not top.empty else [],
                        "rising": rising.head(10).to_dict("records") if rising is not None and not rising.empty else [],
                    }
            return result
        except Exception as e:
            logger.error(f"Trends fetch failed: {e}")
            return {"keywords": keywords, "error": str(e)}

    def search_domains(self, keyword: str, max_results: int = 10) -> list:
        """Search insurance domains for a keyword via DuckDuckGo."""
        results = []
        for domain in INSURANCE_DOMAINS:
            query = f"site:{domain} {keyword}"
            try:
                from ddgs import DDGS
                with DDGS(proxy="socks5://127.0.0.1:1080", timeout=15) as ddgs:
                    for r in ddgs.text(query, max_results=3):
                        href = r.get("href", "")
                        if domain in href:
                            results.append({
                                "id": "gs_" + hashlib.md5(href.encode()).hexdigest()[:12],
                                "title": r.get("title", ""),
                                "url": href,
                                "snippet": r.get("body", ""),
                                "domain": domain,
                                "matched_keyword": keyword,
                            })
            except Exception:
                continue
            time.sleep(0.5)

        logger.info(f"  '{keyword}': {len(results)} results across {len(INSURANCE_DOMAINS)} domains")
        return results

    def run_all(self) -> dict:
        """Run trends + domain search for all keyword groups."""
        all_results = {"trends": {}, "domain_results": [], "at": time.strftime("%Y-%m-%d %H:%M")}
        seen = set()

        for group_name, keywords in self.kw_groups.items():
            logger.info(f"Trends group '{group_name}': {keywords}")
            all_results["trends"][group_name] = self.get_trends(keywords)
            time.sleep(1)

            for kw in keywords:
                items = self.search_domains(kw)
                for item in items:
                    if item["id"] not in seen:
                        seen.add(item["id"])
                        all_results["domain_results"].append(item)

        logger.info(
            f"Trends complete: {len(all_results['trends'])} groups, "
            f"{len(all_results['domain_results'])} domain results"
        )
        return all_results
