#!/usr/bin/env python3
"""
Reddit Insurance Pain Point Crawler
===================================
Scrapes insurance-related subreddits, identifies customer pain points,
and generates daily summary reports.

Usage:
    python main.py scrape              # Full scrape cycle
    python main.py scrape --no-comments  # Skip comment fetching (faster)
    python main.py scrape -s Insurance LifeInsurance  # Specific subreddits
    python main.py report              # Generate report from existing data
    python main.py search "claim denied"  # Search for keyword
    python main.py stats               # Show database statistics
"""
import argparse
import logging
import sys
from pathlib import Path

import yaml


def setup_logging(config: dict):
    log_config = config.get("logging", {})
    level = getattr(logging, log_config.get("level", "INFO"))
    log_file = log_config.get("file", "logs/crawler.log")

    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stderr),
        ],
    )


def load_config(config_path: str = None) -> dict:
    if config_path is None:
        config_path = Path(__file__).parent / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def cmd_scrape(args, config: dict):
    from src.engine import Engine

    engine = Engine(config)
    subreddits = args.subreddits if args.subreddits else None
    result = engine.run(subreddits=subreddits, with_comments=not args.no_comments)

    print(f"\nDone. {result['posts_new']} new posts, {result['pain_points']} pain points found.")
    if result["summary"]["high_severity_count"] > 0:
        print(f"⚠️  {result['summary']['high_severity_count']} HIGH severity items!")


def cmd_report(args, config: dict):
    from src.database import Database
    from src.reporter import Reporter
    from src.analyzer import PainPointAnalyzer

    db = Database(config["database"]["path"])
    analyzer = PainPointAnalyzer(config)
    reporter = Reporter(config["reports"]["output_dir"])

    pain_points = db.get_pain_points(limit=500)
    summary = analyzer.summarize(pain_points)
    reporter.generate_daily_report(db, summary)

    stats = db.get_stats()
    print(f"\nReport generated.")
    print(f"  Total posts: {stats['total_posts']}")
    print(f"  Total pain points: {stats['total_pain_points']}")
    if stats["pain_points_by_category"]:
        print(f"  Top category: {stats['pain_points_by_category'][0]}")
    db.close()


def cmd_search(args, config: dict):
    from src.engine import Engine

    engine = Engine(config)
    results = engine.search_keyword(args.keyword, subreddit=args.subreddit)

    print(f"\nSearch results for '{args.keyword}' in r/{args.subreddit}:")
    print("-" * 60)
    for i, post in enumerate(results[:20]):
        print(f"{i+1}. [{post['subreddit']}] {post['title']}")
        print(f"   Score: {post['score']} | Comments: {post['comment_count']}")
        print(f"   URL: {post['url']}")
        print()


def cmd_stats(args, config: dict):
    from src.database import Database

    db = Database(config["database"]["path"])
    stats = db.get_stats()

    print("\nDatabase Statistics")
    print("=" * 40)
    print(f"Total posts stored:    {stats['total_posts']}")
    print(f"Total pain points:     {stats['total_pain_points']}")
    print()
    print("Posts by subreddit:")
    for sub, cnt in stats["posts_by_subreddit"]:
        bar = "█" * min(cnt, 50)
        print(f"  r/{sub:25s} {cnt:5d} {bar}")
    print()
    print("Pain points by category:")
    for cat, cnt in stats["pain_points_by_category"]:
        print(f"  {cat:15s} {cnt:5d}")
    db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Reddit Insurance Pain Point Crawler"
    )
    parser.add_argument(
        "-c", "--config", default=None,
        help="Path to config.yaml (default: config.yaml in script dir)"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # scrape
    p_scrape = subparsers.add_parser("scrape", help="Run full scrape cycle")
    p_scrape.add_argument("-s", "--subreddits", nargs="*", help="Target subreddits")
    p_scrape.add_argument("--no-comments", action="store_true", help="Skip comment fetching")

    # report
    subparsers.add_parser("report", help="Generate report from existing data")

    # search
    p_search = subparsers.add_parser("search", help="Search for keyword")
    p_search.add_argument("keyword", help="Keyword to search for")
    p_search.add_argument("-s", "--subreddit", default="Insurance", help="Target subreddit")

    # youtube
    subparsers.add_parser("youtube", help="Run YouTube search + comment extraction")
    subparsers.add_parser("quora", help="Run Quora search via DuckDuckGo")
    subparsers.add_parser("trends", help="Run Google Trends + domain search")
    subparsers.add_parser("tstats", help="Show Trends database statistics")

    subparsers.add_parser("qstats", help="Show Quora database statistics")

    subparsers.add_parser("ytstats", help="Show YouTube database statistics")

    # stats
    subparsers.add_parser("stats", help="Show full database statistics")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    config = load_config(args.config)
    setup_logging(config)

    if args.command == "scrape":
        cmd_scrape(args, config)
    elif args.command == "report":
        cmd_report(args, config)
    elif args.command == "search":
        cmd_search(args, config)
    elif args.command == "stats":
        cmd_stats(args, config)
    elif args.command == "youtube":
        cmd_youtube(args, config)
    elif args.command == "ytstats":
        cmd_ytstats(args, config)
    elif args.command == "quora":
        cmd_quora(args, config)
    elif args.command == "qstats":
        cmd_qstats(args, config)
    elif args.command == "trends":
        cmd_trends(args, config)
    elif args.command == "tstats":
        cmd_tstats(args, config)


def cmd_trends(args, config):
    from src.engine import Engine
    engine = Engine(config)
    result = engine.run_trends()
    print(f"\nDone. {result['groups']} trend groups, {result['domain_results']} domain results.")


def cmd_tstats(args, config):
    from src.database import Database
    db = Database(config["database"]["path"])
    stats = db.get_trends_stats()
    print("\nTrends Database Statistics")
    print("=" * 40)
    print(f"Trend groups:      {stats['trends_groups']}")
    print(f"Domain results:    {stats['domain_results']}")
    db.close()
    from src.engine import Engine
    engine = Engine(config)
    result = engine.run_quora()
    print(f"\nDone. {result['posts']} posts, {result['pain_points']} pain points.")
    print(f"  Spanish: {result['stats']['spanish']} posts")
    print(f"  English: {result['stats']['english']} posts")


def cmd_qstats(args, config):
    from src.database import Database
    db = Database(config["database"]["path"])
    stats = db.get_quora_stats()
    print("\nQuora Database Statistics")
    print("=" * 40)
    print(f"Total posts:      {stats['total_posts']}")
    print(f"  Spanish (es):   {stats['spanish']}")
    print(f"  English (en):   {stats['english']}")
    print(f"Total pain points: {stats['total_pain_points']}")
    db.close()
    from src.engine import Engine
    engine = Engine(config)
    result = engine.run_youtube()
    print(f"\nDone. {result['videos']} videos, {result['pain_points']} pain points.")
    print(f"  Spanish: {result['stats']['spanish']} videos")
    print(f"  English: {result['stats']['english']} videos")


def cmd_ytstats(args, config):
    from src.database import Database
    db = Database(config["database"]["path"])
    stats = db.get_yt_stats()
    print("\nYouTube Database Statistics")
    print("=" * 40)
    print(f"Total videos:     {stats['total_videos']}")
    print(f"  Spanish (es):   {stats['spanish']}")
    print(f"  English (en):   {stats['english']}")
    print(f"Total pain points: {stats['total_pain_points']}")
    db.close()


if __name__ == "__main__":
    main()
