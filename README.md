# Cortexa Labs — Cold Email Automation Engine

> **AI-powered cold email system** built for Cortexa Labs to automate outreach to VCs and prospects while maintaining world-class deliverability and human-first reply handling.

---

## What This Does

- **Imports leads** from CSV files
- **Sends gradually** across multiple Gmail inboxes with rotation, rate limits, and human send-time jitter. Includes 35% reserved limit for inbox warmup.
- **Generates personalized emails** using Groq (Llama-3.3-70B/Mixtral) — unique opening lines based on LinkedIn/Company data, 50–80 word bodies, and 3 subject variants.
- **Detects replies** automatically via the Gmail API.
- **Analytics dashboard** to track open rates, reply rates, domain health, and priority reply inbox management.
- **Dynamic Configuration** — manage AI models and API keys directly from the UI dashboard.

---

## Quick Start & Setup Guide

### 1. Clone & Setup Environment

```bash
git clone https://github.com/Nikshay1/Cold-email-Campaign
cd Cold-email-Campaign

# Copy the environment file
cp .env.example .env
```

### 2. Configure Google Cloud OAuth (Required for Gmail)
To send emails from your authentic Gmail accounts, you must configure a Google Cloud Project:
1. Go to the [Google Cloud Console](https://console.cloud.google.com).
2. Create a new project and enable the **Gmail API**.
3. Go to **APIs & Services > OAuth consent screen** and set up an External app (add your own email as a Test User if your app is unpublished).
4. Go to **Credentials**, click **Create Credentials**, and select **OAuth client ID** (Web application).
5. Add the following to **Authorized redirect URIs**:
   ```
   http://localhost:8000/auth/google/callback
   ```
6. Copy your **Client ID** and **Client Secret**, and paste them into your `.env` file:
   ```env
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```

*(Optional)* Fill in your Slack Webhook URL and SendGrid keys in `.env` if you want external notifications.

### 3. Launch the Application

Make sure Docker Desktop is running, then boot everything up:

```bash
docker compose up --build -d
```

Your services are now running:
- **Dashboard (Next.js)**: [http://localhost:3000](http://localhost:3000)
- **Backend API (FastAPI)**: [http://localhost:8000](http://localhost:8000)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## How to Use the System

### Step 1: Configure AI (Groq API)
1. Navigate to **[Settings](http://localhost:3000/settings)** in the Dashboard.
2. Get a free API key from [console.groq.com/keys](https://console.groq.com/keys).
3. Paste the key into the UI and select your preferred AI model (e.g., `llama-3.3-70b-versatile`). Click **Save Settings**. This is saved securely to your local database.

### Step 2: Connect Sending Inboxes
1. Go to **[Inboxes](http://localhost:3000/inboxes)**.
2. Enter the Email Address you want to send from (e.g., `nikshay@cortexalabs.io` or a personal `@gmail.com` account for testing), a Sender Name, and the Domain.
3. Click **Continue to Google OAuth**. You will be redirected to Google to grant permissions. Once approved, the inbox will show a green `GOOD` health status.

### Step 3: Import Leads
1. Go to **[Leads](http://localhost:3000/leads)** -> Click Upload CSV.
2. Upload a CSV file. The file must have at minimum an `email` and `first_name` column.
   *Optional high-value AI personalization columns: `title`, `company_name`, `company_recent_news`, `linkedin_recent_post`*.
   *(A sample CSV is available in `backend/tests/fixtures/sample_leads.csv`)*

### Step 4: Launch a Campaign
1. Go to **[Campaigns](http://localhost:3000/campaigns)** -> Click **New Campaign**.
2. Write out your **Value Proposition** and the **Pain Point** you are solving.
3. Use the **Custom AI Instructions** (optional) to give the AI specific behaviors or rules for this campaign (e.g. "Mention we recently raised a Seed Round").
4. The AI engine will automatically combine your proposition with the lead data to write hyper-personalized outreach.
5. Click **Launch**! The backend scheduler will distribute the emails safely across your connected inboxes.

### Step 5: Monitor Replies
1. The backend automatically polls connected Gmail inboxes for replies every few minutes.
2. Go to **[Replies](http://localhost:3000/replies)** to see a prioritized list of responses. 
3. Cortexa's AI automatically categorizes them (e.g., "Interested", "Wrong Person", "Not Now") so you know who to respond to first.

---

## Architecture & Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 14, React, Tailwind CSS |
| **Backend API** | Python, FastAPI, SQLAlchemy |
| **Database** | PostgreSQL 16 |
| **Task Queue** | Redis 7, python-arq |
| **AI Inference** | Groq API (Llama 3, Mixtral) |
| **Integrations** | Gmail API (OAuth2) |
| **Infrastructure**| Docker Compose |

---
*Built by Cortexa Labs*