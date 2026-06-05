# SeguroTools Static Site

Cloudflare Pages-ready bilingual insurance education site for `segurotools.com`.

Chinese deployment and SEO checklist: `DEPLOYMENT_SEO_CN.md`.

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
- Pages project name: `segurotools`

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
FROM_EMAIL=reports@segurotools.com
REPLY_TO_EMAIL=support@segurotools.com
OWNER_EMAIL=segruotools@gmail.com
RESEND_API_KEY=...
```

The form requires explicit consent before sending a report or forwarding the lead notification to the owner email.

## Inbound Email Forwarding

The inbound Resend webhook endpoint is:

```text
POST /api/inbound-email
```

Configure Resend Receiving for `segurotools.com`, then add this production webhook URL:

```text
https://segurotools.com/api/inbound-email
```

Select the `email.received` event. All role inboxes shown on the Contact page use the `@segurotools.com` domain and are forwarded to:

```text
segruotools@gmail.com
```

Cloudflare Pages variables:

```text
FORWARD_EMAIL=segruotools@gmail.com
INBOUND_FROM_EMAIL=forwarder@segurotools.com
INBOUND_DOMAIN=segurotools.com
```

Cloudflare Pages secrets:

```text
RESEND_API_KEY=...
RESEND_WEBHOOK_SECRET=...
```

The forwarder verifies Resend's Svix webhook signature before forwarding. It forwards the message body and attachment names; attachments remain available in Resend Receiving and are not re-attached by this lightweight Worker.

Visible role inboxes:

```text
hello@segurotools.com
hola@segurotools.com
support@segurotools.com
calculators@segurotools.com
editorial@segurotools.com
corrections@segurotools.com
sources@segurotools.com
research@segurotools.com
privacy@segurotools.com
legal@segurotools.com
ads@segurotools.com
partners@segurotools.com
```

## Deployment

Direct upload with Wrangler:

```bash
cd /root/insurance/site
python3 build.py
npx wrangler pages deploy dist --project-name segurotools
```

After the first deployment, add `segurotools.com` under Cloudflare Pages > `segurotools` > Custom domains. Keep the domain in the same Cloudflare account as the Pages project.

## Content Model

`build.py` reads:

```text
data/knowledge_items.jsonl
```

For local research refreshes, replace `site/data/knowledge_items.jsonl` with the latest crawler export from `../reddit_crawler/reports/knowledge_base/knowledge_items.jsonl`, then rebuild and commit.

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
