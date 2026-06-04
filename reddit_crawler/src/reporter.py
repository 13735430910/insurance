"""
Report generator — creates Markdown summary reports from pain point data.
"""
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class Reporter:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_daily_report(self, db, summary: dict, date_str: str = None) -> str:
        """Generate a daily pain point summary report."""
        if date_str is None:
            date_str = datetime.utcnow().strftime("%Y-%m-%d")

        pain_points = db.get_pain_points(limit=200)
        stats = db.get_stats()

        lines = []
        lines.append(f"# Insurance Pain Point Report — {date_str}")
        lines.append("")
        lines.append("> Auto-generated from Reddit insurance communities")
        lines.append("")
        lines.append("## Overview")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total posts scraped | {stats['total_posts']} |")
        lines.append(f"| Pain points detected | {stats['total_pain_points']} |")
        lines.append(f"| Subreddits monitored | {len(stats['posts_by_subreddit'])} |")
        lines.append("")

        # By category
        if stats["pain_points_by_category"]:
            lines.append("## Pain Points by Category")
            lines.append("")
            lines.append("| Category | Count |")
            lines.append("|----------|-------|")
            for cat, cnt in stats["pain_points_by_category"]:
                cat_label = self._category_label(cat)
                bar = "█" * min(cnt, 40)
                lines.append(f"| {cat_label} | {cnt} {bar} |")
            lines.append("")

        # LLM Insight Summary (if available)
        llm_summary_data = summary.get("llm_summary") if summary else None
        if llm_summary_data:
            lines.append("## AI Insight Summary")
            lines.append("")
            if llm_summary_data.get("top_themes"):
                lines.append("### Top Themes")
                for theme in llm_summary_data["top_themes"]:
                    lines.append(f"- {theme}")
                lines.append("")
            if llm_summary_data.get("most_impactful"):
                lines.append(f"### Most Impactful Finding")
                lines.append(f"{llm_summary_data['most_impactful']}")
                lines.append("")
            if llm_summary_data.get("actionable_insight"):
                lines.append(f"### Actionable Insight for Tool Builders")
                lines.append(f"{llm_summary_data['actionable_insight']}")
                lines.append("")
            if llm_summary_data.get("trend_alert"):
                lines.append(f"### Trend Alert")
                lines.append(f"{llm_summary_data['trend_alert']}")
                lines.append("")

        # Keyword summary
        if summary:
            lines.append(f"## Analysis Summary")
            lines.append("")
            lines.append(f"- **Total pain points found:** {summary['total']}")
            lines.append(f"- **High severity:** {summary['high_severity_count']}")
            lines.append("")

            if summary.get("top_keywords"):
                lines.append("### Most Frequent Keywords")
                lines.append("")
                for kw, cnt in summary["top_keywords"]:
                    lines.append(f"- `{kw}` ({cnt} occurrences)")
                lines.append("")

        # Top pain points
        if pain_points:
            lines.append("## Top Pain Points (Most Recent)")
            lines.append("")
            by_severity = sorted(pain_points, key=lambda p: (
                0 if p["severity"] == "high" else 1 if p["severity"] == "medium" else 2,
                -(len(p["matched_keywords"].split(",")))
            ))
            for i, pp in enumerate(by_severity[:30]):
                sev_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(pp["severity"], "⚪")
                cat_label = self._category_label(pp["category"])
                lines.append(f"### {i+1}. {sev_emoji} [{cat_label}] {pp['title']}")
                lines.append(f"- **Subreddit:** r/{pp['subreddit']}")
                lines.append(f"- **Matched:** {pp['matched_keywords']}")
                lines.append(f"- **Severity:** {pp['severity']}")
                if pp.get("url"):
                    lines.append(f"- **Link:** {pp['url']}")
                if pp.get("excerpt"):
                    lines.append(f"- **Excerpt:** {pp['excerpt']}")
                lines.append("")

        # Subreddit breakdown
        if stats["posts_by_subreddit"]:
            lines.append("## Posts by Subreddit")
            lines.append("")
            lines.append("| Subreddit | Posts |")
            lines.append("|-----------|-------|")
            for sub, cnt in stats["posts_by_subreddit"]:
                lines.append(f"| r/{sub} | {cnt} |")
            lines.append("")

        lines.append(f"---")
        lines.append(f"*Report generated: {datetime.utcnow().isoformat()} UTC*")

        content = "\n".join(lines)

        # Save brief version
        brief_path = self.output_dir / f"{date_str}_brief.md"
        brief_path.write_text(self._generate_brief(stats, summary, pain_points, date_str))

        # Save detailed version
        detail_path = self.output_dir / f"{date_str}_detailed.md"
        detail_path.write_text(content)

        logger.info(f"Reports saved: {brief_path}, {detail_path}")
        return content

    def _generate_brief(self, stats: dict, summary: dict, pain_points: list, date_str: str) -> str:
        """Generate a brief summary for quick scanning."""
        lines = []
        lines.append(f"# Daily Brief — {date_str}")
        lines.append("")
        lines.append(f"**{stats['total_pain_points']}** pain points from **{stats['total_posts']}** posts")
        lines.append("")

        if summary.get("high_severity_count", 0) > 0:
            lines.append(f"⚠️ **{summary['high_severity_count']} HIGH severity** items need attention.")
            lines.append("")

        if stats["pain_points_by_category"]:
            cats = stats["pain_points_by_category"][:5]
            lines.append("### Top Categories")
            for cat, cnt in cats:
                lines.append(f"- {self._category_label(cat)}: {cnt}")
            lines.append("")

        # Quick list of high-severity items
        high_items = [pp for pp in pain_points if pp["severity"] == "high"]
        if high_items:
            lines.append("### 🔴 High Severity")
            for pp in high_items[:10]:
                lines.append(f"- [{self._category_label(pp['category'])}] {pp['title']}")
            lines.append("")

        return "\n".join(lines)

    def _category_label(self, category: str) -> str:
        """Human-readable category label."""
        labels = {
            "denied": "Claim Denied",
            "cost": "Cost Concerns",
            "confusion": "Confusion",
            "service": "Poor Service",
            "coverage_gap": "Coverage Gap",
            "shopping": "Shopping/Comparison",
        }
        return labels.get(category, category.replace("_", " ").title())
