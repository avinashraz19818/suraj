
from playwright.sync_api import sync_playwright
import wingo
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(wingo.profile_dir(3, '6649173245'), executable_path='/usr/bin/google-chrome-stable', headless=True, **wingo.MOBILE_CONTEXT)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.screenshot(path='/root/surajfeed/debug_client3.png')
    ctx.close()
