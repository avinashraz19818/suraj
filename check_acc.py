
import os, sys, json
from playwright.sync_api import sync_playwright
import wingo

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        wingo.profile_dir(1, '6649173245'),
        executable_path='/usr/bin/google-chrome-stable',
        headless=True
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.goto('https://9k2.club9.eu.cc/WinGo/WinGo_1M')
    page.wait_for_timeout(3000)
    
    # Check text content of wallet / balance
    html = page.evaluate('() => document.body.innerText')
    print('PAGE TEXT SUMMARY:')
    for line in html.splitlines():
        if any(w in line.lower() for w in ['balance', 'wallet', '₹', 'rs', 'coin', '1234567891']):
            print('  ->', line)
    
    # Check localStorage / sessionStorage
    storage = page.evaluate('() => JSON.stringify(window.localStorage)')
    print('STORAGE KEYS:', list(json.loads(storage).keys()))
    
    context.close()
