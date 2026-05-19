"""
GTM Auditor — Client-side Google Tag Manager audit tool.

Paste any URL → fetch the page → detect GTM container ID → pull the public
gtm.js script → parse tags, triggers, variables → run an AI audit via Groq.

Works without GTM access because gtm.js is publicly served by Google.
"""

import json
import re
from typing import Any
from urllib.parse import urlparse

import requests
import streamlit as st
from groq import Groq

# ─────────────────────────────────────────────────────────────────────────────
# Page config + styling
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="GTM Auditor", page_icon="🔍", layout="wide")

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
html, body, [class*="css"], .stApp, .stApp > div,
div[data-testid="stAppViewContainer"], div[data-testid="stAppViewBlockContainer"],
div[data-testid="block-container"], div[data-testid="stVerticalBlock"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    -webkit-font-smoothing: antialiased;
    color: #1d1d1f !important;
    background-color: #f5f5f7 !important;
}
.main, .stApp { background-color: #f5f5f7 !important; }
.block-container { padding: 2rem 2rem 4rem; max-width: 980px; background: #f5f5f7 !important; }
section[data-testid="stSidebar"] { background: #fff !important; border-right: 1px solid rgba(0,0,0,0.06); }
section[data-testid="stSidebar"] * { color: #1d1d1f !important; }
h1 { font-size: 2.2rem !important; font-weight: 600 !important; letter-spacing: -.03em !important; }
h2 { font-size: 1.3rem !important; font-weight: 600 !important; letter-spacing: -.02em !important; }
h3 { font-size: 1rem !important; font-weight: 500 !important; }
.metric-card { background: #fff; border-radius: 16px; padding: 20px 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); text-align: center; margin-bottom: 8px; }
.metric-num { font-size: 2rem; font-weight: 600; letter-spacing: -.03em; }
.metric-lbl { font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: #86868b; margin-top: 2px; font-weight: 500; }
.tag-card { background: #fff; border-radius: 14px; padding: 16px 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 10px; border-left: 4px solid #e0e0e0; }
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
.stButton > button { background: #0071e3 !important; color: white !important; border: none !important; border-radius: 980px !important; padding: 12px 28px !important; font-size: 15px !important; font-weight: 400 !important; font-family: Inter, sans-serif !important; letter-spacing: -.01em !important; width: 100%; }
.stButton > button:hover { background: #0077ed !important; }
.stTextInput > div > div > input { border-radius: 12px !important; border: 1px solid rgba(0,0,0,0.12) !important; padding: 12px 16px !important; font-size: 15px !important; font-family: Inter, sans-serif !important; font-weight: 300 !important; background: #fff !important; color: #1d1d1f !important; }
.stTextInput > div > div > input:focus { border-color: #0071e3 !important; box-shadow: none !important; }
.detected-pill { background:#f0f6ff;border-radius:980px;padding:6px 14px;font-size:12px;color:#0071e3;font-weight:500;display:inline-block;margin:3px }
</style>
""",
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# GTM internal function names → human-readable tag types.
# Source: observed in production gtm.js scripts.
GTM_TAG_TYPES = {
    "__googtag": "Google Tag (gtag.js)",
    "__ga4": "GA4 Event",
    "__gaawc": "GA4 Configuration",
    "__gaawe": "GA4 Event",
    "__ua": "Universal Analytics (DEPRECATED)",
    "__awct": "Google Ads Conversion",
    "__sp": "Google Ads Remarketing",
    "__cl": "Conversion Linker",
    "__gclidw": "Conversion Linker",
    "__fls": "Floodlight Sales",
    "__flc": "Floodlight Counter",
    "__fbpx": "Facebook Pixel",
    "__tikt": "TikTok Pixel",
    "__pntr": "Pinterest Tag",
    "__lnkd": "LinkedIn Insight Tag",
    "__bzi": "LinkedIn Insight Tag",
    "__twitter_website_tag": "Twitter / X Pixel",
    "__uet": "Microsoft / Bing UET",
    "__html": "Custom HTML",
    "__img": "Custom Image Tag",
    "__hjtc": "Hotjar Tracking",
    "__crto": "Criteo OneTag",
    "__bb": "Snap Pixel",
}

# Detection signatures we look for in page HTML.
TRACKING_SIGNATURES = {
    "facebook_pixel": [r"connect\.facebook\.net", r"\bfbq\("],
    "tiktok_pixel": [r"analytics\.tiktok\.com", r"ttq\.load"],
    "pinterest_tag": [r"\bpintrk\(", r"ct\.pinterest\.com"],
    "linkedin_insight": [r"snap\.licdn\.com/li\.lms-analytics", r"_linkedin_partner_id"],
    "twitter_pixel": [r"static\.ads-twitter\.com", r"\btwq\("],
    "bing_uet": [r"bat\.bing\.com", r"\buetq\b"],
    "snap_pixel": [r"sc-static\.net/scevent", r"snaptr\("],
    "reddit_pixel": [r"redditstatic\.com.*pixel", r"rdt\("],
    "klaviyo": [r"static\.klaviyo\.com", r"klaviyo\.com/onsite"],
    "hubspot": [r"js\.hs-scripts\.com", r"js\.hs-analytics\.net"],
    "hotjar": [r"static\.hotjar\.com", r"\bhj\("],
    "clarity": [r"clarity\.ms"],
    "fullstory": [r"fullstory\.com", r"\bFS\."],
    "segment": [r"cdn\.segment\.com", r"analytics\.load"],
    "amplitude": [r"amplitude\.com/libs"],
    "mixpanel": [r"cdn\.mxpnl\.com", r"mixpanel\.init"],
    "onetrust_consent": [r"cdn\.cookielaw\.org", r"otSDKStub"],
    "cookiebot_consent": [r"consent\.cookiebot\.com"],
    "usercentrics_consent": [r"app\.usercentrics\.eu", r"app\.usercentrics\.com"],
    "shopify": [r"cdn\.shopify\.com", r"Shopify\.theme", r"shopify_pay"],
    "woocommerce": [r"wp-content/plugins/woocommerce"],
    "magento": [r"Magento_", r"/static/version\d+/frontend"],
}


# ─────────────────────────────────────────────────────────────────────────────
# Fetching
# ─────────────────────────────────────────────────────────────────────────────

def normalize_url(raw: str) -> str:
    """Ensure URL has a scheme and is well-formed."""
    raw = raw.strip()
    if not raw:
        return ""
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    parsed = urlparse(raw)
    if not parsed.netloc:
        return ""
    return raw


def fetch_page(url: str) -> str | None:
    """Fetch raw HTML. Returns None on failure."""
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        r.raise_for_status()
        return r.text
    except requests.RequestException as e:
        st.error(f"Could not fetch page: {e}")
        return None


def fetch_gtm_script(gtm_id: str) -> str | None:
    """Pull the public gtm.js for a container ID."""
    url = f"https://www.googletagmanager.com/gtm.js?id={gtm_id}"
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        r.raise_for_status()
        return r.text
    except requests.RequestException as e:
        st.warning(f"Could not fetch gtm.js for {gtm_id}: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Detection
# ─────────────────────────────────────────────────────────────────────────────

def extract_gtm_ids(html: str) -> list[str]:
    """Find all unique GTM-XXXXXX container IDs in the HTML."""
    ids = set(re.findall(r"GTM-[A-Z0-9]{4,12}", html))
    return sorted(ids)


def extract_page_signals(html: str) -> dict[str, Any]:
    """Pull supplementary tracking signals from the page source."""
    detected_tools = []
    for tool, patterns in TRACKING_SIGNATURES.items():
        if any(re.search(p, html, re.I) for p in patterns):
            detected_tools.append(tool)

    # Server-side GTM signature: custom GTM domain or sgtm subdomain
    server_side_gtm = bool(
        re.search(r"sgtm\.|server-side.*gtm|gtm\.[a-z0-9-]+\.[a-z]{2,}\?id=GTM", html, re.I)
    )

    return {
        "ga4_ids": sorted(set(re.findall(r"G-[A-Z0-9]{8,12}", html))),
        "ga_universal_ids": sorted(set(re.findall(r"UA-\d{4,10}-\d{1,4}", html))),
        "google_ads_ids": sorted(set(re.findall(r"AW-\d{8,12}", html))),
        "floodlight_ids": sorted(set(re.findall(r"DC-\d{6,10}", html))),
        "datalayer_pushes": re.findall(r"dataLayer\.push\(\{[^}]{0,300}\}\)", html)[:10],
        "gtag_calls": list(set(re.findall(r"gtag\([^)]{0,200}\)", html)))[:10],
        "consent_mode": bool(re.search(r"gtag\s*\(\s*['\"]consent['\"]", html)),
        "consent_mode_v2": bool(
            re.search(r"ad_user_data|ad_personalization", html)
        ),
        "detected_tools": detected_tools,
        "server_side_gtm": server_side_gtm,
        "script_count": len(re.findall(r"<script", html, re.I)),
    }


# ─────────────────────────────────────────────────────────────────────────────
# GTM container parser
# ─────────────────────────────────────────────────────────────────────────────

def extract_balanced_object(text: str, start_idx: int) -> str | None:
    """Walk braces from start_idx (must point to '{') and return the balanced object."""
    if start_idx < 0 or start_idx >= len(text) or text[start_idx] != "{":
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start_idx, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start_idx : i + 1]
    return None


def parse_gtm_container(script: str | None) -> dict[str, Any] | None:
    """Parse tags, triggers, variables out of a gtm.js container script."""
    if not script:
        return None

    # Find `var data = {` (or `let data = {`) and walk to the closing brace.
    m = re.search(r"(?:var|let|const)\s+data\s*=\s*", script)
    if not m:
        return None
    brace_idx = script.find("{", m.end())
    raw_obj = extract_balanced_object(script, brace_idx)
    if not raw_obj:
        return None

    try:
        data = json.loads(raw_obj)
    except json.JSONDecodeError:
        return None

    resource = data.get("resource", {}) if isinstance(data, dict) else {}
    if not resource:
        return None

    # Tags
    tags = []
    for t in resource.get("tags", []):
        fn = t.get("function", "")
        params = {p.get("key", ""): p.get("value", "") for p in t.get("vtp", []) if isinstance(p, dict)}
        tags.append(
            {
                "function": fn,
                "type": GTM_TAG_TYPES.get(fn, fn.replace("__", "")),
                "name": t.get("instance_name") or t.get("function", "Unknown"),
                "paused": bool(t.get("paused", False)),
                "once_per_event": bool(t.get("once_per_event", False)),
                "params": params,
            }
        )

    # Variables (macros)
    variables = []
    for v in resource.get("macros", []):
        fn = v.get("function", "")
        params = {p.get("key", ""): p.get("value", "") for p in v.get("vtp", []) if isinstance(p, dict)}
        variables.append(
            {
                "function": fn,
                "type": fn.replace("__", ""),
                "name": v.get("instance_name") or fn,
                "params": params,
            }
        )

    # Predicates (conditions)
    predicates = []
    for p in resource.get("predicates", []):
        predicates.append(
            {
                "function": p.get("function", ""),
                "arg0": p.get("arg0", ""),
                "arg1": p.get("arg1", ""),
            }
        )

    # Rules — these map predicates to tags. Approximate "trigger count" by
    # counting unique rule bindings, since GTM "triggers" don't exist
    # natively in gtm.js (the UI assembles them from rules + predicates).
    rules = resource.get("rules", [])

    return {
        "version": resource.get("version", "unknown"),
        "tags": tags,
        "variables": variables,
        "predicates": predicates,
        "rules": rules,
        "tag_count": len(tags),
        "variable_count": len(variables),
        "predicate_count": len(predicates),
        "rule_count": len(rules),
    }


# ─────────────────────────────────────────────────────────────────────────────
# AI audit
# ─────────────────────────────────────────────────────────────────────────────

def build_audit_prompt(
    url: str, gtm_id: str, parsed: dict[str, Any] | None, signals: dict[str, Any]
) -> str:
    """Build the audit prompt for the LLM with parsed container + page signals."""
    container_section = "Container could not be parsed."
    if parsed:
        tag_lines = []
        for t in parsed["tags"][:60]:
            paused_tag = " [PAUSED]" if t["paused"] else ""
            tag_lines.append(
                f"- {t['name']} | type: {t['type']}{paused_tag} | "
                f"params: {json.dumps(t['params'])[:180]}"
            )
        var_lines = []
        for v in parsed["variables"][:60]:
            var_lines.append(f"- {v['name']} | type: {v['type']}")
        pred_lines = []
        for p in parsed["predicates"][:40]:
            pred_lines.append(f"- {p['function']} | arg0={p['arg0']} arg1={p['arg1']}")

        container_section = f"""
Container version: {parsed['version']}
Counts: {parsed['tag_count']} tags, {parsed['variable_count']} variables, {parsed['predicate_count']} predicates, {parsed['rule_count']} rules

TAGS:
{chr(10).join(tag_lines) or '(none)'}

VARIABLES:
{chr(10).join(var_lines) or '(none)'}

PREDICATES (trigger conditions):
{chr(10).join(pred_lines) or '(none)'}
"""

    return f"""You are a senior web analytics implementation auditor. Audit the GTM setup at {url} (Container: {gtm_id}).

GTM CONTAINER (parsed from public gtm.js):
{container_section}

PAGE SIGNALS (from rendered HTML):
- GA4 IDs detected: {signals.get('ga4_ids', [])}
- Universal Analytics IDs (DEPRECATED): {signals.get('ga_universal_ids', [])}
- Google Ads IDs: {signals.get('google_ads_ids', [])}
- Floodlight IDs: {signals.get('floodlight_ids', [])}
- Consent Mode detected: {signals.get('consent_mode', False)}
- Consent Mode v2 signals (ad_user_data / ad_personalization): {signals.get('consent_mode_v2', False)}
- Other tracking tools detected: {signals.get('detected_tools', [])}
- Server-side GTM signals: {signals.get('server_side_gtm', False)}

AUDIT PRIORITIES (apply these standards strictly):
1. Universal Analytics is DEPRECATED (sunset July 2023). Flag any UA tag, UA-XXXXX ID, or analytics.js as a HIGH priority issue.
2. Consent Mode v2 became required for EEA traffic in March 2024. If GA4 / Google Ads are present without `ad_user_data` and `ad_personalization` signals, flag as a HIGH priority issue.
3. GA4 event names must be snake_case. Flag non-compliant custom event names.
4. Conversion Linker should be present whenever Google Ads tags are present.
5. Server-side GTM is a maturity indicator — call it out if missing for ecommerce/lead-gen sites.
6. Duplicate firing: if both Shopify native tracking AND a GTM-based GA4 tag exist, flag duplicate-event risk.
7. Use the ACTUAL tag/variable names from the container above — do not invent names.

Return ONLY valid JSON, no markdown, no commentary:

{{
  "site_summary": "2 sentences about the site and how their tracking is set up",
  "health_score": 0-100,
  "tags_found": <int>,
  "triggers_found": <int>,
  "variables_found": <int>,
  "issues_count": <int>,
  "ga4": {{
    "detected": true|false,
    "measurement_id": "G-XXXXX or null",
    "via": "GTM | direct gtag | both | none",
    "ecommerce": true|false,
    "consent_mode": true|false,
    "consent_mode_v2": true|false,
    "status": "pass|warn|fail",
    "note": "specific observation"
  }},
  "tags": [
    {{"name": "<real tag name>", "type": "<readable type>", "status": "pass|warn|fail|info", "detail": "what it does", "recommendation": "specific fix or null"}}
  ],
  "triggers": [
    {{"name": "<readable trigger label>", "type": "Page View|Click|Form|Custom Event|Timer|...", "status": "pass|warn|fail|info", "detail": "what fires it", "recommendation": "specific fix or null"}}
  ],
  "top_issues": [
    {{"title": "Issue title", "priority": "high|medium|low", "detail": "what is wrong", "fix": "how to fix"}}
  ],
  "quick_wins": ["short actionable win", "..."]
}}"""


def run_audit(api_key: str, prompt: str) -> dict[str, Any] | None:
    """Send prompt to Groq and parse JSON response."""
    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        text = response.choices[0].message.content.strip()
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
        return json.loads(text)
    except json.JSONDecodeError as e:
        st.error(f"AI returned invalid JSON: {e}")
        return None
    except Exception as e:
        st.error(f"AI audit failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Rendering helpers
# ─────────────────────────────────────────────────────────────────────────────

def badge(status: str) -> str:
    mapping = {
        "pass": ("badge-pass", "Pass"),
        "warn": ("badge-warn", "Warning"),
        "fail": ("badge-fail", "Issue"),
        "info": ("badge-info", "Info"),
    }
    cls, label = mapping.get(status, ("badge-info", status.title()))
    return f'<span class="badge {cls}">{label}</span>'


def priority_badge(priority: str) -> str:
    mapping = {"high": "badge-fail", "medium": "badge-warn", "low": "badge-pass"}
    return f'<span class="badge {mapping.get(priority, "badge-info")}">{priority.title()}</span>'


# ─────────────────────────────────────────────────────────────────────────────
# Main app
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    # ── Sidebar ──
    with st.sidebar:
        st.markdown(
            """
        <div style="padding:8px 0 16px">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:20px">
                <div style="width:7px;height:7px;background:#0071e3;border-radius:50%"></div>
                <span style="font-size:13px;font-weight:600;color:#1d1d1f;letter-spacing:-.01em">GTM Auditor</span>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        saved_key = st.secrets.get("GROQ_API_KEY", "") if hasattr(st, "secrets") else ""
        api_key = saved_key or st.text_input(
            "Groq API Key", type="password", placeholder="gsk_...", help="Free at console.groq.com"
        )
        if saved_key:
            st.markdown(
                '<div style="font-size:11px;color:#34c759;margin-top:2px">✓ API key loaded from secrets</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="font-size:11px;color:#86868b;margin-top:2px">Free key at <a href="https://console.groq.com" target="_blank" style="color:#0071e3">console.groq.com</a></div>',
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            """
        <div style="background:#f5f5f7;border-radius:12px;padding:14px 16px">
            <div style="font-size:11px;font-weight:600;color:#1d1d1f;text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px">What this audits</div>
            <div style="font-size:12px;color:#6e6e73;line-height:1.9;font-weight:300">
                GTM tags, triggers, variables<br>
                GA4 + Google Ads + Floodlight<br>
                Universal Analytics deprecation<br>
                Consent Mode v2 compliance<br>
                Server-side GTM signals<br>
                Duplicate tracking risk<br>
                Quick wins and fixes
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # ── Hero ──
    st.markdown(
        """
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
    """,
        unsafe_allow_html=True,
    )

    # ── URL input ──
    col1, col2 = st.columns([4, 1])
    with col1:
        url_input = st.text_input("Website URL", placeholder="https://yourwebsite.com", label_visibility="collapsed")
    with col2:
        analyze = st.button("Audit GTM →")

    if not api_key:
        st.markdown(
            """
        <div style="background:#fff8ec;border-radius:12px;padding:14px 18px;font-size:13px;color:#b25000;font-weight:300;margin-top:8px">
            Add your free Groq API key in the sidebar to get started. Get one at <a href="https://console.groq.com" target="_blank" style="color:#0071e3">console.groq.com</a>
        </div>
        """,
            unsafe_allow_html=True,
        )
        return

    if not (analyze and url_input):
        # Show explainer cards when idle
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            """
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-top:16px">
            <div class="info-card">
                <div style="font-size:24px;margin-bottom:10px">🏷️</div>
                <h3>What is GTM?</h3>
                <p>Google Tag Manager is a free tool that lets businesses add and manage tracking codes on their website without touching the source code. It controls everything from GA4 to Facebook Pixel to conversion tracking.</p>
            </div>
            <div class="info-card">
                <div style="font-size:24px;margin-bottom:10px">🔍</div>
                <h3>How this tool works</h3>
                <p>Paste any website URL. The tool fetches the page source, detects the GTM container ID, pulls the public gtm.js script, parses every tag and variable, then runs an AI audit against current best practices.</p>
            </div>
            <div class="info-card">
                <div style="font-size:24px;margin-bottom:10px">💡</div>
                <h3>Who is this for?</h3>
                <p>Digital marketers, analytics consultants, and agency teams who want to quickly check a client or competitor site's tracking setup without needing access to their GTM account.</p>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
        return

    # ── Run audit ──
    url = normalize_url(url_input)
    if not url:
        st.error("Please enter a valid URL.")
        return

    with st.spinner("Fetching page source..."):
        html = fetch_page(url)
    if not html:
        return

    with st.spinner("Detecting GTM container..."):
        gtm_ids = extract_gtm_ids(html)
        signals = extract_page_signals(html)

    if not gtm_ids:
        # No GTM — render the helpful "what we did find" panel
        pills = "".join(f'<div class="detected-pill">{t.replace("_", " ").title()}</div>' for t in signals["detected_tools"])
        if signals["ga4_ids"]:
            pills += f'<div class="detected-pill">GA4: {", ".join(signals["ga4_ids"])}</div>'
        if signals["ga_universal_ids"]:
            pills += f'<div class="detected-pill">UA (deprecated): {", ".join(signals["ga_universal_ids"])}</div>'

        st.markdown(
            f"""
        <div style="background:#fff;border-radius:18px;padding:32px;box-shadow:0 2px 12px rgba(0,0,0,0.06);text-align:center;margin-top:8px">
            <div style="font-size:36px;margin-bottom:14px">🔎</div>
            <div style="font-size:20px;font-weight:600;color:#1d1d1f;margin-bottom:8px;letter-spacing:-.02em">No GTM container found</div>
            <div style="font-size:14px;color:#6e6e73;font-weight:300;max-width:480px;margin:0 auto;line-height:1.7">
                This website does not appear to be using Google Tag Manager. Many sites manage tracking differently.
            </div>
            <div style="margin-top:18px">{pills}</div>
            <div style="margin-top:24px;background:#f5f5f7;border-radius:14px;padding:20px 24px;text-align:left">
                <div style="font-size:12px;font-weight:600;color:#1d1d1f;text-transform:uppercase;letter-spacing:.05em;margin-bottom:12px">Common reasons GTM is not found</div>
                <div style="font-size:13px;color:#6e6e73;font-weight:300;line-height:2">
                    🛍️ <strong style="color:#1d1d1f;font-weight:500">Shopify native tracking</strong> — Shopify has built-in analytics; many stores use the Shopify pixel instead of GTM<br>
                    📦 <strong style="color:#1d1d1f;font-weight:500">Direct GA4 (gtag.js)</strong> — Some sites fire GA4 directly without GTM<br>
                    🔒 <strong style="color:#1d1d1f;font-weight:500">Server-side tracking</strong> — Tags fire server-side, invisible in the page source<br>
                    🧩 <strong style="color:#1d1d1f;font-weight:500">Custom CMS</strong> — Webflow, Wix, Squarespace have native integrations<br>
                    ⚡ <strong style="color:#1d1d1f;font-weight:500">Single Page App</strong> — React or Next.js sites may load GTM dynamically after initial HTML
                </div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
        return

    gtm_id = gtm_ids[0]

    with st.spinner(f"Fetching GTM container {gtm_id}..."):
        gtm_script = fetch_gtm_script(gtm_id)
        parsed = parse_gtm_container(gtm_script)

    if parsed:
        st.markdown(
            f"""
        <div style="background:#f0f6ff;border-radius:12px;padding:12px 18px;margin-bottom:12px;display:flex;gap:20px;flex-wrap:wrap;font-size:12px;color:#0071e3;font-weight:400">
            <span>✓ Container parsed</span>
            <span>{parsed['tag_count']} tags</span>
            <span>{parsed['variable_count']} variables</span>
            <span>{parsed['predicate_count']} conditions</span>
            <span>{parsed['rule_count']} rules</span>
            <span>Version {parsed['version']}</span>
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        st.warning("Container detected but could not be parsed. AI audit will rely on page signals only.")

    with st.spinner("Running AI audit..."):
        prompt = build_audit_prompt(url, gtm_id, parsed, signals)
        audit = run_audit(api_key, prompt)

    if not audit:
        st.error("Audit failed. Please try again.")
        return

    domain = urlparse(url).netloc

    # ── Site header ──
    st.markdown(
        f"""
    <div class="site-header">
        <div style="display:flex;align-items:center;gap:16px">
            <div style="width:48px;height:48px;background:#f0f6ff;border-radius:12px;display:flex;align-items:center;justify-content:center;font-weight:600;font-size:16px;color:#0071e3;flex-shrink:0">{domain[:2].upper()}</div>
            <div style="flex:1">
                <div style="font-size:18px;font-weight:600;letter-spacing:-.02em;color:#1d1d1f">{domain}</div>
                <div style="font-size:13px;color:#86868b;margin-top:2px;font-weight:300">{audit.get('site_summary', '')}</div>
            </div>
            <div style="text-align:center;flex-shrink:0">
                <div style="font-size:11px;color:#86868b;font-weight:500;text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px">Container</div>
                <span class="gtm-id">{gtm_id}</span>
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ── Metrics ──
    score = audit.get("health_score", 0)
    score_color = "#34c759" if score >= 70 else "#ff9f0a" if score >= 50 else "#ff3b30"
    c1, c2, c3, c4, c5 = st.columns(5)
    metrics = [
        (c1, str(score), "Health Score", score_color),
        (c2, str(audit.get("tags_found", 0)), "Tags Found", "#0071e3"),
        (c3, str(audit.get("triggers_found", 0)), "Triggers", "#0071e3"),
        (c4, str(audit.get("variables_found", 0)), "Variables", "#0071e3"),
        (c5, str(audit.get("issues_count", 0)), "Issues", "#ff3b30"),
    ]
    for col, num, lbl, color in metrics:
        with col:
            st.markdown(
                f'<div class="metric-card"><div class="metric-num" style="color:{color}">{num}</div><div class="metric-lbl">{lbl}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── GA4 banner ──
    ga4 = audit.get("ga4", {})
    cm = "v2" if ga4.get("consent_mode_v2") else ("v1" if ga4.get("consent_mode") else "Off")
    st.markdown(
        f"""
    <div style="background:#0071e3;border-radius:16px;padding:20px 24px;margin-bottom:16px;display:flex;align-items:center;gap:16px;flex-wrap:wrap">
        <div style="background:rgba(255,255,255,.2);width:40px;height:40px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;color:#fff;flex-shrink:0">G4</div>
        <div style="flex:1;min-width:200px">
            <div style="font-size:15px;font-weight:600;color:#fff;letter-spacing:-.01em">Google Analytics 4</div>
            <div style="font-size:12px;color:rgba(255,255,255,.75);margin-top:2px;font-weight:300">{ga4.get('note', '')}</div>
        </div>
        <div style="display:flex;gap:20px;text-align:center;flex-wrap:wrap">
            <div><div style="font-size:11px;color:rgba(255,255,255,.6);text-transform:uppercase;letter-spacing:.05em">ID</div><div style="font-size:13px;font-weight:500;color:#fff;margin-top:2px">{ga4.get('measurement_id') or 'Not found'}</div></div>
            <div><div style="font-size:11px;color:rgba(255,255,255,.6);text-transform:uppercase;letter-spacing:.05em">Via</div><div style="font-size:13px;font-weight:500;color:#fff;margin-top:2px">{ga4.get('via', 'Unknown')}</div></div>
            <div><div style="font-size:11px;color:rgba(255,255,255,.6);text-transform:uppercase;letter-spacing:.05em">Ecommerce</div><div style="font-size:13px;font-weight:500;color:#fff;margin-top:2px">{'Active' if ga4.get('ecommerce') else 'Not found'}</div></div>
            <div><div style="font-size:11px;color:rgba(255,255,255,.6);text-transform:uppercase;letter-spacing:.05em">Consent</div><div style="font-size:13px;font-weight:500;color:#fff;margin-top:2px">{cm}</div></div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ── Detected tools strip ──
    if signals.get("detected_tools"):
        pills = "".join(
            f'<div class="detected-pill">{t.replace("_", " ").title()}</div>'
            for t in signals["detected_tools"]
        )
        st.markdown(
            f'<div style="background:#fff;border-radius:14px;padding:14px 18px;margin-bottom:16px;box-shadow:0 2px 8px rgba(0,0,0,0.05)"><div style="font-size:11px;font-weight:600;color:#86868b;text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px">Also detected on the page</div>{pills}</div>',
            unsafe_allow_html=True,
        )

    # ── Tags + Triggers ──
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("### Tags")
        for tag in audit.get("tags", []):
            rec = f'<div class="tag-rec">→ {tag["recommendation"]}</div>' if tag.get("recommendation") else ""
            st.markdown(
                f'<div class="tag-card {tag.get("status","info")}">'
                f'<div style="display:flex;align-items:center"><span class="tag-name">{tag["name"]}</span>{badge(tag.get("status","info"))}</div>'
                f'<div class="tag-detail">{tag.get("detail","")}</div>{rec}</div>',
                unsafe_allow_html=True,
            )

    with col_right:
        st.markdown("### Triggers")
        for t in audit.get("triggers", []):
            rec = f'<div class="tag-rec">→ {t["recommendation"]}</div>' if t.get("recommendation") else ""
            st.markdown(
                f'<div class="tag-card {t.get("status","info")}">'
                f'<div style="display:flex;align-items:center"><span class="tag-name">{t["name"]}</span>{badge(t.get("status","info"))}</div>'
                f'<div class="tag-detail">{t.get("detail","")}</div>{rec}</div>',
                unsafe_allow_html=True,
            )

    # ── Top issues ──
    if audit.get("top_issues"):
        st.markdown("### Top issues to fix")
        for issue in audit["top_issues"]:
            cls = (
                "fail" if issue.get("priority") == "high"
                else "warn" if issue.get("priority") == "medium"
                else "info"
            )
            st.markdown(
                f'<div class="tag-card {cls}">'
                f'<div style="display:flex;align-items:center"><span class="tag-name">{issue["title"]}</span>{priority_badge(issue.get("priority","medium"))}</div>'
                f'<div class="tag-detail">{issue.get("detail","")}</div>'
                f'<div class="tag-rec">→ {issue.get("fix","")}</div></div>',
                unsafe_allow_html=True,
            )

    # ── Quick wins ──
    if audit.get("quick_wins"):
        st.markdown("### Quick wins")
        wins_html = "".join(
            f'<div style="display:flex;gap:10px;padding:6px 0;border-bottom:1px solid rgba(0,0,0,0.05);font-size:13px;color:#3d3d3f;font-weight:300"><span style="color:#34c759;flex-shrink:0">✓</span> {w}</div>'
            for w in audit["quick_wins"]
        )
        st.markdown(f'<div class="section-card">{wins_html}</div>', unsafe_allow_html=True)

    st.markdown(
        f'<div style="text-align:center;padding:32px 0 8px;font-size:11px;color:#b0b0b5">GTM Auditor — {domain} — Powered by Groq</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
