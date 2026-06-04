"""
Core engine — orchestrates scraping, analysis, and reporting.
"""
import logging
import time
from datetime import datetime

from .scraper import RedditScraper
from .analyzer import PainPointAnalyzer
from .llm_analyzer import LLMAnalyzer
from .database import Database
from .reporter import Reporter
from .youtube_scraper import YouTubeScraper
from .quora_scraper import QuoraScraper
from .trends_scraper import TrendsScraper
from .knowledge_base import KnowledgeBaseBuilder


logger = logging.getLogger(__name__)


class Engine:
    def __init__(self, config: dict):
        self.config = config
        self.scraper = RedditScraper(config)
        self.analyzer = PainPointAnalyzer(config)
        self.llm = LLMAnalyzer(config)
        self.db = Database(config["database"]["path"])
        self.reporter = Reporter(config["reports"]["output_dir"])
        self.yt = YouTubeScraper(config)
        self.quora = QuoraScraper(config)
        self.trends = TrendsScraper(config)
        self.knowledge_base = KnowledgeBaseBuilder(config, self.db, self.reporter)

    def run(self, subreddits: list = None, with_comments: bool = True):
        """Run a full scrape → analyze → report cycle."""
        targets = subreddits or self._get_all_subreddits()
        all_pain_points = []
        total_new = 0
        total_found = 0

        logger.info(f"Starting scrape cycle for {len(targets)} subreddits...")

        for subreddit in targets:
            log_id = self.db.log_scrape_start(subreddit)

            # Determine post limit based on tier
            limit = self._get_limit_for(subreddit)

            # Determine scraping strategy based on subreddit tier
            core_subs = set(self.config["reddit"].get("core_subreddits", []))
            is_core = subreddit in core_subs

            try:
                if is_core:
                    # Core insurance subs: scrape hot page (high signal)
                    posts = self.scraper.scrape_subreddit(subreddit, limit=limit)
                else:
                    # Adjacent/general subs: use keyword search (much higher SNR)
                    posts = self.scraper.search_subreddit(subreddit, limit=limit)
                total_found += len(posts)

                new_count = 0
                pp_count = 0

                for post in posts:
                    is_new = not self.db.post_exists(post["id"])
                    if is_new:
                        self.db.insert_post(post)
                        new_count += 1

                    # Analyze for pain points
                    comments = []
                    if with_comments and post.get("permalink"):
                        comments = self.scraper.scrape_comments(post["permalink"])

                    # Try LLM first, fall back to keyword pattern matching
                    pp = self.llm.analyze_post(post, comments)
                    if pp:
                        self.db.insert_pain_point(pp)
                        all_pain_points.append(pp)
                        pp_count += 1
                    else:
                        # LLM unavailable or returned not_insurance
                        # Fall back to keyword-based analysis for any missed signals
                        kws = self.analyzer.analyze_post(post, comments)
                        for kw_pp in kws:
                            self.db.insert_pain_point(kw_pp)
                            all_pain_points.append(kw_pp)
                            pp_count += 1

                    if is_new:
                        time.sleep(self.config["reddit"]["request_delay"] * 0.5)

                self.db.log_scrape_end(log_id, len(posts), new_count, pp_count)
                logger.info(
                    f"  r/{subreddit}: {len(posts)} posts, "
                    f"{new_count} new, {pp_count} pain points"
                )
                total_new += new_count

            except Exception as e:
                logger.error(f"Error scraping r/{subreddit}: {e}")
                self.db.log_scrape_end(log_id, 0, 0, 0)

        # Generate summary and report
        summary = self.analyzer.summarize(all_pain_points)
        # Add LLM-generated narrative summary
        llm_summary = self.llm.summarize(all_pain_points)
        if llm_summary:
            summary["llm_summary"] = llm_summary
        self.reporter.generate_daily_report(self.db, summary)

        logger.info(
            f"Cycle complete: {total_found} posts ({total_new} new), "
            f"{len(all_pain_points)} pain points"
        )
        return {"posts_new": total_new, "pain_points": len(all_pain_points), "summary": summary}

    def _get_all_subreddits(self) -> list:
        """Return flattened list of all configured subreddits."""
        reddit_cfg = self.config["reddit"]
        all_subs = []
        for key in ["core_subreddits", "adjacent_subreddits", "business_subreddits", "specialty_subreddits"]:
            subs = reddit_cfg.get(key, [])
            if subs:
                all_subs.extend(subs)
        # Fall back to old flat format
        if not all_subs:
            all_subs = reddit_cfg.get("subreddits", [])
        return all_subs

    def _get_limit_for(self, subreddit: str) -> int:
        """Return the post limit for a given subreddit based on its tier."""
        reddit_cfg = self.config["reddit"]
        if subreddit in reddit_cfg.get("core_subreddits", []):
            return reddit_cfg.get("core_post_limit", 50)
        elif subreddit in reddit_cfg.get("adjacent_subreddits", []):
            return reddit_cfg.get("adjacent_post_limit", 30)
        elif subreddit in reddit_cfg.get("business_subreddits", []):
            return reddit_cfg.get("business_post_limit", 25)
        elif subreddit in reddit_cfg.get("specialty_subreddits", []):
            return reddit_cfg.get("specialty_post_limit", 20)
        return reddit_cfg.get("post_limit", 25)

    def run_youtube(self):
        """Run YouTube search → comment extraction → pain point analysis."""
        logger.info("Starting YouTube scrape cycle...")

        videos = self.yt.run_all_searches()
        pp_count = 0

        for video in videos:
            # Store video
            self.db.insert_youtube_video(video)

            # Get comments + details if API available
            comments = self.yt.get_comments(video["id"])
            details = self.yt.get_video_details(video["id"])

            if details:
                video["view_count"] = details.get("view_count", 0)
                video["like_count"] = details.get("like_count", 0)
                video["comment_count"] = details.get("comment_count", 0)

            # Store comments
            for c in comments:
                self.db.insert_youtube_comment(video["id"], c)

            # Analyze for pain points using LLM
            post = {
                "id": video["id"],
                "title": video["title"],
                "selftext": video.get("description", ""),
                "subreddit": f"YT:{video.get('lang', '?')}",
                "url": video.get("url", ""),
                "author": video.get("channel", ""),
            }
            top_comments = comments[:10] if comments else []
            pp = self.llm.analyze_post(post, [
                {"score": c.get("likes", 0), "body": c.get("text", "")}
                for c in top_comments
            ])
            if pp:
                pp["video_id"] = video["id"]
                pp["post_id"] = video["id"]
                self.db.insert_youtube_pain_point(pp)
                pp_count += 1
            else:
                # Fallback to keyword analysis
                kws = self.analyzer.analyze_post(post, [
                    {"score": c.get("likes", 0), "body": c.get("text", "")}
                    for c in top_comments
                ])
                for kw_pp in kws:
                    kw_pp["video_id"] = video["id"]
                    self.db.insert_youtube_pain_point(kw_pp)
                    pp_count += 1

        stats = self.db.get_yt_stats()
        logger.info(
            f"YouTube cycle complete: {len(videos)} videos "
            f"({stats['spanish']} ES, {stats['english']} EN), {pp_count} pain points"
        )
        return {"videos": len(videos), "pain_points": pp_count, "stats": stats}

    def run_quora(self):
        """Run Quora search via DuckDuckGo → pain point analysis."""
        logger.info("Starting Quora search cycle...")
        items = self.quora.run_all_searches()
        pp_count = 0

        for item in items:
            self.db.insert_quora_post(item)

            # LLM analyze the snippet as a pain point
            post = {
                "id": item["id"],
                "title": item["title"],
                "selftext": item.get("snippet", ""),
                "subreddit": f"Quora:{item.get('lang', '?')}",
                "url": item.get("url", ""),
            }
            pp = self.llm.analyze_post(post, None)  # No comments for Quora
            if pp:
                pp["video_id"] = item["id"]  # Reuse key name for compat
                pp["post_id"] = item["id"]
                self.db.insert_quora_pain_point(pp)
                pp_count += 1
            else:
                kws = self.analyzer.analyze_post(post, None)
                for kw_pp in kws:
                    self.db.insert_quora_pain_point(kw_pp)
                    pp_count += 1

        stats = self.db.get_quora_stats()
        logger.info(
            f"Quora cycle complete: {len(items)} posts "
            f"({stats['spanish']} ES, {stats['english']} EN), {pp_count} pain points"
        )
        return {"posts": len(items), "pain_points": pp_count, "stats": stats}

    def run_trends(self):
        """Run Google Trends + domain search for all keyword groups."""
        logger.info("Starting Trends cycle...")
        data = self.trends.run_all()

        # Store trends data
        for group_name, result in data.get("trends", {}).items():
            if "error" not in result:
                self.db.insert_trends(group_name, result)

        # Store domain search results
        for item in data.get("domain_results", []):
            self.db.insert_trends_domain_result(item)

        stats = self.db.get_trends_stats()
        logger.info(
            f"Trends complete: {len(data.get('trends', {}))} groups, "
            f"{len(data.get('domain_results', []))} domain results"
        )
        return {"groups": len(data.get("trends", {})),
                "domain_results": len(data.get("domain_results", [])),
                "stats": stats}

    def run_knowledge_base(
        self,
        fetch_sources: bool = True,
        max_results_per_query: int = None,
        pain_limit: int = None,
        topic_slugs: list = None,
    ) -> dict:
        """Build the bilingual insurance knowledge base from existing data."""
        logger.info("Starting knowledge base build...")
        result = self.knowledge_base.build(
            fetch_sources=fetch_sources,
            max_results_per_query=max_results_per_query,
            pain_limit=pain_limit,
            topic_slugs=topic_slugs,
        )
        logger.info(
            "Knowledge base complete: %s topics, %s sources, %s pain links",
            result.get("topics", 0),
            result.get("sources", 0),
            result.get("pain_links", 0),
        )
        return result

    def search_keyword(self, keyword: str, subreddit: str = "all") -> list:
        """Search for a specific keyword across subreddits."""
        from bs4 import BeautifulSoup

        if subreddit == "all":
            search_url = "https://old.reddit.com/search"
        else:
            search_url = f"https://old.reddit.com/r/{subreddit}/search"

        soup = self.scraper._fetch(search_url, params={
            "q": keyword,
            "restrict_sr": "on" if subreddit != "all" else "off",
            "sort": "relevance",
            "t": "month",
        })

        if not soup:
            return []

        results = []
        for entry in soup.select("div.thing[data-type='link']"):
            post = self.scraper._parse_post_entry(entry, subreddit)
            if post:
                results.append(post)

        logger.info(f"Search '{keyword}' in r/{subreddit}: {len(results)} results")
        return results
