# GTM Auditor

Paste any website URL and get a full Google Tag Manager audit in seconds — no GTM access required.

## What it does

- Detects the GTM container ID from the page source
- Pulls the public `gtm.js` script directly from Google's CDN
- Parses every tag, variable, trigger condition, and rule out of the container
- Detects 20+ other tracking tools (Meta Pixel, TikTok, Pinterest, LinkedIn, Hotjar, Clarity, OneTrust, Cookiebot, Shopify, etc.)
- Runs an AI audit (Llama 3.3 70B via Groq) flagging issues against current best practices:
  - Universal Analytics deprecation (sunset July 2023)
  - Consent Mode v2 compliance (required for EEA traffic since March 2024)
  - Missing conversion linkers
  - Duplicate tracking risk (e.g. Shopify native + GTM GA4)
  - GA4 event naming compliance
- Returns a health score, structured tag/trigger breakdown, top issues with fixes, and quick wins

## How it works

Google serves every container's `gtm.js` publicly — browsers need it to fire tags. We just fetch it directly, parse the embedded JSON config, and let the AI cross-reference it against best practices.

No headless browser, no GTM API access, no auth.

## Setup (local)

```bash
git clone https://github.com/iamgoan123/gtm-auditor.git
cd gtm-auditor
pip install -r requirements.txt
streamlit run app.py
```

Grab a free Groq API key at [console.groq.com](https://console.groq.com) and paste it in the sidebar.

## Deploy to Streamlit Community Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your GitHub
3. Pick this repo, set the main file to `app.py`
4. In **Advanced settings → Secrets**, add:
   ```toml
   GROQ_API_KEY = "gsk_your_key_here"
   ```
5. Deploy. The API key will load automatically from secrets so users don't have to enter it.

## Limitations

- **Single Page Apps**: if GTM loads via JS after initial render, the HTML fetch may miss the container ID.
- **Server-side GTM**: detects signals but cannot inspect the server container itself.
- **Custom HTML tag contents**: we see that a Custom HTML tag exists but not what it executes at runtime.
- **Triggers**: GTM's UI assembles triggers from rules + predicates. The audit shows trigger conditions, not the friendly UI names.

## Stack

- Streamlit (UI + hosting)
- Requests (HTTP)
- Groq + Llama 3.3 70B (AI audit)

## Files

- `app.py` — main application
- `requirements.txt` — dependencies
