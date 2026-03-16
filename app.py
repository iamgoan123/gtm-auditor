import streamlit as st
import requests
import re
import json
import google.generativeai as genai

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="GTM Auditor",
    page_icon="🔍",
    layout="wide"
)

# ── Styling ───────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, sans-serif;
    -webkit-font-smoothing: antialiased;
}
.main { background: #f5f5f7; }
.block-container { padding: 2rem 2rem 4rem; max-width: 960px; }

h1 { font-size: 2.2rem !important; font-weight: 600 !important; letter-spacing: -.03em !important; color: #1d1d1f !important; }
h2 { font-size: 1.3rem !important; font-weight: 600 !important; letter-spacing: -.02em !important; color: #1d1d1f !important; }
h3 { font-size: 1rem !important; font-weight: 500 !important; color: #1d1d1f !important; }

.metric-card {
    background: #fff;
    border-radius: 16px;
    padding: 20px 24px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    text-align: center;
    margin-bottom: 8px;
}
.metric-num { font-size: 2rem; font-weight: 600; letter-spacing: -.03em; }
.metric-lbl { font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: #86868b; margin-top: 2px; font-weight: 500; }

.tag-card {
    background: #fff;
    border-radius: 14px;
    padding: 16px 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    margin-bottom: 10px;
    border-left: 4px solid #e0e0e0;
}
.tag-card.pass { border-left-color: #34c759; }
.tag-card.warn { border-left-color: #ff9f0a; }
.tag-card.fail { border-left-color: #ff3b30; }
.tag-card.info { border-left-color: #0071e3; }

.tag-name { font-size: 14px; font-weight: 500; color: #1d1d1f; letter-spacing: -.01em; }
.tag-detail { font-size: 12px; color: #6e6e73; margin-top: 4px; font-weight: 300; letter-spacing: -.01em; line-height: 1.5; }
.tag-rec { font-size: 12px; color: #ff9f0a; margin-top: 4px; font-style: italic; letter-spacing: -.01em; }

.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 980px;
    font-size: 10px;
    font-weight: 500;
    letter-spacing: .02em;
    margin-left: 8px;
}
.badge-pass { background: #f0fdf4; color: #248a3d; }
.badge-warn { background: #fff8ec; color: #b25000; }
.badge-fail { background: #fff2f2; color: #ff3b30; }
.badge-info { background: #e8f1fd; color: #0071e3; }

.site-header {
    background: #fff;
    border-radius: 18px;
    padding: 22px 28px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    margin-bottom: 20px;
}
.gtm-id {
    font-family: monospace;
    background: #f5f5f7;
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 13px;
    color: #0071e3;
    font-weight: 500;
}
.section-card {
    background: #fff;
    border-radius: 16px;
    padding: 20px 24px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    margin-bottom: 16px;
}
.stButton > button {
    background: #0071e3 !important;
    color: white !important;
    border: none !important;
    border-radius: 980px !important;
    padding: 12px 28px !important;
    font-size: 15px !important;
    font-weight: 400 !important;
    font-family: Inter, sans-serif !important;
    letter-spacing: -.01em !important;
    transition: background .2s !important;
    width: 100%;
}
.stButton > button:hover { background: #0077ed !important; }
.stTextInput > div > div > input {
    border-radius: 12px !important;
    border: 1px solid rgba(0,0,0,0.12) !important;
    padding: 12px 16px !important;
    font-size: 15px !important;
    font-family: Inter, sans-serif !important;
    font-weight: 300 !important;
}
.stTextInput > div > div > input:focus { border-color: #0071e3 !important; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────

def fetch_page(url):
    """Fetch real page HTML using Python requests (no CORS issues)."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        return r.text
    except Exception as e:
        return None


def extract_gtm_ids(html):
    """Extract all GTM container IDs from page source."""
    patterns = [
        r'GTM-[A-Z0-9]{4,12}',
        r"'GTM-([A-Z0-9]{4,12})'",
        r'"GTM-([A-Z0-9]{4,12})"',
    ]
    ids = set()
    for p in patterns:
        for m in re.finditer(p, html):
            val = m.group(0).replace("'", "").replace('"', '')
            if not val.startswith('GTM-'):
                val = 'GTM-' + val
            ids.add(val)
    return list(ids)


def fetch_gtm_script(gtm_id):
    """Fetch the GTM container script."""
    url = f"https://www.googletagmanager.com/gtm.js?id={gtm_id}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        return r.text[:20000]
    except:
        return None


def extract_page_signals(html):
    """Extract key signals from page HTML."""
    signals = {}

    # GA4 measurement IDs
    ga4_ids = re.findall(r'G-[A-Z0-9]{8,12}', html)
    signals['ga4_ids'] = list(set(ga4_ids))

    # dataLayer pushes
    dl_pushes = re.findall(r'dataLayer\.push\(\{[^}]{0,300}\}\)', html)
    signals['datalayer_pushes'] = dl_pushes[:10]

    # gtag calls
    gtag_calls = re.findall(r"gtag\([^)]{0,150}\)", html)
    signals['gtag_calls'] = list(set(gtag_calls))[:10]

    # Consent mode
    signals['consent_mode'] = bool(re.search(r'consent_mode|gtag.*consent', html, re.I))

    # Script srcs
    srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html)
    signals['script_srcs'] = list(set(srcs))[:40]

    return signals


def run_gemini_audit(gtm_script, page_signals, url, gtm_id, api_key):
    """Send GTM data to Gemini for analysis."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')

    prompt = f"""You are an expert GTM and GA4 implementation auditor. Analyze the GTM container and page signals below for {url} (Container: {gtm_id}).

GTM CONTAINER SCRIPT (first 20000 chars):
{gtm_script[:15000] if gtm_script else 'Could not fetch GTM script'}

PAGE SIGNALS:
GA4 IDs found: {page_signals.get('ga4_ids', [])}
GTM calls: {page_signals.get('gtag_calls', [])}
Consent mode detected: {page_signals.get('consent_mode', False)}
Script srcs: {page_signals.get('script_srcs', [])[:20]}
DataLayer pushes: {page_signals.get('datalayer_pushes', [])}

Return ONLY a valid JSON object, no markdown, no backticks:

{{
  "site_summary": "2 sentences about the site and their GTM setup",
  "health_score": 72,
  "tags_found": 14,
  "triggers_found": 8,
  "variables_found": 11,
  "issues_count": 3,
  "ga4": {{
    "detected": true,
    "measurement_id": "G-XXXXXX or null",
    "via": "GTM or direct",
    "ecommerce": true,
    "consent_mode": false,
    "status": "pass or warn or fail",
    "note": "specific observation about GA4 setup"
  }},
  "tags": [
    {{
      "name": "Tag name",
      "type": "GA4 / Google Ads / Facebook Pixel / Custom HTML etc",
      "status": "pass or warn or fail or info",
      "detail": "what this tag does",
      "recommendation": "specific recommendation or null"
    }}
  ],
  "triggers": [
    {{
      "name": "Trigger name",
      "type": "Page View / Click / Custom Event etc",
      "status": "pass or warn or fail or info",
      "detail": "what fires this trigger",
      "recommendation": "specific recommendation or null"
    }}
  ],
  "top_issues": [
    {{
      "title": "Issue title",
      "priority": "high or medium or low",
      "detail": "specific explanation",
      "fix": "how to fix this"
    }}
  ],
  "quick_wins": ["Quick win 1", "Quick win 2", "Quick win 3"]
}}"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except Exception as e:
        st.error(f"AI analysis failed: {str(e)}")
        return None


# ── UI ────────────────────────────────────────────────────────

def render_badge(status):
    colors = {
        'pass': ('badge-pass', 'Pass'),
        'warn': ('badge-warn', 'Warning'),
        'fail': ('badge-fail', 'Issue'),
        'info': ('badge-info', 'Info')
    }
    cls, label = colors.get(status, ('badge-info', status.title()))
    return f'<span class="badge {cls}">{label}</span>'


def render_priority_badge(priority):
    colors = {'high': 'badge-fail', 'medium': 'badge-warn', 'low': 'badge-pass'}
    cls = colors.get(priority, 'badge-info')
    return f'<span class="badge {cls}">{priority.title()}</span>'


def main():
    # ── Header ──
    st.markdown("""
    <div style="text-align:center;padding:40px 0 20px">
        <div style="display:inline-flex;align-items:center;gap:8px;background:#fff;border-radius:980px;padding:7px 18px;box-shadow:0 2px 12px rgba(0,0,0,0.07);font-size:12px;font-weight:500;color:#6e6e73;margin-bottom:24px">
            <div style="width:7px;height:7px;background:#0071e3;border-radius:50%"></div>
            GTM Auditor
        </div>
        <h1 style="font-size:2.8rem;font-weight:600;letter-spacing:-.03em;color:#1d1d1f;margin-bottom:10px">
            Audit any website's <span style="color:#0071e3">GTM setup</span>
        </h1>
        <p style="font-size:17px;color:#6e6e73;font-weight:300;letter-spacing:-.01em">
            Paste a URL and get a full Google Tag Manager audit in seconds
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── API Key ──
    with st.sidebar:
        st.markdown("### Settings")
        api_key = st.text_input(
            "Google Gemini API Key",
            type="password",
            placeholder="AIza...",
            help="Get your free key at aistudio.google.com"
        )
        st.markdown("""
        <div style="font-size:11px;color:#86868b;margin-top:4px">
            Get a free key at <a href="https://aistudio.google.com" target="_blank" style="color:#0071e3">aistudio.google.com</a>
        </div>
        """, unsafe_allow_html=True)
        st.divider()
        st.markdown("""
        <div style="font-size:12px;color:#86868b;line-height:1.7;font-weight:300">
            <strong style="color:#1d1d1f;font-weight:500">What this audits:</strong><br>
            GTM tags, triggers and variables<br>
            GA4 implementation quality<br>
            Missing or broken configurations<br>
            Consent mode setup<br>
            Ecommerce tracking
        </div>
        """, unsafe_allow_html=True)

    # ── URL Input ──
    col1, col2 = st.columns([4, 1])
    with col1:
        url = st.text_input("", placeholder="https://yourwebsite.com", label_visibility="collapsed")
    with col2:
        analyze = st.button("Audit GTM →")

    if not api_key:
        st.markdown("""
        <div style="background:#fff8ec;border-radius:12px;padding:14px 18px;font-size:13px;color:#b25000;font-weight:300;letter-spacing:-.01em;margin-top:8px">
            Add your Gemini API key in the sidebar to get started. It is free at aistudio.google.com
        </div>
        """, unsafe_allow_html=True)
        return

    if analyze and url:
        if not url.startswith('http'):
            url = 'https://' + url

        # ── Fetch & Analyze ──
        with st.spinner("Fetching page source..."):
            html = fetch_page(url)

        if not html:
            st.error("Could not fetch the page. Please check the URL and try again.")
            return

        with st.spinner("Detecting GTM container..."):
            gtm_ids = extract_gtm_ids(html)
            signals = extract_page_signals(html)

        if not gtm_ids:
            st.markdown("""
            <div style="background:#fff2f2;border-radius:14px;padding:20px 24px;text-align:center">
                <div style="font-size:24px;margin-bottom:8px">⚠️</div>
                <div style="font-size:16px;font-weight:500;color:#1d1d1f;margin-bottom:4px">No GTM container found</div>
                <div style="font-size:13px;color:#6e6e73;font-weight:300">This site does not appear to have Google Tag Manager installed.</div>
            </div>
            """, unsafe_allow_html=True)
            return

        gtm_id = gtm_ids[0]

        with st.spinner(f"Fetching GTM container {gtm_id}..."):
            gtm_script = fetch_gtm_script(gtm_id)

        with st.spinner("Running AI audit..."):
            audit = run_gemini_audit(gtm_script, signals, url, gtm_id, api_key)

        if not audit:
            st.error("Audit failed. Please try again.")
            return

        # ── Site Header ──
        domain = url.replace('https://', '').replace('http://', '').split('/')[0]
        st.markdown(f"""
        <div class="site-header">
            <div style="display:flex;align-items:center;gap:16px">
                <div style="width:48px;height:48px;background:#f0f6ff;border-radius:12px;display:flex;align-items:center;justify-content:center;font-weight:600;font-size:16px;color:#0071e3;flex-shrink:0">
                    {domain[:2].upper()}
                </div>
                <div style="flex:1">
                    <div style="font-size:18px;font-weight:600;letter-spacing:-.02em;color:#1d1d1f">{domain}</div>
                    <div style="font-size:13px;color:#86868b;margin-top:2px;font-weight:300">{audit.get('site_summary','')}</div>
                </div>
                <div style="text-align:center;flex-shrink:0">
                    <div style="font-size:11px;color:#86868b;font-weight:500;text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px">Container</div>
                    <span class="gtm-id">{gtm_id}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Score + Summary Metrics ──
        score = audit.get('health_score', 0)
        score_color = '#34c759' if score >= 70 else '#ff9f0a' if score >= 50 else '#ff3b30'
        score_bg = '#f0fdf4' if score >= 70 else '#fff8ec' if score >= 50 else '#fff2f2'

        c1, c2, c3, c4, c5 = st.columns(5)
        metrics = [
            (c1, str(score), "Health Score", score_color),
            (c2, str(audit.get('tags_found', 0)), "Tags Found", "#0071e3"),
            (c3, str(audit.get('triggers_found', 0)), "Triggers", "#0071e3"),
            (c4, str(audit.get('variables_found', 0)), "Variables", "#0071e3"),
            (c5, str(audit.get('issues_count', 0)), "Issues", "#ff3b30"),
        ]
        for col, num, lbl, color in metrics:
            with col:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-num" style="color:{color}">{num}</div>
                    <div class="metric-lbl">{lbl}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── GA4 Status ──
        ga4 = audit.get('ga4', {})
        ga4_status = ga4.get('status', 'info')
        ga4_colors = {'pass': '#34c759', 'warn': '#ff9f0a', 'fail': '#ff3b30', 'info': '#0071e3'}
        ga4_bgs = {'pass': '#f0fdf4', 'warn': '#fff8ec', 'fail': '#fff2f2', 'info': '#e8f1fd'}

        st.markdown(f"""
        <div style="background:#0071e3;border-radius:16px;padding:20px 24px;margin-bottom:16px;display:flex;align-items:center;gap:16px">
            <div style="background:rgba(255,255,255,.2);width:40px;height:40px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;color:#fff;flex-shrink:0">G4</div>
            <div style="flex:1">
                <div style="font-size:15px;font-weight:600;color:#fff;letter-spacing:-.01em">Google Analytics 4</div>
                <div style="font-size:12px;color:rgba(255,255,255,.75);margin-top:2px;font-weight:300">{ga4.get('note','')}</div>
            </div>
            <div style="display:flex;gap:20px;text-align:center">
                <div><div style="font-size:11px;color:rgba(255,255,255,.6);text-transform:uppercase;letter-spacing:.05em">ID</div><div style="font-size:13px;font-weight:500;color:#fff;margin-top:2px">{ga4.get('measurement_id') or 'Not found'}</div></div>
                <div><div style="font-size:11px;color:rgba(255,255,255,.6);text-transform:uppercase;letter-spacing:.05em">Via</div><div style="font-size:13px;font-weight:500;color:#fff;margin-top:2px">{ga4.get('via','Unknown')}</div></div>
                <div><div style="font-size:11px;color:rgba(255,255,255,.6);text-transform:uppercase;letter-spacing:.05em">Ecommerce</div><div style="font-size:13px;font-weight:500;color:#fff;margin-top:2px">{'Active' if ga4.get('ecommerce') else 'Not found'}</div></div>
                <div><div style="font-size:11px;color:rgba(255,255,255,.6);text-transform:uppercase;letter-spacing:.05em">Consent</div><div style="font-size:13px;font-weight:500;color:#fff;margin-top:2px">{'On' if ga4.get('consent_mode') else 'Off'}</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Tags + Triggers ──
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("### Tags")
            tags = audit.get('tags', [])
            if tags:
                for tag in tags:
                    rec_html = f'<div class="tag-rec">→ {tag["recommendation"]}</div>' if tag.get('recommendation') else ''
                    st.markdown(f"""
                    <div class="tag-card {tag.get('status','info')}">
                        <div style="display:flex;align-items:center">
                            <span class="tag-name">{tag['name']}</span>
                            {render_badge(tag.get('status','info'))}
                        </div>
                        <div class="tag-detail">{tag.get('detail','')}</div>
                        {rec_html}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown('<div class="tag-card info"><div class="tag-detail">No tags detected</div></div>', unsafe_allow_html=True)

        with col_right:
            st.markdown("### Triggers")
            triggers = audit.get('triggers', [])
            if triggers:
                for t in triggers:
                    rec_html = f'<div class="tag-rec">→ {t["recommendation"]}</div>' if t.get('recommendation') else ''
                    st.markdown(f"""
                    <div class="tag-card {t.get('status','info')}">
                        <div style="display:flex;align-items:center">
                            <span class="tag-name">{t['name']}</span>
                            {render_badge(t.get('status','info'))}
                        </div>
                        <div class="tag-detail">{t.get('detail','')}</div>
                        {rec_html}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown('<div class="tag-card info"><div class="tag-detail">No triggers detected</div></div>', unsafe_allow_html=True)

        # ── Top Issues ──
        issues = audit.get('top_issues', [])
        if issues:
            st.markdown("### Top issues to fix")
            for issue in issues:
                st.markdown(f"""
                <div class="tag-card {'fail' if issue.get('priority')=='high' else 'warn' if issue.get('priority')=='medium' else 'info'}">
                    <div style="display:flex;align-items:center">
                        <span class="tag-name">{issue['title']}</span>
                        {render_priority_badge(issue.get('priority','medium'))}
                    </div>
                    <div class="tag-detail">{issue.get('detail','')}</div>
                    <div class="tag-rec">→ {issue.get('fix','')}</div>
                </div>
                """, unsafe_allow_html=True)

        # ── Quick Wins ──
        wins = audit.get('quick_wins', [])
        if wins:
            st.markdown("### Quick wins")
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            for win in wins:
                st.markdown(f"""
                <div style="display:flex;gap:10px;padding:6px 0;border-bottom:1px solid rgba(0,0,0,0.05);font-size:13px;color:#3d3d3f;font-weight:300;letter-spacing:-.01em">
                    <span style="color:#34c759;flex-shrink:0">✓</span> {win}
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # ── Footer ──
        st.markdown(f"""
        <div style="text-align:center;padding:32px 0 8px;font-size:11px;color:#b0b0b5;letter-spacing:-.01em">
            GTM Auditor — {domain} — Powered by Google Gemini
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
