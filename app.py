import streamlit as st
import requests
import re
import json
from groq import Groq

st.set_page_config(
    page_title="GTM Auditor",
    page_icon="🔍",
    layout="wide"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

html, body, [class*="css"], .stApp, .stApp > div, div[data-testid="stAppViewContainer"], div[data-testid="stAppViewBlockContainer"], div[data-testid="block-container"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    -webkit-font-smoothing: antialiased;
    color: #1d1d1f !important;
    background-color: #f5f5f7 !important;
}
.main, .stApp { background-color: #f5f5f7 !important; }
div[data-testid="stAppViewContainer"] { background-color: #f5f5f7 !important; }
div[data-testid="stVerticalBlock"] { background-color: #f5f5f7 !important; }
.block-container { padding: 2rem 2rem 4rem; max-width: 980px; background: #f5f5f7 !important; }
section[data-testid="stSidebar"] { background: #fff !important; border-right: 1px solid rgba(0,0,0,0.06); }
section[data-testid="stSidebar"] * { color: #1d1d1f !important; }

h1,h2,h3,p,label,div { color: #1d1d1f; }
h1 { font-size: 2.2rem !important; font-weight: 600 !important; letter-spacing: -.03em !important; }
h2 { font-size: 1.3rem !important; font-weight: 600 !important; letter-spacing: -.02em !important; }
h3 { font-size: 1rem !important; font-weight: 500 !important; }

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
.tag-detail { font-size: 12px; color: #6e6e73; margin-top: 4px; font-weight: 300; line-height: 1.5; }
.tag-rec { font-size: 12px; color: #ff9f0a; margin-top: 4px; font-style: italic; }

.badge { display: inline-block; padding: 3px 10px; border-radius: 980px; font-size: 10px; font-weight: 500; letter-spacing: .02em; margin-left: 8px; }
.badge-pass { background: #f0fdf4; color: #248a3d; }
.badge-warn { background: #fff8ec; color: #b25000; }
.badge-fail { background: #fff2f2; color: #ff3b30; }
.badge-info { background: #e8f1fd; color: #0071e3; }

.site-header { background: #fff; border-radius: 18px; padding: 22px 28px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); margin-bottom: 20px; }
.gtm-id { font-family: monospace; background: #f5f5f7; padding: 3px 8px; border-radius: 6px; font-size: 13px; color: #0071e3; font-weight: 500; }
.section-card { background: #fff; border-radius: 16px; padding: 20px 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 16px; }

.info-card { background: #fff; border-radius: 18px; padding: 28px 32px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); margin-bottom: 16px; }
.info-card h3 { font-size: 17px !important; font-weight: 600 !important; color: #1d1d1f !important; margin-bottom: 8px; letter-spacing: -.02em; }
.info-card p { font-size: 14px; color: #6e6e73; font-weight: 300; line-height: 1.7; margin: 0; }
.feature-row { display: flex; gap: 12px; margin-top: 20px; flex-wrap: wrap; }
.feature-pill { background: #f5f5f7; border-radius: 980px; padding: 8px 16px; font-size: 13px; color: #1d1d1f; font-weight: 400; display: flex; align-items: center; gap: 6px; }
.feature-pill span { color: #0071e3; font-size: 14px; }

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
    background: #fff !important;
    color: #1d1d1f !important;
}
.stTextInput > div > div > input:focus { border-color: #0071e3 !important; box-shadow: none !important; }
.stTextInput label { color: #1d1d1f !important; }
.stMarkdown p { color: #1d1d1f; }
div[data-testid="stSpinner"] { color: #0071e3 !important; }
</style>
""", unsafe_allow_html=True)


def fetch_page(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        return r.text
    except:
        return None

def extract_gtm_ids(html):
    patterns = [r'GTM-[A-Z0-9]{4,12}', r"'GTM-([A-Z0-9]{4,12})'", r'"GTM-([A-Z0-9]{4,12})"']
    ids = set()
    for p in patterns:
        for m in re.finditer(p, html):
            val = m.group(0).replace("'", "").replace('"', '')
            if not val.startswith('GTM-'):
                val = 'GTM-' + val
            ids.add(val)
    return list(ids)

def fetch_gtm_script(gtm_id):
    url = f"https://www.googletagmanager.com/gtm.js?id={gtm_id}"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        return r.text
    except:
        return None

def parse_gtm_container(script):
    """Extract real tags, triggers and variables from GTM container JSON blob."""
    if not script:
        return None
    try:
        # GTM embeds container data as a JSON object inside the script
        match = re.search(r'var data\s*=\s*(\{.*?"resource".*?\})\s*;?\s*\n', script, re.DOTALL)
        if not match:
            match = re.search(r'"resource"\s*:\s*(\{.*?\})\s*,\s*"', script, re.DOTALL)
        if not match:
            # Try broader pattern
            match = re.search(r'(\{"resource":\{"version":.*?"rules":\[.*?\]\}\})', script, re.DOTALL)
        if not match:
            return None

        raw = match.group(1)
        # Sometimes it's wrapped in data = {...}
        if raw.startswith('{') and '"resource"' in raw:
            data = json.loads(raw)
            resource = data.get('resource', data)
        else:
            resource = json.loads(raw)

        tags = []
        for t in resource.get('tags', []):
            tags.append({
                'name': t.get('function', 'Unknown'),
                'display_name': t.get('function', '').replace('__', '').replace('_', ' ').title(),
                'instance_name': t.get('instance_name', ''),
                'paused': t.get('paused', False),
                'once_per_event': t.get('once_per_event', False),
                'once_per_load': t.get('once_per_load', False),
                'params': {p.get('key',''):p.get('value','') for p in t.get('vtp', []) if isinstance(p, dict)}
            })

        triggers = []
        for p in resource.get('predicates', []):
            triggers.append({
                'type': p.get('function', 'Unknown'),
                'arg0': p.get('arg0', ''),
                'arg1': p.get('arg1', ''),
            })

        variables = []
        for v in resource.get('macros', []):
            variables.append({
                'name': v.get('function', 'Unknown'),
                'instance_name': v.get('instance_name', ''),
                'params': {p.get('key',''):p.get('value','') for p in v.get('vtp', []) if isinstance(p, dict)}
            })

        return {
            'tags': tags,
            'triggers': triggers,
            'variables': variables,
            'version': resource.get('version', 'unknown'),
            'container_id': resource.get('container_id', '')
        }
    except Exception as e:
        return None

def extract_page_signals(html):
    signals = {}
    ga4_ids = re.findall(r'G-[A-Z0-9]{8,12}', html)
    signals['ga4_ids'] = list(set(ga4_ids))
    dl_pushes = re.findall(r'dataLayer\.push\(\{[^}]{0,300}\}\)', html)
    signals['datalayer_pushes'] = dl_pushes[:10]
    gtag_calls = re.findall(r"gtag\([^)]{0,150}\)", html)
    signals['gtag_calls'] = list(set(gtag_calls))[:10]
    signals['consent_mode'] = bool(re.search(r'consent_mode|gtag.*consent', html, re.I))
    srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html)
    signals['script_srcs'] = list(set(srcs))[:40]
    shopify = bool(re.search(r'cdn\.shopify\.com|Shopify\.theme|shopify_pay', html, re.I))
    signals['shopify_detected'] = shopify
    ga_direct = bool(re.search(r'gtag\(.*G-[A-Z0-9]{8,12}', html))
    signals['ga_direct'] = ga_direct
    signals['has_pixel'] = bool(re.search(r'connect\.facebook\.net|fbq\(', html))
    signals['has_klaviyo'] = bool(re.search(r'klaviyo', html, re.I))
    return signals

def detect_tracking_method(html, signals):
    methods = []
    if signals.get('shopify_detected'):
        methods.append('Shopify native analytics')
    if signals.get('ga_direct'):
        methods.append('Direct GA4 (gtag.js)')
    if signals.get('has_pixel'):
        methods.append('Facebook Pixel')
    if signals.get('has_klaviyo'):
        methods.append('Klaviyo tracking')
    return methods

def run_groq_audit(gtm_script, page_signals, url, gtm_id, api_key, parsed_container=None):
    client = Groq(api_key=api_key)
    prompt = f"""You are an expert GTM and GA4 implementation auditor. Analyze the GTM container and page signals below for {url} (Container: {gtm_id}).

{real_data_section}

PAGE SIGNALS:
GA4 IDs found: {page_signals.get('ga4_ids', [])}
GTM calls: {page_signals.get('gtag_calls', [])}
Consent mode detected: {page_signals.get('consent_mode', False)}
Script srcs: {page_signals.get('script_srcs', [])[:20]}

GTM SCRIPT SNIPPET:
{gtm_script[:8000] if gtm_script else 'Could not fetch'}

IMPORTANT: Use the REAL tag and variable names from the parsed container data above. Do not make up names.

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
    {{"name": "Tag name", "type": "GA4 / Google Ads / Facebook Pixel / Custom HTML etc", "status": "pass or warn or fail or info", "detail": "what this tag does", "recommendation": "specific recommendation or null"}}
  ],
  "triggers": [
    {{"name": "Trigger name", "type": "Page View / Click / Custom Event etc", "status": "pass or warn or fail or info", "detail": "what fires this trigger", "recommendation": "specific recommendation or null"}}
  ],
  "top_issues": [
    {{"title": "Issue title", "priority": "high or medium or low", "detail": "specific explanation", "fix": "how to fix this"}}
  ],
  "quick_wins": ["Quick win 1", "Quick win 2", "Quick win 3"]
}}"""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.choices[0].message.content.strip()
        text = text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except Exception as e:
        st.error(f"AI analysis failed: {str(e)}")
        return None

def render_badge(status):
    colors = {'pass': ('badge-pass', 'Pass'), 'warn': ('badge-warn', 'Warning'), 'fail': ('badge-fail', 'Issue'), 'info': ('badge-info', 'Info')}
    cls, label = colors.get(status, ('badge-info', status.title()))
    return f'<span class="badge {cls}">{label}</span>'

def render_priority_badge(priority):
    colors = {'high': 'badge-fail', 'medium': 'badge-warn', 'low': 'badge-pass'}
    return f'<span class="badge {colors.get(priority, "badge-info")}">{priority.title()}</span>'


def main():
    # ── Sidebar ──
    with st.sidebar:
        st.markdown("""
        <div style="padding:8px 0 16px">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:20px">
                <div style="width:7px;height:7px;background:#0071e3;border-radius:50%"></div>
                <span style="font-size:13px;font-weight:600;color:#1d1d1f;letter-spacing:-.01em">GTM Auditor</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        saved_key = st.secrets.get("GROQ_API_KEY", "") if hasattr(st, "secrets") else ""
        api_key = saved_key or st.text_input("Groq API Key", type="password", placeholder="gsk_...", help="Free at console.groq.com")
        if saved_key:
            st.markdown('<div style="font-size:11px;color:#34c759;margin-top:2px">✓ API key loaded from secrets</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size:11px;color:#86868b;margin-top:2px">Free key at <a href="https://console.groq.com" target="_blank" style="color:#0071e3">console.groq.com</a></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#f5f5f7;border-radius:12px;padding:14px 16px">
            <div style="font-size:11px;font-weight:600;color:#1d1d1f;text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px">What this audits</div>
            <div style="font-size:12px;color:#6e6e73;line-height:1.9;font-weight:300">
                GTM tags, triggers and variables<br>
                GA4 implementation quality<br>
                Missing or broken configurations<br>
                Consent mode setup<br>
                Ecommerce tracking<br>
                Quick wins and recommendations
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Hero ──
    st.markdown("""
    <div style="text-align:center;padding:48px 0 32px">
        <div style="display:inline-flex;align-items:center;gap:8px;background:#fff;border-radius:980px;padding:7px 18px;box-shadow:0 2px 12px rgba(0,0,0,0.07);font-size:12px;font-weight:500;color:#6e6e73;margin-bottom:28px;letter-spacing:.01em">
            <div style="width:7px;height:7px;background:#0071e3;border-radius:50%"></div>
            GTM Auditor
        </div>
        <div style="font-size:3rem;font-weight:600;letter-spacing:-.04em;color:#1d1d1f;line-height:1.1;margin-bottom:14px">
            Audit any website's<br><span style="color:#0071e3">GTM setup instantly</span>
        </div>
        <div style="font-size:17px;color:#6e6e73;font-weight:300;letter-spacing:-.01em;max-width:520px;margin:0 auto;line-height:1.6">
            Paste any website URL and get a full Google Tag Manager audit in seconds. No GTM access needed.
        </div>
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
        <div style="background:#fff8ec;border-radius:12px;padding:14px 18px;font-size:13px;color:#b25000;font-weight:300;margin-top:8px">
            Add your free Groq API key in the sidebar to get started. Get one at <a href="https://console.groq.com" target="_blank" style="color:#0071e3">console.groq.com</a>
        </div>
        """, unsafe_allow_html=True)
        return

    if analyze and url:
        if not url.startswith('http'):
            url = 'https://' + url

        with st.spinner("Fetching page source..."):
            html = fetch_page(url)

        if not html:
            st.error("Could not fetch the page. Please check the URL and try again.")
            return

        with st.spinner("Detecting GTM container..."):
            gtm_ids = extract_gtm_ids(html)
            signals = extract_page_signals(html)

        if not gtm_ids:
            other_methods = detect_tracking_method(html, signals)
            st.markdown(f"""
            <div style="background:#fff;border-radius:18px;padding:32px;box-shadow:0 2px 12px rgba(0,0,0,0.06);text-align:center;margin-top:8px">
                <div style="font-size:36px;margin-bottom:14px">🔎</div>
                <div style="font-size:20px;font-weight:600;color:#1d1d1f;margin-bottom:8px;letter-spacing:-.02em">No GTM container found</div>
                <div style="font-size:14px;color:#6e6e73;font-weight:300;max-width:480px;margin:0 auto;line-height:1.7">
                    This website does not appear to be using Google Tag Manager. This is actually common — many sites manage their tracking differently.
                </div>
                {"<div style='margin-top:20px;display:flex;gap:10px;justify-content:center;flex-wrap:wrap'>" + "".join([f"<div style='background:#f0f6ff;border-radius:980px;padding:8px 16px;font-size:13px;color:#0071e3;font-weight:400'>Detected: {m}</div>" for m in other_methods]) + "</div>" if other_methods else ""}
                <div style="margin-top:24px;background:#f5f5f7;border-radius:14px;padding:20px 24px;text-align:left">
                    <div style="font-size:12px;font-weight:600;color:#1d1d1f;text-transform:uppercase;letter-spacing:.05em;margin-bottom:12px">Common reasons GTM is not found</div>
                    <div style="font-size:13px;color:#6e6e73;font-weight:300;line-height:2">
                        🛍️ <strong style="color:#1d1d1f;font-weight:500">Shopify native tracking</strong> — Shopify has built-in analytics and many stores use the Shopify pixel instead of GTM<br>
                        📦 <strong style="color:#1d1d1f;font-weight:500">Direct GA4 integration</strong> — Some sites fire GA4 directly via gtag.js without GTM<br>
                        🔒 <strong style="color:#1d1d1f;font-weight:500">Server-side tracking</strong> — Advanced setups where tags fire server-side, invisible in the page source<br>
                        🧩 <strong style="color:#1d1d1f;font-weight:500">Custom CMS or platform</strong> — Platforms like Webflow, Wix, or Squarespace have their own native integrations<br>
                        ⚡ <strong style="color:#1d1d1f;font-weight:500">Single Page App</strong> — React or Next.js sites may load GTM dynamically, making it hard to detect
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            return

        gtm_id = gtm_ids[0]

        with st.spinner(f"Fetching GTM container {gtm_id}..."):
            gtm_script = fetch_gtm_script(gtm_id)
            parsed = parse_gtm_container(gtm_script)

        # Show parsed container summary
        if parsed:
            st.markdown(f"""
            <div style="background:#f0f6ff;border-radius:12px;padding:12px 18px;margin-bottom:12px;display:flex;gap:20px;font-size:12px;color:#0071e3;font-weight:400">
                <span>✓ Container parsed</span>
                <span>{len(parsed.get('tags',[]))} real tags found</span>
                <span>{len(parsed.get('variables',[]))} variables found</span>
                <span>Version {parsed.get('version','?')}</span>
            </div>
            """, unsafe_allow_html=True)

        with st.spinner("Running AI audit..."):
            audit = run_groq_audit(gtm_script, signals, url, gtm_id, api_key, parsed)

        if not audit:
            st.error("Audit failed. Please try again.")
            return

        domain = url.replace('https://', '').replace('http://', '').split('/')[0]

        # ── Site Header ──
        st.markdown(f"""
        <div class="site-header">
            <div style="display:flex;align-items:center;gap:16px">
                <div style="width:48px;height:48px;background:#f0f6ff;border-radius:12px;display:flex;align-items:center;justify-content:center;font-weight:600;font-size:16px;color:#0071e3;flex-shrink:0">{domain[:2].upper()}</div>
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

        # ── Metrics ──
        score = audit.get('health_score', 0)
        score_color = '#34c759' if score >= 70 else '#ff9f0a' if score >= 50 else '#ff3b30'
        c1, c2, c3, c4, c5 = st.columns(5)
        for col, num, lbl, color in [
            (c1, str(score), "Health Score", score_color),
            (c2, str(audit.get('tags_found', 0)), "Tags Found", "#0071e3"),
            (c3, str(audit.get('triggers_found', 0)), "Triggers", "#0071e3"),
            (c4, str(audit.get('variables_found', 0)), "Variables", "#0071e3"),
            (c5, str(audit.get('issues_count', 0)), "Issues", "#ff3b30"),
        ]:
            with col:
                st.markdown(f'<div class="metric-card"><div class="metric-num" style="color:{color}">{num}</div><div class="metric-lbl">{lbl}</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── GA4 Banner ──
        ga4 = audit.get('ga4', {})
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
            for tag in audit.get('tags', []):
                rec = f'<div class="tag-rec">→ {tag["recommendation"]}</div>' if tag.get('recommendation') else ''
                st.markdown(f'<div class="tag-card {tag.get("status","info")}"><div style="display:flex;align-items:center"><span class="tag-name">{tag["name"]}</span>{render_badge(tag.get("status","info"))}</div><div class="tag-detail">{tag.get("detail","")}</div>{rec}</div>', unsafe_allow_html=True)

        with col_right:
            st.markdown("### Triggers")
            for t in audit.get('triggers', []):
                rec = f'<div class="tag-rec">→ {t["recommendation"]}</div>' if t.get('recommendation') else ''
                st.markdown(f'<div class="tag-card {t.get("status","info")}"><div style="display:flex;align-items:center"><span class="tag-name">{t["name"]}</span>{render_badge(t.get("status","info"))}</div><div class="tag-detail">{t.get("detail","")}</div>{rec}</div>', unsafe_allow_html=True)

        # ── Issues ──
        if audit.get('top_issues'):
            st.markdown("### Top issues to fix")
            for issue in audit['top_issues']:
                cls = 'fail' if issue.get('priority') == 'high' else 'warn' if issue.get('priority') == 'medium' else 'info'
                st.markdown(f'<div class="tag-card {cls}"><div style="display:flex;align-items:center"><span class="tag-name">{issue["title"]}</span>{render_priority_badge(issue.get("priority","medium"))}</div><div class="tag-detail">{issue.get("detail","")}</div><div class="tag-rec">→ {issue.get("fix","")}</div></div>', unsafe_allow_html=True)

        # ── Quick Wins ──
        if audit.get('quick_wins'):
            st.markdown("### Quick wins")
            st.markdown('<div class="section-card">' + ''.join([f'<div style="display:flex;gap:10px;padding:6px 0;border-bottom:1px solid rgba(0,0,0,0.05);font-size:13px;color:#3d3d3f;font-weight:300"><span style="color:#34c759;flex-shrink:0">✓</span> {w}</div>' for w in audit['quick_wins']]) + '</div>', unsafe_allow_html=True)

        st.markdown(f'<div style="text-align:center;padding:32px 0 8px;font-size:11px;color:#b0b0b5">GTM Auditor — {domain} — Powered by Groq</div>', unsafe_allow_html=True)

    # ── What is GTM explainer (bottom) ──
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-top:16px">
        <div class="info-card">
            <div style="font-size:24px;margin-bottom:10px">🏷️</div>
            <h3>What is GTM?</h3>
            <p>Google Tag Manager is a free tool that lets businesses add and manage tracking codes on their website without touching the source code. It controls everything from GA4 to Facebook Pixel to conversion tracking.</p>
        </div>
        <div class="info-card">
            <div style="font-size:24px;margin-bottom:10px">🔍</div>
            <h3>How this tool works</h3>
            <p>Paste any website URL and this tool fetches the real page source, detects the GTM container ID, pulls all tags and triggers, then uses AI to audit the entire setup and flag issues with recommendations.</p>
        </div>
        <div class="info-card">
            <div style="font-size:24px;margin-bottom:10px">💡</div>
            <h3>Who is this for?</h3>
            <p>Digital marketers, analytics consultants, and agency teams who want to quickly check a client or competitor site's tracking setup without needing access to their GTM account.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
