"""
Insurance knowledge base builder.

The builder turns existing social pain points into a bilingual research index
and enriches that index with official/authoritative source discovery.
"""
import hashlib
import json
import logging
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


DEFAULT_PAIN_QUERY_MODIFIERS = {
    "claim_denied": ["claims process", "appeal denied claim"],
    "denied": ["claims process", "appeal denied claim"],
    "cost": ["cost", "premium", "subsidy"],
    "confusion": ["explained", "terms", "guide"],
    "coverage_gap": ["coverage exclusions", "what is covered"],
    "shopping": ["compare", "how to choose"],
    "fraud": ["scam warning", "avoid fraud"],
    "service": ["complaint", "consumer help"],
    "other": ["consumer guide"],
}


class KnowledgeBaseBuilder:
    def __init__(self, config: dict, db, reporter=None):
        self.config = config
        self.db = db
        self.reporter = reporter
        self.kb_config = config.get("knowledge_base", {})
        self.enabled = self.kb_config.get("enabled", True)
        self.topics = self.kb_config.get("topics", [])
        self.max_results = self.kb_config.get("max_results_per_query", 3)
        self.search_delay = self.kb_config.get("request_delay", 0.8)
        self.authoritative_domains = self.kb_config.get("authoritative_domains", [])
        self.pain_limit = self.kb_config.get("pain_point_limit", 1200)
        self.proxy = self._normalize_proxy(config.get("proxy", {}).get("socks5", ""))

    def build(
        self,
        fetch_sources: bool = True,
        max_results_per_query: int = None,
        pain_limit: int = None,
        topic_slugs: list = None,
    ) -> dict:
        """Build or refresh the knowledge base."""
        if not self.enabled:
            return {"enabled": False}

        topics = self._selected_topics(topic_slugs)
        all_topics = self.topics
        if not topics:
            logger.warning("Knowledge base has no configured topics.")
            return {"enabled": True, "topics": 0, "sources": 0, "pain_links": 0}

        for topic in topics:
            self.db.upsert_knowledge_topic(topic)
            for source in topic.get("curated_sources", []):
                self.db.upsert_knowledge_source(self._source_record(topic, source, "curated"))

        pain_points = self.db.get_all_pain_points_for_kb(limit=pain_limit or self.pain_limit)
        self.db.clear_knowledge_pain_links([topic["slug"] for topic in topics] if topic_slugs else None)
        allowed_slugs = {topic["slug"] for topic in topics} if topic_slugs else None
        link_count = self._link_pain_points(all_topics, pain_points, allowed_slugs)

        discovered_count = 0
        if fetch_sources:
            per_query = max_results_per_query or self.max_results
            for topic in topics:
                discovered_count += self._discover_topic_sources(topic, per_query)

        export_paths = {}
        if self.reporter:
            export_paths["markdown"] = self.reporter.generate_knowledge_base_report(self.db)
            export_paths.update(self.export_jsonl(self.reporter.output_dir))

        stats = self.db.get_knowledge_stats()
        stats.update({
            "enabled": True,
            "topics_processed": len(topics),
            "pain_points_scanned": len(pain_points),
            "pain_links_created": link_count,
            "sources_discovered": discovered_count,
            "export_paths": export_paths,
        })
        return stats

    def export_jsonl(self, output_dir: Path) -> dict:
        """Export topic cards as JSONL for future static-site generation."""
        kb_dir = Path(output_dir) / "knowledge_base"
        kb_dir.mkdir(parents=True, exist_ok=True)
        jsonl_path = kb_dir / "knowledge_items.jsonl"
        index_path = kb_dir / "topic_index.json"

        cards = []
        for topic in self.db.get_knowledge_topics():
            sources = self.db.get_knowledge_sources(topic["slug"], limit=50)
            pain_links = self.db.get_knowledge_pain_links(topic["slug"], limit=25)
            cards.append({
                "slug": topic["slug"],
                "name_en": topic["name_en"],
                "name_es": topic.get("name_es", ""),
                "priority": topic.get("priority", 50),
                "niche_tier": topic.get("niche_tier", ""),
                "audience": topic.get("audience", ""),
                "site_asset": topic.get("site_asset", ""),
                "description_en": topic.get("description_en", ""),
                "description_es": topic.get("description_es", ""),
                "source_count": topic.get("source_count", 0),
                "pain_link_count": topic.get("pain_link_count", 0),
                "sources": sources,
                "pain_samples": pain_links,
                "content_opportunities": self.content_opportunities(topic, pain_links),
            })

        with jsonl_path.open("w", encoding="utf-8") as f:
            for card in cards:
                f.write(json.dumps(card, ensure_ascii=False) + "\n")

        index = [
            {
                "slug": c["slug"],
                "name_en": c["name_en"],
                "name_es": c["name_es"],
                "priority": c["priority"],
                "source_count": c["source_count"],
                "pain_link_count": c["pain_link_count"],
                "site_asset": c["site_asset"],
            }
            for c in cards
        ]
        index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"jsonl": str(jsonl_path), "index": str(index_path)}

    def content_opportunities(self, topic: dict, pain_links: list) -> list:
        """Create deterministic content ideas without spending LLM tokens."""
        base_asset = topic.get("site_asset") or "consumer guide"
        categories = Counter(p.get("pain_category", "other") for p in pain_links)
        opportunities = []

        if not pain_links:
            opportunities.append(f"Build a bilingual {base_asset} anchored in official sources.")
            return opportunities

        for category, _count in categories.most_common(4):
            if category in ("claim_denied", "denied"):
                opportunities.append(
                    f"Add a claims/appeals explainer to the {base_asset}, with a state DOI complaint path."
                )
            elif category == "cost":
                opportunities.append(
                    f"Add cost inputs, subsidy checks, and premium tradeoff examples to the {base_asset}."
                )
            elif category == "confusion":
                opportunities.append(
                    f"Add plain-English and Spanish glossary blocks near every confusing term in the {base_asset}."
                )
            elif category == "coverage_gap":
                opportunities.append(
                    f"Add a coverage-gap checklist that separates covered, excluded, and optional add-on items."
                )
            elif category == "shopping":
                opportunities.append(
                    f"Add a comparison worksheet and quote-readiness checklist for users shopping this coverage."
                )
            elif category == "fraud":
                opportunities.append(
                    f"Add scam red flags and official verification links before any lead or affiliate CTA."
                )
            else:
                opportunities.append(
                    f"Use representative user questions as FAQ prompts, then answer from official sources."
                )

        return list(dict.fromkeys(opportunities))

    def _selected_topics(self, topic_slugs: list = None) -> list:
        if not topic_slugs:
            return self.topics
        selected = set(topic_slugs)
        return [topic for topic in self.topics if topic.get("slug") in selected]

    def _link_pain_points(
        self,
        topics: list,
        pain_points: list,
        allowed_slugs: set = None,
    ) -> int:
        topic_terms = {
            topic["slug"]: [term.lower() for term in topic.get("pain_keywords", [])]
            for topic in topics
        }
        link_count = 0

        for pp in pain_points:
            text = " ".join([
                pp.get("title", ""),
                pp.get("excerpt", ""),
                pp.get("matched_keywords", ""),
                pp.get("category", ""),
            ]).lower()
            matched_topics = [
                slug for slug, terms in topic_terms.items()
                if any(term and term in text for term in terms)
            ]

            if not matched_topics:
                matched_topics = self._fallback_topics(pp, topics)

            for slug in matched_topics[:3]:
                if allowed_slugs and slug not in allowed_slugs:
                    continue
                self.db.insert_knowledge_pain_link({
                    "topic_slug": slug,
                    "platform": pp["platform"],
                    "item_id": pp["item_id"],
                    "pain_category": pp.get("category", ""),
                    "severity": pp.get("severity", ""),
                    "lang": pp.get("lang", ""),
                    "title": pp.get("title", ""),
                    "url": pp.get("url", ""),
                    "excerpt": pp.get("excerpt", ""),
                })
                link_count += 1

        logger.info("Knowledge base linked %s pain points to topics", link_count)
        return link_count

    def _fallback_topics(self, pp: dict, topics: list) -> list:
        category = pp.get("category", "")
        title = (pp.get("title", "") + " " + pp.get("excerpt", "")).lower()
        slugs = {topic["slug"] for topic in topics}

        if "medicare" in title and "medicare" in slugs:
            return ["medicare"]
        if any(w in title for w in ["daca", "immigrant", "inmigrante"]) and "immigrant_health" in slugs:
            return ["immigrant_health"]
        if category == "fraud" and "insurance_scams" in slugs:
            return ["insurance_scams"]
        if category in ("confusion", "shopping") and "insurance_terms" in slugs:
            return ["insurance_terms"]
        if category in ("claim_denied", "denied", "coverage_gap") and "claims_appeals" in slugs:
            return ["claims_appeals"]
        return ["insurance_terms"] if "insurance_terms" in slugs else []

    def _discover_topic_sources(self, topic: dict, max_results_per_query: int) -> int:
        try:
            from ddgs import DDGS
        except ImportError:
            logger.warning("ddgs is not installed; skipping knowledge source discovery.")
            return 0

        inserted = 0
        search_queries = self._topic_search_queries(topic)
        if not search_queries:
            return 0

        try:
            with DDGS(proxy=self.proxy, timeout=20) as ddgs:
                for query in search_queries:
                    for result in ddgs.text(query, max_results=max_results_per_query):
                        href = result.get("href", "")
                        if not href:
                            continue
                        if not self._is_allowed_domain(href, topic):
                            continue
                        source = {
                            "title": result.get("title", href),
                            "url": href,
                            "snippet": result.get("body", ""),
                            "lang": self._detect_lang_from_query(query),
                            "source_type": "search_result",
                            "authority": self._domain(href),
                            "trust_level": self._trust_level(href),
                            "search_query": query,
                        }
                        self.db.upsert_knowledge_source(
                            self._source_record(topic, source, "search")
                        )
                        inserted += 1
                    time.sleep(self.search_delay)
        except Exception as e:
            logger.error("Knowledge source discovery failed for %s: %s", topic["slug"], e)
            return inserted

        return inserted

    def _topic_search_queries(self, topic: dict) -> list:
        queries = []
        for query in topic.get("search_queries", []):
            domains = topic.get("domains") or self.authoritative_domains
            if domains:
                for domain in domains[:4]:
                    queries.append(f"site:{domain} {query}")
            else:
                queries.append(query)

        pain_categories = self._topic_pain_categories(topic["slug"])
        for category, _count in pain_categories[:2]:
            modifiers = DEFAULT_PAIN_QUERY_MODIFIERS.get(category, [])
            for modifier in modifiers[:2]:
                for domain in (topic.get("domains") or self.authoritative_domains)[:2]:
                    queries.append(f"site:{domain} {topic.get('name_en', topic['slug'])} {modifier}")

        return list(dict.fromkeys(queries))

    def _topic_pain_categories(self, topic_slug: str) -> list:
        pain_links = self.db.get_knowledge_pain_links(topic_slug, limit=200)
        return Counter(p.get("pain_category", "other") for p in pain_links).most_common()

    def _source_record(self, topic: dict, source: dict, origin: str) -> dict:
        url = source["url"]
        source_id = "kb_" + hashlib.md5(f"{topic['slug']}|{url}".encode()).hexdigest()[:16]
        return {
            "id": source_id,
            "topic_slug": topic["slug"],
            "lang": source.get("lang", "en"),
            "source_type": source.get("source_type", "guide"),
            "authority": source.get("authority", self._domain(url)),
            "trust_level": source.get("trust_level", self._trust_level(url)),
            "title": source.get("title", url),
            "url": url,
            "domain": self._domain(url),
            "snippet": source.get("snippet", ""),
            "search_query": source.get("search_query", ""),
            "source_origin": origin,
        }

    def _detect_lang_from_query(self, query: str) -> str:
        q = query.lower()
        spanish_markers = [
            "seguro", "seguros", "medicare en espanol", "espanol",
            "inmigrante", "cobertura", "reclamacion", "deducible",
        ]
        if any(marker in q for marker in spanish_markers):
            return "es"
        return "en"

    def _domain(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed.netloc.lower().removeprefix("www.")

    def _trust_level(self, url: str) -> str:
        domain = self._domain(url)
        if domain.endswith(".gov") or "naic.org" in domain:
            return "official"
        if domain.endswith(".edu") or "cfp.net" in domain:
            return "professional"
        return "industry"

    def _is_allowed_domain(self, url: str, topic: dict) -> bool:
        allowed = topic.get("domains") or self.authoritative_domains
        if not allowed:
            return True
        domain = self._domain(url)
        return any(domain == item or domain.endswith("." + item) for item in allowed)

    def _normalize_proxy(self, proxy: str) -> str | None:
        if not proxy:
            return None
        return proxy.replace("socks5h://", "socks5://")
