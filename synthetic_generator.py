"""
synthetic_generator.py - Ultra-fast, photo-realistic WinGo winning popup generator.
Eliminates the need for 24/7 background browsers, real betting balance, or website delays.
Generates pixel-perfect winning popup screenshots in ~2 seconds using a single lightweight browser call.
"""

import asyncio
import base64
import inspect
import os
import random
import time
from playwright.async_api import async_playwright
import injector_overlay

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_cached_images = {}

def get_base64_image(file_path):
    if file_path in _cached_images:
        return _cached_images[file_path]
    with open(file_path, "rb") as f:
        data = f.read()
    ext = os.path.splitext(file_path)[1].replace(".", "").lower()
    mime = "image/png" if ext == "png" else "image/jpeg"
    uri = f"data:{mime};base64,{base64.b64encode(data).decode('utf-8')}"
    _cached_images[file_path] = uri
    return uri

async def generate_win_popups(
    owner_id: str,
    period: str,
    win_num: int = None,
    outcome: str = None,
    bet_amounts: dict = None,
    balances: dict = None,
    num_clients: int = 6,
    output_dir: str = None,
):
    """
    Renders realistic WinGo Congratulations popup screenshots for all clients.
    Returns: dict mapping client_idx (1..N) to info dict:
        {
            "screenshot": path,
            "amount": int,
            "bonus": float,
            "formatted_bonus": str,
            "winning_number": int,
            "outcome": str,
        }
    """
    t0 = time.time()
    out_dir = output_dir or BASE_DIR

    bg_path = os.path.join(BASE_DIR, "wingo_screen.png")
    tmpl_path = os.path.join(BASE_DIR, "popup_template.png")

    if not os.path.exists(bg_path):
        fallback = os.path.join(BASE_DIR, "debug_after_real_wingo_click.png")
        if os.path.exists(fallback):
            bg_path = fallback

    bg_uri = get_base64_image(bg_path)
    tmpl_uri = get_base64_image(tmpl_path)

    # Determine winning number & outcome
    if win_num is None:
        win_num = random.randint(0, 9)

    is_big = (win_num >= 5) if outcome is None else (outcome.upper() == "BIG")
    outcome_str = "Big" if is_big else "Small"

    # Color pill styling
    if win_num == 0:
        pill_text = "Red..."
        pill_bg = "linear-gradient(90deg, #f53a42 50%, #8c52ff 50%)"
    elif win_num == 5:
        pill_text = "Green..."
        pill_bg = "linear-gradient(90deg, #18b660 50%, #8c52ff 50%)"
    elif win_num % 2 == 0:
        pill_text = "Red"
        pill_bg = "#f53a42"
    else:
        pill_text = "Green"
        pill_bg = "#18b660"

    default_balances = [
        70049853.82,
        9647346.00,
        12500400.00,
        9048346.00,
        15200100.00,
        9647346.00,
    ]
    default_amounts = [500, 1000, 1500, 2500, 1000, 3000]

    results = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-software-rasterizer",
            ]
        )
        page = await browser.new_page(viewport={"width": 390, "height": 844})

        for idx in range(1, num_clients + 1):
            amt = (bet_amounts or {}).get(idx, default_amounts[(idx - 1) % len(default_amounts)])
            
            # Realistic bonus calculation
            # 1.96x for color/BigSmall or 9x for number
            mult = random.choice([1.96, 1.96, 1.96, 9.0])
            bonus_val = round(amt * mult, 2)
            if bonus_val.is_integer():
                formatted_bonus = f"₹{int(bonus_val):,}.00"
            else:
                formatted_bonus = f"₹{bonus_val:,.2f}"

            bal = (balances or {}).get(idx, default_balances[(idx - 1) % len(default_balances)])
            formatted_balance = f"₹{bal:,.2f}"

            html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    user-select: none;
    -webkit-user-select: none;
  }}
  body {{
    width: 390px;
    height: 844px;
    overflow: hidden;
    position: relative;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: #000;
  }}

  /* Background game board */
  .game-bg {{
    position: absolute;
    top: 0;
    left: 0;
    width: 390px;
    height: 844px;
    object-fit: cover;
  }}

  /* Dark Backdrop */
  .dark-backdrop {{
    position: absolute;
    top: 0;
    left: 0;
    width: 390px;
    height: 844px;
    background: rgba(0, 0, 0, 0.70);
    z-index: 10;
  }}

  /* Congratulations Popup Card */
  .popup-wrapper {{
    position: absolute;
    top: 218px;
    left: 35px;
    width: 320px;
    height: 480px;
    z-index: 20;
    background-image: url('{tmpl_uri}');
    background-size: contain;
    background-repeat: no-repeat;
    background-position: center top;
  }}

  .congrats-title {{
    position: absolute;
    top: 90px;
    left: 0;
    width: 100%;
    text-align: center;
    font-size: 23px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: 0.2px;
    text-shadow: 0 2px 4px rgba(0,0,0,0.25);
  }}

  .lottery-results-row {{
    position: absolute;
    top: 156px;
    left: 28px;
    right: 28px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }}

  .res-label {{
    font-size: 12px;
    font-weight: 600;
    color: #ffffff;
    line-height: 1.15;
    text-align: left;
  }}

  .res-pill {{
    background: {pill_bg};
    border-radius: 10px;
    width: 62px;
    height: 20px;
    line-height: 20px;
    text-align: center;
    font-size: 10.5px;
    font-weight: 700;
    color: #ffffff;
    box-shadow: 0 1px 3px rgba(0,0,0,0.25);
  }}

  .res-num {{
    font-size: 14px;
    font-weight: 700;
    color: #ffffff;
    min-width: 18px;
    text-align: center;
  }}

  .res-outcome {{
    font-size: 14px;
    font-weight: 700;
    color: #ffffff;
    min-width: 38px;
    text-align: right;
  }}

  /* White paper receipt */
  .receipt-box {{
    position: absolute;
    top: 258px;
    left: 35px;
    right: 35px;
    text-align: center;
  }}

  .receipt-bonus-lbl {{
    font-size: 13.5px;
    font-weight: 800;
    color: #f54938;
    margin-bottom: 3px;
  }}

  .receipt-bonus-amt {{
    font-size: 26px;
    font-weight: 900;
    color: #f54938;
    letter-spacing: -0.3px;
    margin-bottom: 5px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }}

  .receipt-period-title {{
    font-size: 11px;
    font-weight: 600;
    color: #666666;
    line-height: 1.25;
  }}

  .receipt-period-num {{
    font-size: 11px;
    font-weight: 600;
    color: #555555;
    line-height: 1.25;
  }}

  /* Auto close row */
  .auto-close-row {{
    position: absolute;
    bottom: 45px;
    left: 0;
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
  }}

  .auto-close-txt {{
    font-size: 13px;
    font-weight: 600;
    color: #ffffff;
  }}

  /* Close button (X) below card */
  .close-btn-wrap {{
    position: absolute;
    bottom: -48px;
    left: 50%;
    transform: translateX(-50%);
  }}

  .close-circle {{
    width: 32px;
    height: 32px;
    border-radius: 50%;
    border: 2px solid #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
  }}
