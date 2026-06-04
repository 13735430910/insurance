"""
SQLite database for storing scraped posts, pain points, and knowledge base items.
"""
import sqlite3
from datetime import datetime
from pathlib import Path


class Database:
    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            subreddit TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            author TEXT,
            score INTEGER DEFAULT 0,
            comment_count INTEGER DEFAULT 0,
            created_utc REAL,
            selftext TEXT,
            permalink TEXT,
            scraped_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS comments (
            id TEXT PRIMARY KEY,
            post_id TEXT NOT NULL,
            author TEXT,
            body TEXT NOT NULL,
            score INTEGER DEFAULT 0,
            created_utc REAL,
            FOREIGN KEY (post_id) REFERENCES posts(id)
        );

        CREATE TABLE IF NOT EXISTS pain_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id TEXT NOT NULL,
            category TEXT NOT NULL,
            matched_keywords TEXT NOT NULL,
            excerpt TEXT,
            severity TEXT DEFAULT 'medium',
            created_at TEXT NOT NULL,
            FOREIGN KEY (post_id) REFERENCES posts(id)
        );

        CREATE TABLE IF NOT EXISTS scrape_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subreddit TEXT NOT NULL,
            posts_found INTEGER DEFAULT 0,
            posts_new INTEGER DEFAULT 0,
            pain_points_found INTEGER DEFAULT 0,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            status TEXT DEFAULT 'started'
        );

        CREATE INDEX IF NOT EXISTS idx_posts_subreddit ON posts(subreddit);
        CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_utc);
        CREATE INDEX IF NOT EXISTS idx_pain_points_post ON pain_points(post_id);
        CREATE TABLE IF NOT EXISTS youtube_videos (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            channel TEXT,
            url TEXT,
            description TEXT,
            matched_keyword TEXT,
            lang TEXT,
            view_count INTEGER DEFAULT 0,
            like_count INTEGER DEFAULT 0,
            comment_count INTEGER DEFAULT 0,
            published_at TEXT,
            scraped_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS youtube_comments (
            id TEXT PRIMARY KEY,
            video_id TEXT NOT NULL,
            author TEXT,
            text TEXT NOT NULL,
            likes INTEGER DEFAULT 0,
            published_at TEXT,
            FOREIGN KEY (video_id) REFERENCES youtube_videos(id)
        );

        CREATE TABLE IF NOT EXISTS youtube_pain_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            category TEXT NOT NULL,
            matched_keywords TEXT NOT NULL,
            excerpt TEXT,
            severity TEXT DEFAULT 'medium',
            created_at TEXT NOT NULL,
            FOREIGN KEY (video_id) REFERENCES youtube_videos(id)
        );

        CREATE INDEX IF NOT EXISTS idx_pain_points_category ON pain_points(category);
        CREATE INDEX IF NOT EXISTS idx_yt_videos_lang ON youtube_videos(lang);
        CREATE TABLE IF NOT EXISTS quora_posts (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT,
            snippet TEXT,
            matched_keyword TEXT,
            lang TEXT,
            scraped_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS quora_pain_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id TEXT NOT NULL,
            category TEXT NOT NULL,
            matched_keywords TEXT NOT NULL,
            excerpt TEXT,
            severity TEXT DEFAULT 'medium',
            created_at TEXT NOT NULL,
            FOREIGN KEY (post_id) REFERENCES quora_posts(id)
        );

        CREATE INDEX IF NOT EXISTS idx_yt_pp_video ON youtube_pain_points(video_id);
        CREATE TABLE IF NOT EXISTS trends_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_name TEXT NOT NULL,
            keywords TEXT NOT NULL,
            geo TEXT,
            interest_data TEXT,
            related_top TEXT,
            related_rising TEXT,
            fetched_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS trends_domain_results (
            id TEXT PRIMARY KEY,
            keyword TEXT NOT NULL,
            domain TEXT NOT NULL,
            title TEXT,
            url TEXT,
            snippet TEXT,
            fetched_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_quora_pp_post ON quora_pain_points(post_id);
        CREATE INDEX IF NOT EXISTS idx_trends_domain ON trends_domain_results(keyword);

        CREATE TABLE IF NOT EXISTS knowledge_topics (
            slug TEXT PRIMARY KEY,
            name_en TEXT NOT NULL,
            name_es TEXT,
            priority INTEGER DEFAULT 50,
            niche_tier TEXT,
            description_en TEXT,
            description_es TEXT,
            audience TEXT,
            site_asset TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS knowledge_sources (
            id TEXT PRIMARY KEY,
            topic_slug TEXT NOT NULL,
            lang TEXT DEFAULT 'en',
            source_type TEXT,
            authority TEXT,
            trust_level TEXT DEFAULT 'official',
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            domain TEXT,
            snippet TEXT,
            search_query TEXT,
            source_origin TEXT DEFAULT 'curated',
            fetched_at TEXT NOT NULL,
            FOREIGN KEY (topic_slug) REFERENCES knowledge_topics(slug)
        );

        CREATE TABLE IF NOT EXISTS knowledge_pain_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_slug TEXT NOT NULL,
            platform TEXT NOT NULL,
            item_id TEXT NOT NULL,
            pain_category TEXT,
            severity TEXT,
            lang TEXT,
            title TEXT,
            url TEXT,
            excerpt TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (topic_slug) REFERENCES knowledge_topics(slug)
        );

        CREATE INDEX IF NOT EXISTS idx_kb_sources_topic ON knowledge_sources(topic_slug);
        CREATE INDEX IF NOT EXISTS idx_kb_sources_lang ON knowledge_sources(lang);
        CREATE INDEX IF NOT EXISTS idx_kb_pain_topic ON knowledge_pain_links(topic_slug);
        """)
        self.conn.commit()

    def post_exists(self, post_id: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM posts WHERE id = ?", (post_id,)
        ).fetchone()
        return row is not None

    def insert_post(self, post: dict) -> bool:
        try:
            self.conn.execute("""
                INSERT OR IGNORE INTO posts
                (id, subreddit, title, url, author, score, comment_count,
                 created_utc, selftext, permalink, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                post["id"], post["subreddit"], post["title"], post["url"],
                post.get("author"), post.get("score", 0),
                post.get("comment_count", 0), post.get("created_utc"),
                post.get("selftext", ""), post.get("permalink", ""),
                datetime.utcnow().isoformat()
            ))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def insert_pain_point(self, pp: dict):
        self.conn.execute("""
            INSERT INTO pain_points (post_id, category, matched_keywords, excerpt, severity, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            pp["post_id"], pp["category"], pp["matched_keywords"],
            pp["excerpt"], pp.get("severity", "medium"),
            datetime.utcnow().isoformat()
        ))
        self.conn.commit()

    def log_scrape_start(self, subreddit: str) -> int:
        cur = self.conn.execute("""
            INSERT INTO scrape_log (subreddit, posts_found, started_at, status)
            VALUES (?, 0, ?, 'started')
        """, (subreddit, datetime.utcnow().isoformat()))
        self.conn.commit()
        return cur.lastrowid

    def log_scrape_end(self, log_id: int, posts_found: int, posts_new: int, pain_points: int):
        self.conn.execute("""
            UPDATE scrape_log
            SET posts_found = ?, posts_new = ?, pain_points_found = ?,
                completed_at = ?, status = 'completed'
            WHERE id = ?
        """, (posts_found, posts_new, pain_points, datetime.utcnow().isoformat(), log_id))
        self.conn.commit()

    def get_recent_posts(self, limit: int = 100, subreddit: str = None) -> list:
        if subreddit:
            rows = self.conn.execute(
                "SELECT * FROM posts WHERE subreddit = ? ORDER BY created_utc DESC LIMIT ?",
                (subreddit, limit)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM posts ORDER BY created_utc DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_pain_points(self, limit: int = 50, category: str = None) -> list:
        if category:
            rows = self.conn.execute("""
                SELECT pp.*, p.title, p.subreddit, p.url
                FROM pain_points pp
                JOIN posts p ON pp.post_id = p.id
                WHERE pp.category = ?
                ORDER BY pp.id DESC LIMIT ?
            """, (category, limit)).fetchall()
        else:
            rows = self.conn.execute("""
                SELECT pp.*, p.title, p.subreddit, p.url
                FROM pain_points pp
                JOIN posts p ON pp.post_id = p.id
                ORDER BY pp.id DESC LIMIT ?
            """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self) -> dict:
        total_posts = self.conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        total_pps = self.conn.execute("SELECT COUNT(*) FROM pain_points").fetchone()[0]
        pp_by_cat = self.conn.execute(
            "SELECT category, COUNT(*) as cnt FROM pain_points GROUP BY category ORDER BY cnt DESC"
        ).fetchall()
        posts_by_sub = self.conn.execute(
            "SELECT subreddit, COUNT(*) as cnt FROM posts GROUP BY subreddit ORDER BY cnt DESC"
        ).fetchall()
        return {
            "total_posts": total_posts,
            "total_pain_points": total_pps,
            "pain_points_by_category": [(r["category"], r["cnt"]) for r in pp_by_cat],
            "posts_by_subreddit": [(r["subreddit"], r["cnt"]) for r in posts_by_sub],
        }

    # --- YouTube methods ---

    def insert_youtube_video(self, video: dict) -> bool:
        try:
            self.conn.execute("""
                INSERT OR IGNORE INTO youtube_videos
                (id, title, channel, url, description, matched_keyword, lang,
                 view_count, like_count, comment_count, published_at, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                video["id"], video["title"], video.get("channel", ""),
                video["url"], video.get("description", ""),
                video.get("matched_keyword", ""), video.get("lang", ""),
                video.get("view_count", 0), video.get("like_count", 0),
                video.get("comment_count", 0), video.get("published_at", ""),
                datetime.utcnow().isoformat()
            ))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def insert_youtube_comment(self, video_id: str, comment: dict):
        self.conn.execute("""
            INSERT OR IGNORE INTO youtube_comments
            (id, video_id, author, text, likes, published_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            comment["id"], video_id, comment.get("author", ""),
            comment.get("text", ""), comment.get("likes", 0),
            comment.get("published_at", "")
        ))
        self.conn.commit()

    def insert_youtube_pain_point(self, pp: dict):
        self.conn.execute("""
            INSERT INTO youtube_pain_points (video_id, category, matched_keywords, excerpt, severity, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            pp["video_id"], pp["category"], pp["matched_keywords"],
            pp["excerpt"], pp.get("severity", "medium"),
            datetime.utcnow().isoformat()
        ))
        self.conn.commit()

    def get_youtube_videos(self, lang: str = None) -> list:
        if lang:
            rows = self.conn.execute(
                "SELECT * FROM youtube_videos WHERE lang = ? ORDER BY view_count DESC",
                (lang,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM youtube_videos ORDER BY view_count DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_youtube_pain_points(self, limit: int = 50) -> list:
        rows = self.conn.execute("""
            SELECT ypp.*, yv.title, yv.url, yv.lang
            FROM youtube_pain_points ypp
            JOIN youtube_videos yv ON ypp.video_id = yv.id
            ORDER BY ypp.id DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def get_yt_stats(self) -> dict:
        total = self.conn.execute("SELECT COUNT(*) FROM youtube_videos").fetchone()[0]
        es = self.conn.execute(
            "SELECT COUNT(*) FROM youtube_videos WHERE lang = 'es'"
        ).fetchone()[0]
        en = self.conn.execute(
            "SELECT COUNT(*) FROM youtube_videos WHERE lang = 'en'"
        ).fetchone()[0]
        total_pp = self.conn.execute(
            "SELECT COUNT(*) FROM youtube_pain_points"
        ).fetchone()[0]
        return {
            "total_videos": total, "spanish": es, "english": en,
            "total_pain_points": total_pp,
        }

    # --- Quora methods ---

    def insert_quora_post(self, post: dict):
        self.conn.execute("""
            INSERT OR IGNORE INTO quora_posts
            (id, title, url, snippet, matched_keyword, lang, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            post["id"], post["title"], post["url"], post.get("snippet", ""),
            post.get("matched_keyword", ""), post.get("lang", ""),
            datetime.utcnow().isoformat()
        ))
        self.conn.commit()

    def insert_quora_pain_point(self, pp: dict):
        self.conn.execute("""
            INSERT INTO quora_pain_points (post_id, category, matched_keywords, excerpt, severity, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            pp["post_id"], pp["category"], pp["matched_keywords"],
            pp["excerpt"], pp.get("severity", "medium"),
            datetime.utcnow().isoformat()
        ))
        self.conn.commit()

    def get_quora_stats(self) -> dict:
        total = self.conn.execute("SELECT COUNT(*) FROM quora_posts").fetchone()[0]
        es = self.conn.execute(
            "SELECT COUNT(*) FROM quora_posts WHERE lang = 'es'"
        ).fetchone()[0]
        en = self.conn.execute(
            "SELECT COUNT(*) FROM quora_posts WHERE lang = 'en'"
        ).fetchone()[0]
        total_pp = self.conn.execute(
            "SELECT COUNT(*) FROM quora_pain_points"
        ).fetchone()[0]
        return {
            "total_posts": total, "spanish": es, "english": en,
            "total_pain_points": total_pp,
        }

    # --- Trends methods ---

    def insert_trends(self, group_name: str, result: dict):
        self.conn.execute("""
            INSERT INTO trends_data (group_name, keywords, geo, interest_data, related_top, related_rising, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            group_name, ",".join(result.get("keywords", [])), result.get("geo", ""),
            str(result.get("interest_over_time", {})),
            str(result.get("related_queries", {}).get("top", [])),
            str(result.get("related_queries", {}).get("rising", [])),
            datetime.utcnow().isoformat()
        ))
        self.conn.commit()

    def insert_trends_domain_result(self, item: dict):
        self.conn.execute("""
            INSERT OR IGNORE INTO trends_domain_results (id, keyword, domain, title, url, snippet, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            item["id"], item.get("matched_keyword", ""), item.get("domain", ""),
            item.get("title", ""), item.get("url", ""), item.get("snippet", ""),
            datetime.utcnow().isoformat()
        ))
        self.conn.commit()

    def get_trends_data(self, limit: int = 20) -> list:
        rows = self.conn.execute(
            "SELECT * FROM trends_data ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_trends_stats(self) -> dict:
        total_groups = self.conn.execute(
            "SELECT COUNT(*) FROM trends_data"
        ).fetchone()[0]
        total_domains = self.conn.execute(
            "SELECT COUNT(*) FROM trends_domain_results"
        ).fetchone()[0]
        return {"trends_groups": total_groups, "domain_results": total_domains}

    # --- Knowledge base methods ---

    def upsert_knowledge_topic(self, topic: dict):
        self.conn.execute("""
            INSERT INTO knowledge_topics
            (slug, name_en, name_es, priority, niche_tier, description_en,
             description_es, audience, site_asset, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                name_en = excluded.name_en,
                name_es = excluded.name_es,
                priority = excluded.priority,
                niche_tier = excluded.niche_tier,
                description_en = excluded.description_en,
                description_es = excluded.description_es,
                audience = excluded.audience,
                site_asset = excluded.site_asset,
                updated_at = excluded.updated_at
        """, (
            topic["slug"], topic["name_en"], topic.get("name_es", ""),
            topic.get("priority", 50), topic.get("niche_tier", ""),
            topic.get("description_en", ""), topic.get("description_es", ""),
            topic.get("audience", ""), topic.get("site_asset", ""),
            datetime.utcnow().isoformat(),
        ))
        self.conn.commit()

    def upsert_knowledge_source(self, source: dict):
        self.conn.execute("""
            INSERT INTO knowledge_sources
            (id, topic_slug, lang, source_type, authority, trust_level, title,
             url, domain, snippet, search_query, source_origin, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                topic_slug = excluded.topic_slug,
                lang = excluded.lang,
                source_type = excluded.source_type,
                authority = excluded.authority,
                trust_level = excluded.trust_level,
                title = excluded.title,
                url = excluded.url,
                domain = excluded.domain,
                snippet = excluded.snippet,
                search_query = excluded.search_query,
                source_origin = excluded.source_origin,
                fetched_at = excluded.fetched_at
        """, (
            source["id"], source["topic_slug"], source.get("lang", "en"),
            source.get("source_type", ""), source.get("authority", ""),
            source.get("trust_level", "official"), source["title"],
            source["url"], source.get("domain", ""), source.get("snippet", ""),
            source.get("search_query", ""), source.get("source_origin", "curated"),
            datetime.utcnow().isoformat(),
        ))
        self.conn.commit()

    def clear_knowledge_pain_links(self, topic_slugs: list = None):
        if topic_slugs:
            placeholders = ",".join("?" for _ in topic_slugs)
            self.conn.execute(
                f"DELETE FROM knowledge_pain_links WHERE topic_slug IN ({placeholders})",
                tuple(topic_slugs),
            )
        else:
            self.conn.execute("DELETE FROM knowledge_pain_links")
        self.conn.commit()

    def insert_knowledge_pain_link(self, link: dict):
        self.conn.execute("""
            INSERT INTO knowledge_pain_links
            (topic_slug, platform, item_id, pain_category, severity, lang,
             title, url, excerpt, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            link["topic_slug"], link["platform"], link["item_id"],
            link.get("pain_category", ""), link.get("severity", ""),
            link.get("lang", ""), link.get("title", ""), link.get("url", ""),
            link.get("excerpt", ""), datetime.utcnow().isoformat(),
        ))
        self.conn.commit()

    def get_all_pain_points_for_kb(self, limit: int = 1000) -> list:
        items = []

        rows = self.conn.execute("""
            SELECT 'reddit' AS platform, pp.post_id AS item_id, pp.category,
                   pp.severity, '' AS lang, p.title, p.url, pp.excerpt,
                   pp.matched_keywords, pp.created_at
            FROM pain_points pp
            JOIN posts p ON pp.post_id = p.id
            ORDER BY pp.id DESC
            LIMIT ?
        """, (limit,)).fetchall()
        items.extend(dict(r) for r in rows)

        rows = self.conn.execute("""
            SELECT 'youtube' AS platform, ypp.video_id AS item_id, ypp.category,
                   ypp.severity, yv.lang, yv.title, yv.url, ypp.excerpt,
                   ypp.matched_keywords, ypp.created_at
            FROM youtube_pain_points ypp
            JOIN youtube_videos yv ON ypp.video_id = yv.id
            ORDER BY ypp.id DESC
            LIMIT ?
        """, (limit,)).fetchall()
        items.extend(dict(r) for r in rows)

        rows = self.conn.execute("""
            SELECT 'quora' AS platform, qpp.post_id AS item_id, qpp.category,
                   qpp.severity, qp.lang, qp.title, qp.url, qpp.excerpt,
                   qpp.matched_keywords, qpp.created_at
            FROM quora_pain_points qpp
            JOIN quora_posts qp ON qpp.post_id = qp.id
            ORDER BY qpp.id DESC
            LIMIT ?
        """, (limit,)).fetchall()
        items.extend(dict(r) for r in rows)

        return sorted(items, key=lambda x: x.get("created_at") or "", reverse=True)[:limit]

    def get_knowledge_topics(self) -> list:
        rows = self.conn.execute("""
            SELECT kt.*,
                   COUNT(DISTINCT ks.id) AS source_count,
                   COUNT(DISTINCT kpl.id) AS pain_link_count
            FROM knowledge_topics kt
            LEFT JOIN knowledge_sources ks ON ks.topic_slug = kt.slug
            LEFT JOIN knowledge_pain_links kpl ON kpl.topic_slug = kt.slug
            GROUP BY kt.slug
            ORDER BY kt.priority ASC, pain_link_count DESC, kt.slug ASC
        """).fetchall()
        return [dict(r) for r in rows]

    def get_knowledge_sources(self, topic_slug: str = None, limit: int = 500) -> list:
        if topic_slug:
            rows = self.conn.execute("""
                SELECT * FROM knowledge_sources
                WHERE topic_slug = ?
                ORDER BY trust_level, source_origin, authority, title
                LIMIT ?
            """, (topic_slug, limit)).fetchall()
        else:
            rows = self.conn.execute("""
                SELECT * FROM knowledge_sources
                ORDER BY topic_slug, trust_level, source_origin, authority, title
                LIMIT ?
            """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def get_knowledge_pain_links(self, topic_slug: str = None, limit: int = 100) -> list:
        if topic_slug:
            rows = self.conn.execute("""
                SELECT * FROM knowledge_pain_links
                WHERE topic_slug = ?
                ORDER BY CASE severity WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
                         id DESC
                LIMIT ?
            """, (topic_slug, limit)).fetchall()
        else:
            rows = self.conn.execute("""
                SELECT * FROM knowledge_pain_links
                ORDER BY id DESC
                LIMIT ?
            """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def get_knowledge_stats(self) -> dict:
        topics = self.conn.execute("SELECT COUNT(*) FROM knowledge_topics").fetchone()[0]
        sources = self.conn.execute("SELECT COUNT(*) FROM knowledge_sources").fetchone()[0]
        links = self.conn.execute("SELECT COUNT(*) FROM knowledge_pain_links").fetchone()[0]
        by_lang = self.conn.execute("""
            SELECT lang, COUNT(*) AS cnt
            FROM knowledge_sources
            GROUP BY lang
            ORDER BY cnt DESC
        """).fetchall()
        by_topic = self.conn.execute("""
            SELECT kt.slug, kt.name_en, COUNT(DISTINCT kpl.id) AS pain_links,
                   COUNT(DISTINCT ks.id) AS sources
            FROM knowledge_topics kt
            LEFT JOIN knowledge_pain_links kpl ON kpl.topic_slug = kt.slug
            LEFT JOIN knowledge_sources ks ON ks.topic_slug = kt.slug
            GROUP BY kt.slug
            ORDER BY pain_links DESC, kt.priority ASC
        """).fetchall()
        return {
            "topics": topics,
            "sources": sources,
            "pain_links": links,
            "sources_by_lang": [(r["lang"], r["cnt"]) for r in by_lang],
            "topics_summary": [dict(r) for r in by_topic],
        }

    def close(self):
        self.conn.close()
