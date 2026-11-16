"""
IMARA ONE Shield - Anonymous Safe Reader Gateway
Fetches web pages server-side, eliminating tracking scripts, beacons, and ads
before rendering a clean, secure view without leaking client IP.
"""

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import HTMLResponse
import httpx
from bs4 import BeautifulSoup

from backend.app.security.ssrf import validate_url_safe
from backend.app.security.shield_analyzer import shield_analyzer

router = APIRouter(tags=["Shield Proxy"])


@router.get("/proxy/preview", response_class=HTMLResponse)
def get_anonymous_page_preview(
    url: str = Query(..., description="Target webpage URL to view safely"),
):
    """
    Renders an anonymized, tracker-free reader view of any web page.
    Protects user IP and blocks all client-side telemetry.
    """
    is_safe, val_url, _ = validate_url_safe(url)
    if not is_safe:
        raise HTTPException(status_code=400, detail=f"Target URL blocked by security policy: {val_url}")

    # Analyze safety
    shield_info = shield_analyzer.analyze_url(val_url)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        with httpx.Client(timeout=8.0, follow_redirects=True, headers=headers) as client:
            resp = client.get(val_url)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="Unable to retrieve target page.")
            html_text = resp.text
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Shield proxy gateway error: {str(e)}")

    # Parse and cleanse HTML
    soup = BeautifulSoup(html_text, "html.parser")

    # Title
    title = soup.title.string.strip() if soup.title and soup.title.string else val_url

    # Strip dangerous tags: scripts, iframes, embed, object, trackers
    for tag in soup(["script", "iframe", "embed", "object", "noscript", "svg", "form"]):
        tag.decompose()

    # Extract clean article or main body
    main_content = soup.find("article") or soup.find("main") or soup.find("body") or soup

    # Build safe reader template
    safe_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>[Shield View] {title}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #080D18;
      color: #E2E8F0;
      line-height: 1.7;
      margin: 0;
      padding: 0;
    }}
    .shield-banner {{
      position: sticky;
      top: 0;
      background: #111B2C;
      border-bottom: 1px solid #25344A;
      padding: 12px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 13px;
      z-index: 100;
    }}
    .shield-brand {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 700;
      color: #3987FF;
      letter-spacing: 0.5px;
    }}
    .shield-pill {{
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.4);
      color: #10B981;
      padding: 3px 10px;
      border-radius: 9999px;
      font-size: 11px;
      font-weight: 600;
    }}
    .article-container {{
      max-width: 780px;
      margin: 40px auto;
      padding: 0 20px 80px 20px;
    }}
    h1, h2, h3, h4 {{
      color: #FFFFFF;
      margin-top: 1.5em;
    }}
    a {{
      color: #3987FF;
      text-decoration: underline;
    }}
    img {{
      max-width: 100%;
      height: auto;
      border-radius: 8px;
    }}
    p {{
      margin-bottom: 1.2em;
    }}
  </style>
</head>
<body>
  <div class="shield-banner">
    <div class="shield-brand">
      <span>🛡️ IMARA ONE SHIELD</span>
      <span style="color: #A7B4C8; font-weight: 400;">• Anonymous Reader View</span>
    </div>
    <div style="display: flex; gap: 12px; align-items: center;">
      <span class="shield-pill">IP Cloaked • {shield_info['trackers_count']} Trackers Blocked</span>
      <a href="{val_url}" target="_blank" rel="noopener noreferrer" style="color: #A7B4C8; font-size: 12px; text-decoration: none;">Original Site ↗</a>
    </div>
  </div>

  <div class="article-container">
    <h1 style="font-size: 28px; line-height: 1.3; margin-bottom: 8px;">{title}</h1>
    <div style="font-size: 12px; color: #A7B4C8; margin-bottom: 24px; padding-bottom: 12px; border-bottom: 1px solid #25344A;">
      Source: <strong>{val_url}</strong> • Shield Security Rating: <strong>{shield_info['shield_score']}% ({shield_info['shield_status']})</strong>
    </div>

    <div>
      {main_content.decode_contents()}
    </div>
  </div>
</body>
</html>"""

    return HTMLResponse(content=safe_html, status_code=200)

