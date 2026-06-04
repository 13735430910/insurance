# CoverWise Tools Static Site

Cloudflare Pages-ready bilingual insurance education site.

## Build

```bash
cd /root/insurance
python3 site/build.py
```

Output:

```text
site/dist
```

Cloudflare Pages settings:

- Build command: `python3 build.py`
- Build output directory: `dist`
- Project root: `site`
- Functions directory: `functions`

## Email Reports

The calculator report endpoint is:

```text
POST /api/send-report
```

Configure one email provider in Cloudflare:

- Preferred: bind Cloudflare Email Sending as `EMAIL`
- Fallback: set `RESEND_API_KEY`

Required/optional variables:

```text
FROM_EMAIL=reports@yourdomain.com
OWNER_EMAIL=rockxh2036@gmail.com
RESEND_API_KEY=...
```

The form requires explicit consent before sending a report or forwarding the lead notification to the owner email.

## Content Model

`build.py` reads:

```text
../reddit_crawler/reports/knowledge_base/knowledge_items.jsonl
```

The generated site includes:

- `/en/` and `/es/` language roots
- 8 calculator pages per language
- 14 topic guide articles per language
- 8 calculator support articles per language
- category pages, knowledge-source pages, legal pages, sitemap, robots, redirects, and headers

## AdSense

Ad slots are reserved with `.ad-slot` but hidden by default. After AdSense approval, add the publisher script and enable slots by adding `ads-ready` to the body or adjusting the template.

Before applying, manually review:

- About, Contact, Privacy, Disclaimer, Terms, Author pages
- every generated article for accuracy and Spanish localization quality
- source links and state-specific caveats
- calculator disclaimers and email consent language

## Extending State-Specific Knowledge

Add a new knowledge-base layer with fields such as:

```text
state
topic_slug
source_url
effective_date
policy_note
rate_context
page_section
```

Then extend `site/build.py` to render state pages and link them from the relevant topic and calculator pages.
