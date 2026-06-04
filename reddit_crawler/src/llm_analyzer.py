"""
LLM-powered pain point analyzer using OpenAI-compatible API.
Uses local Qwen model for deep understanding of insurance pain points.
"""
import json
import logging
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an insurance industry analyst specializing in identifying customer pain points from social media posts.

Your task: analyze Reddit posts about insurance and extract structured pain points.

For each post, identify:
1. **category**: One of:
   - "claim_denied" — insurer refused to pay a claim
   - "cost" — premium too high, unexpected fees, affordability issues
   - "confusion" — user doesn't understand policy terms, coverage, or process
   - "service" — poor customer service, unresponsive agents, long wait times
   - "coverage_gap" — discovered something isn't covered, underinsured
   - "shopping" — actively looking for insurance, comparing options, asking recommendations
   - "fraud" — suspected scam, misleading sales, deceptive practices
   - "other" — doesn't fit above categories

2. **severity**: "high", "medium", or "low"
   - high: significant financial loss, health at risk, legal issues, fraud
   - medium: frustrating experience, moderate cost impact, coverage gap found
   - low: general question, curiosity, minor complaint

3. **summary**: One sentence summarizing the user's core problem (max 80 chars)

4. **insurance_type**: What type of insurance this is about (life, health, auto, home, pet, disability, medicare, business, travel, renters, umbrella, other)

Output as a JSON object with these exact keys:
{"category": "...", "severity": "...", "summary": "...", "insurance_type": "..."}

If the post is NOT about insurance or contains no pain point, output: {"category": "not_insurance", "severity": null, "summary": null, "insurance_type": null}"""


class LLMAnalyzer:
    def __init__(self, config: dict):
        llm_config = config.get("llm", {})
        self.enabled = llm_config.get("enabled", False)
        self.base_url = llm_config.get("base_url", "")
        self.model = llm_config.get("model", "")
        self.max_tokens = llm_config.get("max_tokens", 300)
        self.temperature = llm_config.get("temperature", 0.3)
        self.timeout = llm_config.get("timeout", 30)

        # Verify connectivity
        if self.enabled:
            self._check_connection()

    def _check_connection(self):
        try:
            resp = requests.get(
                f"{self.base_url}/../health",
                timeout=5,
                proxies={"http": None, "https": None},  # local network, no proxy
            )
            if resp.status_code == 200:
                logger.info(f"LLM connected: {self.model}")
            else:
                logger.warning(f"LLM health check: {resp.status_code}")
                self.enabled = False
        except Exception as e:
            logger.warning(f"LLM unavailable: {e}")
            self.enabled = False

    def analyze_post(self, post: dict, comments: list = None) -> dict | None:
        """Analyze a single post with LLM. Returns pain point dict or None."""
        if not self.enabled:
            return None

        # Build context text
        text = f"Title: {post.get('title', '')}"
        if post.get("selftext"):
            text += f"\nBody: {post['selftext'][:500]}"

        if comments:
            top_comments = sorted(
                comments, key=lambda c: c.get("score", 0), reverse=True
            )[:5]
            comment_text = "\n".join(
                f"- {c.get('body', '')[:200]}" for c in top_comments if c.get("body")
            )
            if comment_text:
                text += f"\nTop Comments:\n{comment_text}"

        try:
            result = self._call_llm(text)
            if result and result.get("category") != "not_insurance":
                return {
                    "post_id": post["id"],
                    "category": result["category"],
                    "matched_keywords": f"LLM: {result.get('summary', '')}",
                    "excerpt": result.get("summary", text[:200]),
                    "severity": result.get("severity", "medium"),
                    "insurance_type": result.get("insurance_type", ""),
                }
        except Exception as e:
            logger.error(f"LLM analysis failed for {post['id']}: {e}")

        return None

    def _call_llm(self, text: str) -> dict | None:
        """Call the LLM API and parse the JSON response."""
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
            },
            timeout=self.timeout,
            proxies={"http": None, "https": None},
        )
        resp.raise_for_status()

        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        # Parse JSON from response (handle markdown code blocks)
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content[:-3].strip()
            if content.startswith("json"):
                content = content[4:].strip()

        return json.loads(content)

    def summarize(self, pain_points: list) -> dict:
        """Generate a natural-language summary of all pain points."""
        if not self.enabled or len(pain_points) < 3:
            return None

        pp_text = "\n".join(
            f"- [{pp.get('category', '?')}] {pp.get('excerpt', 'N/A')}"
            for pp in pain_points[:30]
        )

        prompt = f"""Analyze these {len(pain_points)} insurance pain points from Reddit and create a concise summary report.

Pain points:
{pp_text}

Respond with a JSON object:
{{
  "top_themes": ["theme1", "theme2", "theme3"],
  "most_impactful": "The single most impactful finding...",
  "actionable_insight": "What an insurance tool website builder should know...",
  "trend_alert": "Any emerging trend or pattern noticed..."
}}"""

        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are an insurance market analyst. Output JSON only."},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 400,
                    "temperature": 0.3,
                },
                timeout=45,
                proxies={"http": None, "https": None},
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                if content.endswith("```"):
                    content = content[:-3].strip()
                if content.startswith("json"):
                    content = content[4:].strip()
            return json.loads(content)
        except Exception as e:
            logger.error(f"LLM summary failed: {e}")
            return None
