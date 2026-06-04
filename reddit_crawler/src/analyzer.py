"""
Pain point analyzer for insurance-related Reddit posts.
Uses keyword pattern matching to identify customer pain points.
"""
import logging
import re
from collections import Counter
from datetime import datetime

logger = logging.getLogger(__name__)


class PainPointAnalyzer:
    def __init__(self, config: dict):
        self.keywords = config["pain_point_analysis"]["keywords"]
        self.categories_config = config["pain_point_analysis"]["categories"]

    def analyze_post(self, post: dict, comments: list = None) -> list:
        """
        Analyze a post and its comments for pain points.
        Returns list of detected pain point dicts.
        """
        text = post.get("title", "")
        if post.get("selftext"):
            text += " " + post["selftext"]

        # Also analyze top comments (most signal)
        if comments:
            top_comments = sorted(comments, key=lambda c: c.get("score", 0), reverse=True)[:10]
            text += " " + " ".join(c.get("body", "") for c in top_comments)

        pain_points = []

        for category, patterns in self.keywords.items():
            matched = []
            for pattern in patterns:
                if pattern.lower() in text.lower():
                    matched.append(pattern)

            if matched:
                # Find excerpt surrounding the first match
                excerpt = self._extract_excerpt(text, matched[0])

                # Determine severity based on match count and intensity keywords
                severity = self._assess_severity(matched, text)

                pain_points.append({
                    "post_id": post["id"],
                    "category": category,
                    "matched_keywords": ", ".join(matched),
                    "excerpt": excerpt,
                    "severity": severity,
                })

        return pain_points

    def _extract_excerpt(self, text: str, keyword: str, context_chars: int = 200) -> str:
        """Extract the surrounding context around a keyword match."""
        idx = text.lower().find(keyword.lower())
        if idx == -1:
            return text[:context_chars]

        start = max(0, idx - context_chars // 2)
        end = min(len(text), idx + len(keyword) + context_chars // 2)
        excerpt = text[start:end].strip()
        if start > 0:
            excerpt = "..." + excerpt
        if end < len(text):
            excerpt += "..."
        return excerpt

    def _assess_severity(self, matched: list, text: str) -> str:
        """Assess pain point severity (high/medium/low)."""
        intensity_words = [
            "urgent", "desperate", "screwed", "terrible", "horrible",
            "nightmare", "fraud", "scam", "lawsuit", "dying", "bankrupt",
            "impossible", "helpless", "devastated"
        ]
        text_lower = text.lower()

        intensity_score = sum(1 for w in intensity_words if w in text_lower)
        match_score = len(matched)

        if intensity_score >= 3 or match_score >= 5:
            return "high"
        elif intensity_score >= 1 or match_score >= 3:
            return "medium"
        return "low"

    def detect_insurance_categories(self, text: str) -> list:
        """Detect which insurance categories the text relates to."""
        found = []
        text_lower = text.lower()
        for category, keywords in self.categories_config.items():
            if any(kw in text_lower for kw in keywords):
                found.append(category)
        return found

    def summarize(self, pain_points: list) -> dict:
        """Generate a summary of pain points."""
        cat_counts = Counter(pp["category"] for pp in pain_points)
        sev_counts = Counter(pp["severity"] for pp in pain_points)

        # Top recurring keywords
        all_kw = []
        for pp in pain_points:
            all_kw.extend(pp["matched_keywords"].split(", "))
        top_keywords = Counter(all_kw).most_common(10)

        return {
            "total": len(pain_points),
            "by_category": dict(cat_counts.most_common()),
            "by_severity": dict(sev_counts),
            "high_severity_count": sev_counts.get("high", 0),
            "top_keywords": top_keywords,
        }