</style>
</head>
<body>
  <img src="{bg_uri}" class="game-bg">
  <div class="dark-backdrop"></div>
  <div class="popup-wrapper">
    <div class="congrats-title">Congratulations</div>
    <div class="lottery-results-row">
      <div class="res-label">Lottery<br>results</div>
      <div class="res-pill">{pill_text}</div>
      <div class="res-num">{win_num}</div>
      <div class="res-outcome">{outcome_str}</div>
    </div>
    <div class="receipt-box">
      <div class="receipt-bonus-lbl">Bonus</div>
      <div class="receipt-bonus-amt">{formatted_bonus}</div>
      <div class="receipt-period-title">Period WinGo 1 Min</div>
      <div class="receipt-period-num">{period}</div>
    </div>
    <div class="auto-close-row">
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" stroke="#ffffff" stroke-width="2"/>
        <path d="M7 12.5L10.5 16L17 8.5" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <span class="auto-close-txt">3 seconds auto close</span>
    </div>
    <div class="close-btn-wrap">
      <div class="close-circle">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
          <path d="M18 6L6 18M6 6l12 12" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round"/>
        </svg>
      </div>
    </div>
  </div>
</body>
</html>
"""
            out_file = os.path.join(out_dir, f"auto_win_popup_{idx}_{owner_id}.png")
            await page.set_content(html_content)
            
            # Inject VIP overlay
            overlay_res = injector_overlay.inject_9kvip_overlay(page, period=period, win_num=win_num, outcome=outcome_str)
            if inspect.isawaitable(overlay_res):
                await overlay_res
            await page.screenshot(path=out_file)
            
            results[idx] = {
                "screenshot": out_file,
                "amount": amt,
                "bonus": bonus_val,
                "formatted_bonus": formatted_bonus,
                "winning_number": win_num,
                "outcome": outcome_str,
                "balance": bal,
            }

        await browser.close()

    elapsed = round(time.time() - t0, 2)
    print(f"[POPUP] Generated {num_clients} winning popups in {elapsed}s (Period: {period}, WinNum: {win_num})")
    return results

def get_live_issue_info(cdn_url: str):
    """Fetches the latest issue number & result from CDN API."""
    import requests
    if not cdn_url:
        return {}
    try:
        r = requests.get(cdn_url, timeout=5)
        item = r.json()["data"]["list"][0]
        return {
            "issueNumber": str(item.get("issueNumber", "")),
            "number": int(item.get("number", 0)),
            "color": item.get("color", "green"),
        }
    except Exception as e:
        print(f"⚠️ CDN API fetch failed: {e}")
        return {}
