import os
import sys
import shutil

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(__file__)

from playwright.sync_api import sync_playwright

import wingo

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

load_dotenv()

client_idx = int(sys.argv[1]) if len(sys.argv) > 1 else 1
phone = sys.argv[2] if len(sys.argv) > 2 else ""
password = sys.argv[3] if len(sys.argv) > 3 else ""
mode = sys.argv[4] if len(sys.argv) > 4 else "bet"
owner_id = sys.argv[5] if len(sys.argv) > 5 else ""
intended_period = sys.argv[6] if len(sys.argv) > 6 else ""

HEADLESS = os.getenv("HEADLESS", "false").lower() in ("true", "1", "yes")


def run_betting_sequence():
    client = wingo.WingoClient(client_idx, phone, password, owner_id)

    with sync_playwright() as p:
        chromium_path = (
            os.getenv("SMEX_CHROMIUM_PATH")
            or os.getenv("CHROMIUM_EXECUTABLE_PATH")
            or shutil.which("google-chrome-stable")
            or shutil.which("google-chrome")
            or ("/usr/bin/google-chrome-stable" if os.path.exists("/usr/bin/google-chrome-stable") else None)
            or shutil.which("chromium")
            or shutil.which("chrome")
        )
        if not chromium_path:
            for candidate in [
                "/usr/bin/google-chrome-stable",
                "/usr/bin/google-chrome",
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                "/usr/bin/chromium",
            ]:
                if os.path.exists(candidate):
                    chromium_path = candidate
                    break

        launch_kwargs = {
            "headless": HEADLESS,
            "ignore_default_args": ["--enable-unsafe-swiftshader"],
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-gpu-compositing",
                "--disable-software-rasterizer",
                "--disable-accelerated-2d-canvas",
                "--disable-accelerated-video-decode",
                "--disable-gl-drawing-for-tests",
                "--disable-extensions",
                "--disable-background-networking",
                "--disable-default-apps",
                "--disable-sync",
                "--mute-audio",
                "--window-size=375,667",
            ],
            **wingo.MOBILE_CONTEXT,
        }
        if chromium_path and os.path.exists(chromium_path):
            launch_kwargs["executable_path"] = chromium_path

        with p.chromium.launch_persistent_context(
            wingo.profile_dir(client_idx, owner_id),
            **launch_kwargs
        ) as context:
            page = context.pages[0] if context.pages else context.new_page()
            try:
                client.open_room(page)
                client.log("🎯 Connected to Wingo Room")
                client.run_round(page, mode, intended_period or None)
            finally:
                try:
                    page.close()
                except Exception:
                    pass
                try:
                    context.close()
                except Exception:
                    pass


if __name__ == '__main__':
    run_betting_sequence()
