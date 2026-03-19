# Cortexa Labs — Cold Email Automation Engine

> **AI-powered cold email system** built for Cortexa Labs to automate outreach to Indian VCs while maintaining world-class deliverability and human-first reply handling.

---

## What This Does

- **Imports leads** from CSV (VC list, Apollo export, etc.)
- **Scores & tiers** every lead by ICP fit (funding stage, seniority, company size)
- **Generates personalized emails** using Groq (Llama-3.3-70B) — unique opening lines, 50–80 word bodies, 3 subject variants
- **Sends gradually** across multiple Gmail inboxes with rotation, rate limits, and human send-time jitter
- **Detects replies** every 5 minutes via Gmail API
- **Notifies you instantly** via Slack + email when any VC replies
- **You personally respond** — AI never auto-replies in VC campaign mode
- **Analytics dashboard** — open rates, reply rates, domain health, priority reply inbox

---

## Quick Start

### 1. Clone & Set Up

```bash
git clone https://github.com/Nikshay1/Cold-email-Campaign
cd Cold-email-Campaign

# Copy env file and fill in your API keys
cp .env.example .env
```

### 2. Fill in `.env`

| Key | Where to get it |
|---|---|
| `GROQ_API_KEY` | [console.groq.com/keys](https://console.groq.com/keys) |
| `HUNTER_IO_API_KEY` | [hunter.io/api-keys](https://hunter.io/api-keys) |
| `SLACK_WEBHOOK_URL` | [api.slack.com/messaging/webhooks](https://api.slack.com/messaging/webhooks) |
| `GOOGLE_CLIENT_ID/SECRET` | [Google Cloud Console](https://console.cloud.google.com) → Gmail API |

> **No keys?** That's fine. The app runs in **mock mode** — Groq and Gmail calls return realistic fake data so you can test the full flow locally.

### 3. Launch

```bash
docker compose up --build
```

- API: [http://localhost:8000](http://localhost:8000)
- Dashboard: [http://localhost:3000](http://localhost:3000)
- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
---

## Onboarding Checklist

### Step 1 — Add Sending Domains
Go to **Settings → Inboxes** and add each Gmail inbox. Then authorize it via Google OAuth.

```
Each domain needs: SPF ✓  DKIM ✓  DMARC ✓
Each inbox: 14 days warmup before sending cold emails
Daily limit: 40 sends/inbox, 35% reserved for warmup
```

### Step 2 — Import Leads

Go to **Leads** → drag and drop your CSV. Required columns:
```
email, first_name
Optional: last_name, title, company_name, company_domain, funding_stage, linkedin_url
```
Or use the included sample: `backend/tests/fixtures/sample_leads.csv`

### Step 3 — Create & Launch Campaign

Go to **Campaigns** → click **New Campaign** → fill in:
- Value proposition (what Cortexa does)
- Pain point you solve
- Check **VC Campaign Mode** (ensures no AI auto-replies)
- Click **Launch** 🚀

### Step 4 — Monitor Replies

Go to **Replies** — the page auto-refreshes every 30 seconds. When a VC replies:
1. You get a Slack alert + email with the full reply + AI talking points
2. The sequence is **auto-paused** — no accidental follow-ups
3. Click **Reply in Gmail** to respond personally

---

## Project Structure

```
Cold-email-Campaign/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app factory
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   ├── config.py            # Settings from .env
│   │   ├── database.py          # Async DB engine
│   │   ├── worker.py            # arq background worker
│   │   ├── routers/
│   │   │   ├── leads.py         # Lead ingestion + CSV upload
│   │   │   ├── campaigns.py     # Campaign CRUD + launch
│   │   │   ├── analytics.py     # Metrics + reply inbox
│   │   │   ├── inboxes.py       # Inbox management
│   │   │   ├── tracking.py      # Open pixel + unsubscribe
│   │   │   └── auth.py          # Google OAuth
│   │   └── services/
│   │       ├── leads/
│   │       │   ├── scoring.py   # ICP lead scorer
│   │       │   └── enrichment.py # Hunter.io enrichment
│   │       ├── ai/
│   │       │   └── personalizer.py # Groq email generator
│   │       ├── sending/
│   │       │   ├── inbox_rotator.py
│   │       │   ├── scheduler.py     # Send-time randomizer
│   │       │   ├── gmail_sender.py  # Gmail API sender
│   │       │   └── send_worker.py   # arq send task
│   │       └── replies/
│   │           ├── gmail_poller.py  # Cron reply detector
│   │           ├── classifier.py    # Groq triage
│   │           └── notifier.py      # Slack + email alerts
│   └── tests/
│       ├── fixtures/sample_leads.csv
│       ├── test_scoring.py
│       ├── test_scheduler.py
│       └── test_classifier.py
├── frontend/
│   └── src/app/
│       ├── page.tsx             # Dashboard (funnel + domain health)
│       ├── leads/page.tsx       # CSV upload + lead table
│       ├── campaigns/page.tsx   # Campaign management
│       ├── replies/page.tsx     # Priority VC reply inbox
│       ├── inboxes/page.tsx     # Gmail OAuth connection
│       └── settings/page.tsx    # Configuration instructions
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Sending Limits (Safe Defaults)

| Inboxes | Safe Cold Emails/Day |
|---|---|
| 5 domains × 3 inboxes | ~390/day |
| 15 domains × 3 inboxes | ~1,170/day |
| 40 domains × 3 inboxes | ~3,120/day |

Rule: **Max 40 sends/inbox/day, 35% reserved for warmup** (always keep warmup running).

---

## Running Tests

```bash
cd backend
pip install -e ".[dev]"
pytest tests/ -v
```

---

## Tech Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI + SQLAlchemy + arq |
| Database | PostgreSQL 16 |
| Queue | Redis 7 + arq |
| AI | Llama 3.3 70B (Groq) |
| Email Send | Gmail API (OAuth2) |
| Enrichment | Hunter.io |
| Notifications | Slack Webhooks + SendGrid |
| Frontend | Next.js 14 + Tailwind + Tremor |
| Infra | Docker Compose |

---

*Built by Cortexa Labs — March 2026*