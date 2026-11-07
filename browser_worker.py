import os
import sys
import json
import shutil

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(__file__)


from playwright.sync_api import sync_playwright

import wingo

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

load_dotenv()

client_idx = int(sys.argv[1]) if len(sys.argv) > 1 else 1
phone = sys.argv[2] if len(sys.argv) > 2 else ""
password = sys.argv[3] if len(sys.argv) > 3 else ""
owner_id = sys.argv[4] if len(sys.argv) > 4 else ""

HEADLESS = os.getenv("HEADLESS", "false").lower() in ("true", "1", "yes")


def emit(marker, text=""):
    print(f"{marker}{text}", flush=True)


def main():
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

        launch_options = {
            "headless": HEADLESS,
            "ignore_default_args": [
                "--enable-unsafe-swiftshader",
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
                "--disable-backgrounding-occluded-windows"
            ],
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
                "--disable-webgl",
                "--disable-webgl2",
                "--disable-3d-apis",
                "--use-gl=disabled",
                "--disable-gpu-rasterization",
                "--disable-threaded-animation",
                "--disable-threaded-scrolling",
                "--disable-extensions",
                "--disable-background-networking",
                "--disable-default-apps",
                "--disable-sync",
                "--mute-audio",
                "--window-size=375,667",
                "--js-flags=--max-old-space-size=128",
            ],
            **wingo.MOBILE_CONTEXT,
        }

        if chromium_path and os.path.exists(chromium_path):
            print(f"🌐 Using system Chromium: {chromium_path}", flush=True)
            launch_options["executable_path"] = chromium_path

        with p.chromium.launch_persistent_context(
            wingo.profile_dir(client_idx, owner_id),
            **launch_options
        ) as context:
            page = context.pages[0] if context.pages else context.new_page()

            ok = client.open_room(page)
            period = client.current_period(page) or "?"
            if ok:
                client.log(f"🎯 Browser ready on WinGo 1Min (period {period})")
                emit("__READY__", f"period {period}")
                # Freeze continuous CSS/Canvas animations to keep CPU at 0%
                try:
                    page.evaluate("""() => {
                        const style = document.createElement('style');
                        style.id = 'freeze-anim';
                        style.innerHTML = `*, *::before, *::after { animation-duration: 0.001s !important; animation-iteration-count: 1 !important; transition: none !important; }`;
                        document.head.appendChild(style);
                    }""")
                except Exception:
                    pass
            else:
                client.log("⚠️ WinGo board nahi khula — /refresh se dobara try karo")
                emit("__READY_FAILED__", "wingo room nahi khula")
                # Navigate failed/wrong-password pages to blank so they don't burn CPU in background
                try:
                    page.goto("about:blank")
                except Exception:
                    pass

            while True:
                line = sys.stdin.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue

                try:
                    cmd = json.loads(line)
                except Exception:
                    client.log(f"⚠️ Invalid command: {line}")
                    continue

                name = cmd.get("cmd")

                if name == "bet":
                    mode = cmd.get("mode", "bet")
                    try:
                        if not client.current_period(page, timeout=1000):
                            client.log("↩️ Board pe nahi tha — pehle WinGo 1Min khol raha hoon")
                            client.ensure_wingo_room(page)
                        client.run_round(page, mode, cmd.get("period"))
                    except Exception as e:
                        client.log(f"❌ Round error: {e}")
                        client.log(f"FAILED_CLIENT_INFO={client_idx}:{phone}:{password}")
                    try:
                        client.dismiss_announcements(page)
                        if not client.current_period(page, timeout=1500):
                            client.ensure_wingo_room(page)
                    except Exception:
                        pass
                    emit("__BET_DONE__")

                elif name == "refresh":
                    try:
                        status = client.refresh(page)
                    except Exception as e:
                        status = f"refresh error: {e}"
                    emit("__REFRESH_DONE__", status)

                elif name == "keepalive":
                    try:
                        status = client.keepalive(page)
                    except Exception as e:
                        status = f"keepalive error: {e}"
                    emit("__KEEPALIVE_DONE__", status)

                elif name == "shutdown":
                    client.log("👋 Shutting down browser")
                    break

                else:
                    client.log(f"⚠️ Unknown command: {name}")


if __name__ == "__main__":
    try:
        main()
    except (Exception, KeyboardInterrupt) as e:
        import traceback
        traceback.print_exc()
        emit("__READY_FAILED__", str(e))
