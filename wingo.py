import os
import re
import json
import time
import random

try:
    from injector_overlay import inject_9kvip_overlay
except Exception:
    def inject_9kvip_overlay(*args, **kwargs):
        return {"success": False}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

MOBILE_CONTEXT = dict(
    viewport={'width': 390, 'height': 844},
    user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 '
               '(KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
    device_scale_factor=1,
    is_mobile=True,
    has_touch=True,
)

# ---- Real WinGo (ar-lottery / 51game / saasLottery) h5 DOM selectors ----
# Verified against the actual frontend: js/elements.js, js/events.js, index.html
PERIOD_SELECTOR = ".TimeLeft__C-id"
TIME_SELECTOR = ".TimeLeft__C-time"
NUM_ITEM_SELECTOR = ".Betting__C-numC-item"          # -> .Betting__C-numC-item0 .. item9
GAME_ITEM_SELECTOR = ".GameList__C-item"
BALANCE_SELECTOR = ".Wallet__C-balance-l1"
BET_POPUP_SELECTOR = ".lottery-container, .Betting__Popup-body"
BET_CONFIRM_SELECTOR = ".footer button.bet-amount, button.bet-amount, .Betting__Popup-foot-s, button:has-text('Total amount')"
BET_CANCEL_SELECTOR = ".footer button.cancel, button.cancel, .Betting__Popup-foot-c, button:has-text('Cancel')"
BET_AGREE_SELECTOR = ".agreement div[role='checkbox'], .agreement .van-checkbox, .Betting__Popup-agree"
BET_SHEET_ITEM_SELECTOR = ".amount-buttons > div, .amount-section .amount-buttons > div, .Betting__Popup-body-line-item"
BET_QUANTITY_INPUT_SELECTOR = ".multiplier-section input[type='number'], .multiplier-section input, .m input, #van-field-5-input, .Betting__Popup-input input"
TOAST_SUCCESS_SELECTOR = ".van-toast, .van-toast__text, .van-toast--text"
TOAST_FAIL_SELECTOR = ".van-toast--fail, .van-toast:has-text('insufficient'), .van-toast:has-text('fail'), .van-toast:has-text('parameter')"
WIN_DIALOG_SELECTOR = ".winning:not([style*='display: none']), .winning-body.isWin, .winning-wrap-l1.isWin, .WinningTip__C"
LOGIN_PHONE_SELECTOR = "input[name='userNumber'], input[placeholder*='phone'], input[placeholder*='Phone']"
LOGIN_PASS_SELECTOR = "input[type='password'], input[placeholder*='password'], input[placeholder*='Password']"
LOGIN_SUBMIT_SELECTOR = (
    "button.sf-submit, "
    "button:has-text('Login'), button:has-text('Log in'), button:has-text('Log In'), "
    ".signIn__container-button button, .btn_main_style"
)

CLOSE_SELECTORS = [
    ".first-recharge-queue-dialog__close",
    ".closeBtn",
    ".close-btn",
    ".van-icon-cross",
    ".van-icon-close",
    ".van-popup__close-icon",
    ".van-popup__close-icon--bottom",
    ".dialog__close",
    "img[src*='close']",
    "[class*='close-icon']",
    "[class*='CloseBtn']",
    ".activity-close",
]

# Betting/timing tuning.
# WinGo 1M rule: "1 minute 1 issue, 45 seconds to order, 15 seconds waiting for
# the draw" — ordering LOCKS 15s before the draw. Clicking numbers inside that
# window is what caused the endless "Modal still open (Glitch detected)" retries.
GAME_LOCK_SECONDS = 15    # site closes ordering 15s before the draw
BET_MIN_SECONDS = 17      # never click numbers closer than this to the draw
BET_STOP_SECONDS = 16     # mid-loop: stop before entering the locked zone
MIN_WINDOW_SECONDS = 20   # need ~5s usable to fit all 10 bets before the lock
                          # (works whether a fresh window shows 45s or 59s)
WAIT_WINDOW_TIMEOUT = 80  # max seconds to wait for a fresh betting window
WAIT_FLIP_TIMEOUT = 12    # max seconds to wait for a lagging board to flip
BET_UNIT_CAP = 100       # prefer the "100" balance chip (same as the old behaviour)
DEFAULT_BET_UNIT = 100
POPUP_OPEN_TIMEOUT = 1200   # ms after clicking a number
POPUP_CLOSE_TIMEOUT = 1200  # ms after clicking Confirm/Cancel


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def profile_dir(idx, owner_id):
    return os.path.join(BASE_DIR, f"playwright_profile_{idx}_{owner_id}")


def period_matches(on_page: str, intended: str) -> bool:
    """True when the on-page period looks like the intended period.
    Compares the matching suffix length so 3-digit periods (e.g. 699) work correctly."""
    if not on_page or not intended:
        return False
    a = ''.join(filter(str.isdigit, on_page))
    b = ''.join(filter(str.isdigit, intended))
    if not a or not b:
        return False
    match_len = min(len(a), len(b))
    return a[-match_len:] == b[-match_len:]


def _period_seq(period: str):
    """Sequence number of a period as int, or None."""
    d = ''.join(filter(str.isdigit, period or ''))
    if not d:
        return None
    seq_str = d[-5:] if len(d) >= 5 else d
    try:
        return int(seq_str)
    except ValueError:
        return None


class WingoClient:
    def __init__(self, idx, phone, password, owner_id, config=None):
        self.idx = idx
        self.phone = phone
        self.password = password
        self.owner_id = owner_id

        cfg = config or load_config()
        self.owner_cfg = cfg.get("owners", {}).get(owner_id, {})
        urls = self.owner_cfg.get("urls", {})
        self.login_url = urls.get("login_url", "https://9k2.club9.eu.cc/#/login")
        self.room_url = urls.get(
            "wingo_room_url",
            "https://9k2.club9.eu.cc/#/saasLottery/WinGo?gameCode=WinGo_1M&lottery=WinGo"
        )
        self.cdn_url = urls.get("cdn_url", "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json")

        # Auto-normalize room url to direct game URL for reliable automation
        if "9k2.club9.eu.cc" in self.room_url or "9kvip.html" in self.room_url or "web.club9.eu.cc" in self.room_url:
            self.room_url = "https://9k2.club9.eu.cc/WinGo/WinGo_1M"
        if "9kvip.html" in self.login_url or "web.club9.eu.cc" in self.login_url:
            self.login_url = "https://9k2.club9.eu.cc/#/login"

    # ------------------------------------------------------------------ #
    #  logging + emit
    # ------------------------------------------------------------------ #
    def log(self, msg):
        print(msg, flush=True)

    def _emit_status(self, key, value):
        """Orchestrator-readable status lines. Prefix is indexed by client id."""
        self.log(f"{key}_{self.idx}={value}")

    def _emit_failed(self):
        self.log(f"FAILED_CLIENT_INFO={self.idx}:{self.phone}:{self.password}")
        self.log(f"INCOMPLETE_BETS_ERROR_FOR_CLIENT={self.idx}")

    # ------------------------------------------------------------------ #
    #  tiny locator helpers (safe against the old .count() overflow bug)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _visible(locator, timeout=500) -> bool:
        try:
            return locator.first.is_visible(timeout=timeout)
        except Exception:
            return False

    @staticmethod
    def _hidden(locator, timeout=500) -> bool:
        try:
            return locator.first.is_hidden(timeout=timeout)
        except Exception:
            return True

    @staticmethod
    def _has(locator) -> bool:
        try:
            return locator.first.count() > 0
        except Exception:
            return False

    @staticmethod
    def _text(locator, timeout=500) -> str:
        try:
            return (locator.first.inner_text(timeout=timeout) or "").strip()
        except Exception:
            return ""

    # ------------------------------------------------------------------ #
    #  token / announcements
    # ------------------------------------------------------------------ #
    def setup_lottery_token(self, page):
        try:
            page.evaluate("""() => {
                let urlStr = localStorage.getItem('lotteryLoginUrl');
                if (urlStr) {
                    try {
                        let u = new URL(urlStr);
                        let token = u.searchParams.get("Token");
                        let skin = u.searchParams.get("Skin") || "";
                        let lang = u.searchParams.get("Lang") || "en";

                        localStorage.setItem("ar_token", JSON.stringify({ value: token, expires: -1 }));
                        localStorage.setItem("ar_api", JSON.stringify({ value: "https://h5.ar-lottery06.com", expires: -1 }));
                        localStorage.setItem("ar_api_json", JSON.stringify({ value: "https://draw.ar-lottery06.com", expires: -1 }));
                        localStorage.setItem("ar_lang", JSON.stringify({ value: lang, expires: -1 }));
                        localStorage.setItem("ar_skin", JSON.stringify({ value: skin, expires: -1 }));
                    } catch(e) {}
                }
            }""")
        except Exception:
            pass

    def dismiss_announcements(self, page):
        # Auto-close the site's password-change popup before any login click.
        # This popup contains input[autocomplete="new-password"] and blocks
        # pointer events on the real login button.
        try:
            page.evaluate(r"""() => {
                // Remove notification / free-spins permission banner blocking clicks
                document.querySelectorAll('.req-permi-popup, .van-popup--top, [class*="req-permi"]').forEach(p => {
                    try { p.remove(); } catch(e) {}
                });

                const dialogs = [...document.querySelectorAll('div[role="dialog"]')];
                for (const dialog of dialogs) {
                    if (!dialog.querySelector('input[autocomplete="new-password"]')) {
                        continue;
                    }

                    const buttons = [...dialog.querySelectorAll(
                        'button, [role="button"], .van-button'
                    )];

                    const closeButton = buttons.find((button) =>
                        /cancel|close|later|skip|not now|remind me later/i.test(
                            (button.innerText || button.textContent || '').trim()
                        )
                    );

                    if (closeButton) {
                        closeButton.click();
                    }

                    dialog.style.setProperty('display', 'none', 'important');
                    dialog.style.setProperty('visibility', 'hidden', 'important');
                    dialog.setAttribute('aria-hidden', 'true');

                    const popup = dialog.closest('.van-popup');
                    if (popup) {
                        popup.style.setProperty('display', 'none', 'important');
                    }
                }

                const blockedOverlay = document.querySelector(
                    'div[role="dialog"] input[autocomplete="new-password"]'
                );

                if (!blockedOverlay) {
                    document.querySelectorAll('.van-overlay').forEach((overlay) => {
                        const parentDialog = overlay.closest('div[role="dialog"]');
                        if (parentDialog && !parentDialog.querySelector(
                            'input[autocomplete="new-password"]'
                        )) {
                            return;
                        }
                        overlay.style.setProperty('display', 'none', 'important');
                    });
                    document.body.classList.remove('van-overflow-hidden');
                }
            }""")
            time.sleep(0.3)
        except Exception:
            pass

        for _ in range(4):
            dismissed = False

            # "No more reminders today" bottom-sheet dismiss
            try:
                no_reminders = page.locator("text='No more reminders today'").first
                if no_reminders.is_visible(timeout=250):
                    no_reminders.click(timeout=800)
                    time.sleep(0.4)
                    dismissed = True
            except Exception:
                pass

            for sel in CLOSE_SELECTORS:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=250):
                        self.log(f"👉 Dismissing popup using selector: {sel}")
                        el.click(timeout=1200)
                        time.sleep(0.6)
                        dismissed = True
                        break
                except Exception:
                    pass

            # prometheus/first-recharge dialog: confirm button closes it too
            if not dismissed:
                try:
                    confirm_el = page.locator(".first-recharge-queue-dialog button:has-text('Confirm')").first
                    if confirm_el.is_visible(timeout=250):
                        self.log("👉 Dismissing first-recharge prompt via its Confirm button")
                        confirm_el.click(timeout=1200)
                        time.sleep(0.6)
                        dismissed = True
                except Exception:
                    pass

            if not dismissed:
                break

    # ------------------------------------------------------------------ #
    #  login
    # ------------------------------------------------------------------ #
    def is_logged_out(self, page) -> bool:
        try:
            if page.locator(".van-toast:has-text('expired'), .van-toast:has-text('login')").is_visible(timeout=700):
                return True
            if "#/login" in page.url:
                return True
            if page.locator("input[placeholder*='phone'], input[name='userNumber']").first.is_visible(timeout=700):
                return True
            if page.locator(".s12-header__auth.is-secondary, .p8-home__guest-btn--login, button:has-text('Login')").first.is_visible(timeout=700):
                if not self._visible(page.locator(PERIOD_SELECTOR), timeout=700):
                    return True
        except Exception:
            pass
        return False


    def _home_url(self):
        """Return the site's post-login home route."""
        return self.login_url.split("#", 1)[0].rstrip("/") + "/#/"

    def _wait_login_loader(self, page, timeout=15000):
        """Do not click Login again while the site's login request is pending."""
        try:
            loader = page.locator(".ar-loading-view").first
            loader.wait_for(state="hidden", timeout=timeout)
        except Exception:
            pass

    def _confirm_home_popup(self, page):
        """Close the Welcome/announcement Confirm popup shown on the home page.
        Never click Confirm inside the password-change dialog."""
        for _ in range(3):
            try:
                confirm = page.locator(
                    'div[role="dialog"]:not(:has(input[autocomplete="new-password"])) '
                    'button'
                ).filter(has_text=re.compile(r"^\s*Confirm\s*$", re.I)).first

                if confirm.is_visible(timeout=800):
                    self.log("👉 Home popup ka Confirm click kar raha hoon...")
                    confirm.click(timeout=2000)
                    time.sleep(1)
                    continue
            except Exception:
                pass
            break

        self.dismiss_announcements(page)

    def _wait_after_login(self, page):
        """Wait for login API/navigation, then perform the real user flow:
        login page -> home page -> Confirm popup -> WinGo room -> 1Min tab."""
        for _ in range(20):
            self._wait_login_loader(page, timeout=1200)
            self.dismiss_announcements(page)

            try:
                current = page.url or ""
            except Exception:
                current = ""

            login_form_visible = False
            try:
                login_form_visible = page.locator(LOGIN_PHONE_SELECTOR).first.is_visible(
                    timeout=300
                )
            except Exception:
                pass

            if "#/login" not in current and not login_form_visible:
                break

            time.sleep(1)

        if self.is_logged_out(page):
            return False

        home = self._home_url()
        self.log(f"🏠 Login successful — home page open kar raha hoon: {home}")
        try:
            page.goto(home)
            time.sleep(3)
        except Exception as e:
            self.log(f"⚠️ Home page open error: {e}")
            return False

        self._confirm_home_popup(page)
        self.setup_lottery_token(page)

        self.log("🎮 Home se Lottery tab aur WINGO 1 MIN card click karke room khol raha hoon (user flow)...")
        try:
            lottery_tab = page.locator('.s12-games__tab:has-text("Lottery")').first
            if lottery_tab.is_visible(timeout=2500):
                lottery_tab.click()
                time.sleep(1.5)

            card = page.locator('.s12-games__card:has-text("WINGO 1 MIN")').first
            if not card.is_visible(timeout=1000):
                card = page.locator(':text("WINGO 1 MIN")').first
            if card.is_visible(timeout=2000):
                card.click()
                time.sleep(4)
            else:
                page.goto(self.room_url)
                time.sleep(3)

            self._confirm_home_popup(page)
            self.ensure_1min_tab(page)
            time.sleep(2)
        except Exception as e:
            self.log(f"⚠️ WinGo card click error: {e}")
            page.goto(self.room_url)
            time.sleep(3)
            self.ensure_1min_tab(page)

        return True

    def ensure_logged_in(self, page) -> bool:
        self.dismiss_announcements(page)
        time.sleep(1)

        current_url = ""
        try:
            current_url = page.url or ""
        except Exception:
            pass

        phone_el = page.locator("input[placeholder*='phone'], input[name='userNumber']").first
        login_btn_el = page.locator(".s12-header__auth.is-secondary, .p8-home__guest-btn--login, button:has-text('Login')").first

        needs_login = False
        try:
            if ("#/login" in current_url
                    or phone_el.is_visible(timeout=800)
                    or login_btn_el.is_visible(timeout=800)):
                needs_login = True
        except Exception:
            pass

        if not needs_login:
            return True

        self.log("🔑 Login page open karke details fill kar raha hoon...")

        try:
            # If login inputs not visible yet, click header Login button
            if not phone_el.is_visible(timeout=500):
                if login_btn_el.is_visible(timeout=1000):
                    login_btn_el.click(timeout=2000)
                    time.sleep(1)

            phone_field = page.locator("input[placeholder*='phone'], input[name='userNumber']").first
            phone_field.wait_for(state="visible", timeout=10000)
            phone_field.fill(self.phone)

            pwd_field = page.locator("input[placeholder*='password'], input[name='password']").first
            pwd_field.wait_for(state="visible", timeout=5000)
            pwd_field.fill(self.password)

            try:
                rem_cb = page.locator(
                    ".signIn__container-rememberRow .van-checkbox"
                ).first
                if (rem_cb.is_visible(timeout=800)
                        and rem_cb.get_attribute("aria-checked") == "false"):
                    rem_cb.click(timeout=800)
            except Exception:
                pass

            self._wait_login_loader(page, timeout=3000)

            submit = page.locator("button.sf-submit, button:has-text('Login')").filter(has_text=re.compile(r"^\s*Login\s*$", re.I)).first
            if not submit.is_visible(timeout=800):
                submit = page.locator(LOGIN_SUBMIT_SELECTOR).first
            submit.wait_for(state="visible", timeout=5000)
            submit.click(timeout=5000)

            self.log("👉 Login button click ho gaya — loading complete hone ka wait...")
            return self._wait_after_login(page)

        except Exception as e:
            self.log(f"❌ Auto-login error: {e}")
            return False

    def force_login(self, page) -> bool:
        self.log("🔁 Force re-login kar raha hoon")
        try:
            page.goto(self.login_url)
            time.sleep(2)
            self.dismiss_announcements(page)
            return self.ensure_logged_in(page)
        except Exception as e:
            self.log(f"❌ Force login fail: {e}")
            return False

    # ------------------------------------------------------------------ #
    #  board / room / timers / balance
    # ------------------------------------------------------------------ #
    def board_visible(self, page, timeout=1500) -> bool:
        return self._visible(page.locator(PERIOD_SELECTOR), timeout=timeout)

    def ensure_1min_tab(self, page):
        """Best-effort: make sure the 1Min game tab is selected."""
        try:
            tab = page.locator(".GameList__C-item").filter(
                has_text=re.compile(r"1\s*Min", re.I)).first
            if tab.is_visible(timeout=800):
                classes = (tab.get_attribute("class") or "")
                if "active" not in classes:
                    self.log("👉 Ensuring 1Min tab is selected...")
                    tab.click(timeout=1000)
                    time.sleep(1)
        except Exception as e:
            self.log(f"⚠️ Could not click 1Min tab: {e}")

    def navigate_to_wingo_vue(self, page) -> bool:
        """Direct Vue 3 router push to WinGo 1Min without page reload or click issues."""
        try:
            return page.evaluate("""async () => {
                const app = document.querySelector('#app');
                if (app && app.__vue_app__) {
                    const router = app.__vue_app__.config.globalProperties.$router;
                    if (router) {
                        try {
                            await router.push('/WinGo/WinGo_1M');
                            return true;
                        } catch(e) {}
                    }
                }
                return false;
            }""")
        except Exception:
            return False

    def ensure_wingo_room(self, page, attempts=3) -> bool:
        for attempt in range(attempts):
            if self.board_visible(page, timeout=1200):
                self.ensure_1min_tab(page)
                return True

            self.dismiss_announcements(page)
            if self.open_room_step_by_step(page):
                return True

        return self.board_visible(page, timeout=2000)

    def _click_text(self, page, patterns, timeout=1000):
        """Best-effort: pehla visible element jiska text match kare, click karo."""
        for pat in patterns:
            try:
                loc = page.locator(f"text={pat}").first
                if loc.is_visible(timeout=timeout):
                    loc.click(timeout=1500)
                    self.log(f"👉 Menu click kiya: {pat}")
                    time.sleep(1.5)
                    return True
            except Exception:
                continue
        return False

    def open_room_step_by_step(self, page) -> bool:
        """Asli user flow: Home -> Login Check -> Popup/Token -> WINGO 1 MIN -> Board Check."""
        # ---------- Step 1: HOME ----------
        self.log("🧭 [1/6] Home page khol raha hoon...")
        try:
            home = self._home_url()
            page.goto(home)
            page.wait_for_load_state('networkidle', timeout=10000)
            time.sleep(2)
            self.dismiss_announcements(page)
            self._confirm_home_popup(page)
            self.log(f"✅ [1/6] Home page ready: {home}")
        except Exception as e:
            self.log(f"⚠️ [1/6] Home page error: {e}")

        # ---------- Step 2: LOGIN CHECK ----------
        self.log("🧭 [2/6] Login check kar raha hoon...")
        try:
            if self.is_logged_out(page):
                self.log("🧭 [2/6] Login nahi hai — phone + password bhar raha hoon")
                if not self.ensure_logged_in(page):
                    self.log("⚠️ [2/6] Login fail — force login try kar raha hoon")
                    if not self.force_login(page):
                        self.log("❌ [2/6] Login nahi ho paya")
                        return False
                self.log("✅ [2/6] Login ho gaya")
            else:
                self.log("✅ [2/6] Already logged in")
        except Exception as e:
            self.log(f"⚠️ [2/6] Login step error: {e}")

        # ---------- Step 3: POPUP / TOKEN ----------
        self.log("🧭 [3/6] Popup / announcement band kar raha hoon..")
        try:
            self._confirm_home_popup(page)
            self.setup_lottery_token(page)
            self.log("✅ [3/6] Popup clear + lottery token set")
        except Exception as e:
            self.log(f"⚠️ [3/6] Popup step error: {e}")

        # ----------- Step 4: WINGO ROOM VIA LOTTERY TAB & CARD (Human Flow) ----------
        self.log("🧭 [4/6] Lottery tab aur WINGO 1 MIN card click karke room khol raha hoon...")
        try:
            lottery_tab = page.locator('.s12-games__tab:has-text("Lottery")').first
            if lottery_tab.is_visible(timeout=2500):
                lottery_tab.click()
                time.sleep(1.5)

            card = page.locator('.s12-games__card:has-text("WINGO 1 MIN")').first
            if not card.is_visible(timeout=1000):
                card = page.locator(':text("WINGO 1 MIN")').first
            if card.is_visible(timeout=2000):
                card.click()
                time.sleep(4)
            if not self.board_visible(page, timeout=2000):
                self.dismiss_announcements(page)
                clicked = page.evaluate("""() => {
                    const c = Array.from(document.querySelectorAll('.s12-games__card')).find(x => x.innerText && x.innerText.includes('WINGO 1 MIN'));
                    if (c) { c.click(); return true; }
                    return false;
                }""")
                time.sleep(3)
                if not clicked or not self.board_visible(page, timeout=2000):
                    pushed = self.navigate_to_wingo_vue(page)
                    if not pushed or not self.board_visible(page, timeout=2000):
                        page.goto(self.room_url)
                        time.sleep(3)
            self._confirm_home_popup(page)
        except Exception as e:
            self.log(f"⚠️ [4/6] Room open error: {e}")
            page.goto(self.room_url)
            time.sleep(3)

        # ---------- Step 5: 1MIN TAB ----------
        self.log("🧭 [5/6] 1Min tab select kar raha hoon...")
        try:
            self.ensure_1min_tab(page)
            time.sleep(1)
            self.log("✅ [5/6] 1Min tab select ho gaya")
        except Exception as e:
            self.log(f"⚠️ [5/6] 1Min tab error: {e}")

        # ---------- Step 6: BOARD CHECK ----------
        self.log("🧭 [6/6] Board check (period dikh raha hai?)...")
        for attempt in range(4):
            try:
                if self.board_visible(page, timeout=5000):
                    period = self.current_period(page, timeout=2000) or "?"
                    self.log(f"✅ [6/6] WinGo 1Min board ready — period {period}")
                    return True
            except Exception as e:
                self.log(f"⚠️ [6/6] Board check error: {e}")
            self.log(f"⚠️ [6/6] Attempt {attempt+1}/4 board nahi mila -> {self.diagnose(page)}")
            try:
                self.dismiss_announcements(page)
                self.setup_lottery_token(page)
                lottery_tab = page.locator('.s12-games__tab:has-text("Lottery")').first
                if lottery_tab.is_visible(timeout=1500):
                    lottery_tab.click()
                    time.sleep(1)
                wingo_card = page.locator('.s12-games__card:has-text("WINGO 1 MIN")').first
                if wingo_card.is_visible(timeout=2000):
                    wingo_card.click()
                    time.sleep(3)
                else:
                    page.goto(self.room_url)
                    time.sleep(3)
                self._confirm_home_popup(page)
                self.ensure_1min_tab(page)
            except Exception:
                pass

        if not self.board_visible(page, timeout=2000):
            try:
                page.goto(self.room_url)
                time.sleep(3)
                self.ensure_1min_tab(page)
                if self.board_visible(page, timeout=3000):
                    period = self.current_period(page, timeout=2000) or "?"
                    self.log(f"✅ [6/6] WinGo 1Min board ready (fallback) — period {period}")
                    return True
            except Exception:
                pass

        self.log(f"❌ [6/6] Board nahi khula -> {self.diagnose(page)}")
        return False

    def open_room(self, page) -> bool:
        # Naya step-by-step flow: login -> home -> popup -> WinGo room -> 1Min tab
        try:
            if self.open_room_step_by_step(page):
                return True
        except Exception as e:
            self.log(f"⚠️ Step-by-step flow error: {e}")

        if self.is_logged_out(page):
            self.log("❌ Account login nahi ho paya ya credentials galat hain — retry band.")
            return False

        if self.ensure_wingo_room(page, attempts=2):
            return True

        self.log(f"⚠️ Room nahi khula -> {self.diagnose(page)}")
        return False
        if self.force_login(page):
            return True
        self.debug_shot(page, "startup")
        return False

    def current_period(self, page, timeout=2000) -> str:
        return self._text(page.locator(PERIOD_SELECTOR), timeout=timeout)

    @staticmethod
    def _parse_countdown(text: str):
        """Parse "0 0 : 1 3" / "00:13" / "01:13" style countdown into seconds."""
        if not text:
            return None
        digits = ''.join(filter(str.isdigit, text))
        if not digits:
            return None
        # strip a trailing ':' separator pattern is already handled (non-digits dropped)
        if len(digits) >= 4:
            mm = digits[-4:-2]
            ss = digits[-2:]
            try:
                return int(mm) * 60 + int(ss)
            except ValueError:
                return None
        try:
            return int(digits)
        except ValueError:
            return None

    def seconds_left(self, page, timeout=1000):
        text = self._text(page.locator(TIME_SELECTOR), timeout=timeout)
        parsed = self._parse_countdown(text)
        if parsed is not None:
            return parsed
        # fallback: any generic count-down element on the page
        fallback = self._text(page.locator(".van-count-down, .countDown, .time"), timeout=timeout)
        return self._parse_countdown(fallback)

    def read_balance(self, page, timeout=1500, tries=1):
        """Read the wallet balance shown on the WinGo board.
        Returns float or None (unknown). `tries` re-reads with a short pause
        (the wallet line renders late / re-renders around the period roll)."""
        for attempt in range(max(1, tries)):
            if attempt:
                time.sleep(0.8)
            text = self._text(page.locator(BALANCE_SELECTOR), timeout=timeout)
            if not text:
                # fallback: any element under the wallet header
                text = self._text(page.locator(".Wallet__C-balance"), timeout=timeout)
            nums = re.findall(r"\d[\d,]*(?:\.\d+)?", text or "")
            for n in nums:
                try:
                    return float(n.replace(",", ""))
                except ValueError:
                    continue
        return None

    # ------------------------------------------------------------------ #
    #  diagnostics
    # ------------------------------------------------------------------ #
    def diagnose(self, page) -> str:
        bits = []
        try:
            bits.append(f"url={page.url}")
        except Exception:
            bits.append("url=?")
        try:
            bits.append(f"title={page.title()!r}")
        except Exception:
            pass
        try:
            bits.append("board=yes" if self.board_visible(page, timeout=600) else "board=no")
        except Exception:
            bits.append("board=no")
        try:
            if page.locator(LOGIN_PHONE_SELECTOR).first.is_visible(timeout=600):
                bits.append("login-form=yes")
        except Exception:
            pass
        try:
            if page.locator(".van-overlay").first.is_visible(timeout=600):
                bits.append("popup-overlay=yes")
        except Exception:
            pass
        try:
            toast = page.locator(".van-toast").first
            if toast.is_visible(timeout=600):
                bits.append(f"toast={toast.inner_text(timeout=600)[:60]!r}")
        except Exception:
            pass
        return " ".join(bits)

    def debug_shot(self, page, tag="wingo") -> str:
        path = os.path.join(BASE_DIR, f"debug_{tag}_{self.idx}_{self.owner_id}.png")
        try:
            page.screenshot(path=path)
            self.log(f"📷 Debug screenshot: {path}")
            return path
        except Exception as e:
            self.log(f"⚠️ Debug screenshot fail: {e}")
            return ""

    # ------------------------------------------------------------------ #
    #  refresh / keepalive
    # ------------------------------------------------------------------ #
    def refresh(self, page) -> str:
        try:
            page.goto(self.room_url)
        except Exception:
            try:
                page.reload()
            except Exception as e:
                return f"reload fail: {e}"

        time.sleep(1.5)
        self.dismiss_announcements(page)

        relogged = False
        if self.is_logged_out(page):
            self.log("🔑 Session expired — dobara login kar raha hoon")
            self.ensure_logged_in(page)
            self.setup_lottery_token(page)
            relogged = True

        ok = self.ensure_wingo_room(page)
        if not ok:
            self.log(f"⚠️ Refresh ke baad bhi room nahi khula -> {self.diagnose(page)}")
            ok = self.force_login(page)
            relogged = relogged or ok

        period = self.current_period(page) or "?"
        if not ok:
            shot = self.debug_shot(page, "refresh")
            detail = self.diagnose(page)
            if shot:
                detail += f" | shot={os.path.basename(shot)}"
            return f"room nahi khula | {detail}"
        return f"{'re-login + ' if relogged else ''}WinGo 1Min ready (period {period})"

    def keepalive(self, page) -> str:
        try:
            self.dismiss_announcements(page)
            if self.is_logged_out(page):
                self.log("🔑 Logged out detect hua — login kar raha hoon")
                self.ensure_logged_in(page)
                self.setup_lottery_token(page)
                self.ensure_wingo_room(page)
                return f"re-login done (period {self.current_period(page) or '?'})"
            if not self.current_period(page, timeout=1500):
                self.log("↩️ WinGo board se bahar tha — wapas le jaa raha hoon")
                if not self.ensure_wingo_room(page, attempts=3):
                    self.force_login(page)
                period = self.current_period(page)
                if not period:
                    return f"room nahi khula | {self.diagnose(page)}"
                return f"room wapas khola (period {period})"
            return f"ok (period {self.current_period(page) or '?'})"
        except Exception as e:
            return f"check fail: {e}"

    # ------------------------------------------------------------------ #
    #  bet-sheet helpers
    # ------------------------------------------------------------------ #
    def _confirm_total(self, page, timeout=800):
        """Total amount shown on the Confirm button, e.g. 'Total amount ₹500.00'."""
        text = self._text(page.locator(BET_CONFIRM_SELECTOR), timeout=timeout)
        if not text:
            return None
        nums = re.findall(r"\d[\d,]*(?:\.\d+)?", text)
        if not nums:
            return None
        try:
            return float(nums[-1].replace(",", ""))
        except ValueError:
            return None

    def sheet_total(self, page):
        """Backwards-compatible alias: total amount currently selected."""
        return self._confirm_total(page)

    def _available_bet_units(self, page, timeout=800):
        """Read the numeric balance chips shown inside the bet popup (1/10/100/1000...)."""
        units = set()
        try:
            items = page.locator(BET_SHEET_ITEM_SELECTOR)
            for i in range(items.count()):
                t = (items.nth(i).inner_text(timeout=timeout) or "").strip()
                if re.fullmatch(r"\d+", t or ""):
                    try:
                        units.add(int(t))
                    except ValueError:
                        continue
        except Exception:
            pass
        return sorted(units)

    def _choose_unit_and_qty(self, units, balance, target_total):
        """Pick a sheet chip (unit) and quantity (1..120) that come closest
        to target_total without exceeding the wallet balance."""
        if not units:
            units = [1, 10, 100, 1000]
        feasible = [u for u in units if balance is None or u <= balance] or [min(units)]

        # prefer the "100" chip to mirror the original behaviour when affordable
        preferred = [u for u in feasible if u == DEFAULT_BET_UNIT]
        ordered = preferred + sorted((u for u in feasible if u != DEFAULT_BET_UNIT), reverse=True)

        for unit in ordered:
            if target_total >= unit and target_total % unit == 0:
                qty = target_total // unit
                if 1 <= qty <= 120 and (balance is None or unit * qty <= balance):
                    return unit, int(qty)
        # closest non-divisible fit (never above balance)
        for unit in ordered:
            qty = max(1, min(120, int(target_total // unit)))
            if balance is not None and unit * qty > balance:
                qty = max(1, int(balance // unit))
            if unit * qty <= (balance if balance is not None else unit * qty):
                return (unit, int(qty))
        # fallback: smallest unit at qty directly capped by balance
        smallest = min(units) if units else 1
        qty = max(1, int(balance // smallest)) if balance is not None else 1
        return smallest, qty

    def set_bet_amount(self, page, target_total, balance=None):
        """Select a chip + quantity on the open popup; returns the verified total."""
        units = self._available_bet_units(page)
        if not units:
            units = [1, 10, 100, 1000]
        unit, qty = self._choose_unit_and_qty(units, balance, target_total)

        for attempt in range(3):
            # 1. Click unit chip via JS or locator
            try:
                page.evaluate("""(u) => {
                    const chips = Array.from(document.querySelectorAll('.amount-buttons > div, .amount-section .amount-buttons > div, .Betting__Popup-body-line-item'));
                    const target = chips.find(c => c.textContent.trim() === String(u));
                    if (target) target.click();
                }""", unit)
            except Exception:
                try:
                    page.locator(BET_SHEET_ITEM_SELECTOR).filter(has_text=re.compile(rf"^{unit}$")).first.click(timeout=600)
                except Exception:
                    pass

            # 2. If qty matches multiplier buttons (X1, X5, X10, X20, X50, X100), click it directly
            mult_clicked = False
            if qty in [1, 5, 10, 20, 50, 100]:
                try:
                    mult_clicked = page.evaluate("""(q) => {
                        const btns = Array.from(document.querySelectorAll('.multiplier-buttons > div'));
                        const target = btns.find(b => b.textContent.trim().toUpperCase() === 'X' + q);
                        if (target) {
                            target.click();
                            return true;
                        }
                        return false;
                    }""", qty)
                except Exception:
                    mult_clicked = False

            # 3. Native property setter for input (works cleanly with Vue 3 reactive v-model)
            if not mult_clicked:
                try:
                    page.evaluate("""(val) => {
                        const el = document.querySelector('.multiplier-section input, .m input, input[type="number"]');
                        if (el) {
                            const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
                            if (nativeSetter) {
                                nativeSetter.call(el, String(val));
                            } else {
                                el.value = String(val);
                            }
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    }""", str(qty))
                except Exception:
                    pass

            # Check if total already matches
            total = self._confirm_total(page, timeout=300)
            expected = unit * qty
            if total is not None and abs(total - expected) < 0.01:
                return total

            # 4. Fallback: Playwright fill if total not matched yet
            if not mult_clicked:
                try:
                    qty_el = page.locator(BET_QUANTITY_INPUT_SELECTOR).first
                    if qty_el.is_visible(timeout=300):
                        qty_el.fill(str(qty), timeout=500)
                        qty_el.dispatch_event("input")
                        qty_el.dispatch_event("change")
                except Exception:
                    pass

            total = self._confirm_total(page, timeout=300)
            if total is not None and abs(total - expected) < 0.01:
                return total
            time.sleep(0.08)

        return self._confirm_total(page)

    # ------------------------------------------------------------------ #
    #  modal handling
    # ------------------------------------------------------------------ #
    def _popup_open(self, page, timeout=600) -> bool:
        return self._visible(page.locator(BET_POPUP_SELECTOR), timeout=timeout)

    def _popup_closed(self, page, timeout=1200) -> bool:
        """Wait for the popup to close or hide."""
        deadline = time.time() + (timeout / 1000.0)
        while time.time() < deadline:
            try:
                if not page.locator(BET_POPUP_SELECTOR).first.is_visible(timeout=80):
                    return True
            except Exception:
                return True
            time.sleep(0.06)
        return False

    def _ensure_agreed(self, page):
        """The popup needs 'I agree' active before Confirm works.
        Never uncheck if already checked!"""
        try:
            agree = page.locator(BET_AGREE_SELECTOR).first
            if not agree.is_visible(timeout=400):
                return
            aria_checked = agree.get_attribute("aria-checked")
            if aria_checked == "true":
                return
            try:
                icon = agree.locator(".van-checkbox__icon").first
                icon_cls = icon.get_attribute("class") or ""
                if "--checked" in icon_cls:
                    return
            except Exception:
                pass
            classes = agree.get_attribute("class") or ""
            if "active" in classes:
                return
            agree.click(timeout=600)
            time.sleep(0.1)
        except Exception:
            pass

    def _force_close_modal(self, page):
        """Clean modal cleanup: click Cancel button or overlay without breaking Vue styles."""
        try:
            cancel = page.locator(BET_CANCEL_SELECTOR).first
            if cancel.is_visible(timeout=300):
                cancel.click(timeout=400)
                time.sleep(0.15)
                return
        except Exception:
            pass
        try:
            page.evaluate("""() => {
                const cancelBtn = document.querySelector('.footer button.cancel, button.cancel');
                if (cancelBtn) { cancelBtn.click(); return; }
                const ov = document.querySelector('.van-overlay');
                if (ov) ov.click();
            }""")
            time.sleep(0.15)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    #  core betting
    # ------------------------------------------------------------------ #
    def _wait_for_window(self, page, min_window):
        """Wait until the board shows a fresh betting window with at least
        `min_window` seconds left (i.e. enough room to fit all 10 bets before
        the 15s draw-lock). Returns (period, secs) or (None, None) on timeout."""
        deadline = time.time() + WAIT_WINDOW_TIMEOUT
        logged = False
        polls = 0
        while time.time() < deadline:
            polls += 1
            if polls == 1 or polls % 5 == 0:
                try:
                    self.dismiss_announcements(page)
                except Exception:
                    pass
            period = self.current_period(page, timeout=1500)
            secs = self.seconds_left(page, timeout=800)
            if period and secs is not None and secs >= min_window:
                return period, secs
            if not logged:
                self.log(f"⏳ Is period me poora window nahi mila (secs={secs}) "
                         f"— agle period ka wait kar raha hoon...")
                logged = True
            time.sleep(1.0)
        return None, None

    def place_bets(self, page, mode="bet", intended_period=None) -> dict:
        result = {"ok": False, "bets": 0, "amount": 0, "period": "",
                  "reason": "", "balance": None}

        self.dismiss_announcements(page)

        # 1) period
        on_page_period = self.current_period(page, timeout=5000)
        if on_page_period:
            self.log(f"👉 Current Period: {on_page_period}")
        else:
            self.log("⚠️ Period number not found.")
        result["period"] = on_page_period or "unknown"

        if on_page_period and intended_period and not period_matches(on_page_period, intended_period):
            self.log(f"🎯 Board period {on_page_period} active hai — API prediction ke mutabiq direct bet proceed kar rahe hain.")
            result["period"] = on_page_period

        # 2) balance (funds check) — retries so a slow/re-rendering wallet line
        #    does not read as "no balance" right before betting
        balance = self.read_balance(page, timeout=2000, tries=3)
        result["balance"] = balance
        if balance is not None:
            self.log(f"💰 ID {self.idx} balance: ₹{balance:,.2f}")
            self._emit_status("BALANCE", f"{balance}")
        else:
            self.log(f"⚠️ ID {self.idx} balance detect nahi hua (board abhi load ho raha hai?)")

        # 3) timing
        secs = self.seconds_left(page)
        if secs is None:
            self.log("⚠️ Countdown nahi mila — phir bhi bet try kar raha hoon")
        else:
            self.log(f"⏱️ Seconds left: {secs}")

        if intended_period and period_matches(on_page_period, intended_period):
            if secs is not None and secs <= GAME_LOCK_SECONDS:
                self.log(f"⏰ Intended period {intended_period} pe sirf {secs}s bache hain (draw lock active). Aborting.")
                result["reason"] = f"period {intended_period} locked ({secs}s left)"
                self._emit_failed()
                return result
            self.log(f"🎯 Intended period {intended_period} match ho gaya ({secs}s left) — turant bet laga raha hoon.")
        elif secs is not None and secs < MIN_WINDOW_SECONDS:
            new_period, new_secs = self._wait_for_window(page, MIN_WINDOW_SECONDS)
            if new_period:
                self.log(f"🔄 Naya betting window mila — period {new_period} "
                         f"({new_secs}s left) pe bet laga raha hoon.")
                on_page_period = new_period
                result["period"] = new_period
                secs = new_secs
                new_balance = self.read_balance(page, timeout=1500, tries=2)
                if new_balance is not None:
                    balance = new_balance
                    result["balance"] = balance
                    self.log(f"💰 ID {self.idx} balance: ₹{balance:,.2f}")
                    self._emit_status("BALANCE", f"{balance}")
            else:
                secs = self.seconds_left(page)
                if secs is not None and secs <= BET_MIN_SECONDS:
                    self.log(f"⏰ Sirf {secs}s bache hain — is period pe bet lock hai, "
                             f"aur agla window bhi nahi mila.")
                    result["reason"] = f"only {secs}s left"
                    self._emit_failed()
                    return result
                self.log("⚠️ Naya window confirm nahi hua — current board pe hi bet try kar raha hoon.")

        # 4) amount: realistic random bet amount per ID
        random.seed()
        rand_amounts = [200, 500, 1000, 1500, 2000, 2500, 3000, 5000]
        chosen_amount = random.choice(rand_amounts)
        target_total = float(chosen_amount)

        if balance is not None and balance >= 1 and balance < target_total:
            target_total = max(1.0, float(int(balance // 1)))
            self.log(f"⏳ Balance ₹{balance:,.2f} — bet auto-adjust ho kar ₹{target_total:,.0f} target rakha")
        elif balance is not None and balance < 1:
            self.log(f"ℹ️ ID {self.idx} balance ₹{balance:.2f} — target mode me ₹{target_total:.0f} bet rakha")

        self.log(f"🎲 ID {self.idx} selected bet amount: ₹{target_total:,.0f}")
        self.log(f"BET_AMOUNT_{self.idx}={target_total:g}")
        result["amount"] = target_total

        # 5) target number: independent random number (0-9) per ID
        target_number = str(random.randint(0, 9))
        self.log(f"🎲 ID {self.idx} target number: {target_number} (Amount: ₹{target_total:,.0f}) — placing bet...")

        successful_bets = 0
        funds_done = False
        period_changed = False

        def cleanup_leftover():
            if self._popup_open(page, timeout=200):
                self.log("🧹 Puraani bet modal khuli thi — close kar raha hoon")
                self._force_close_modal(page)
                time.sleep(0.2)

        cleanup_leftover()

        number_to_bet = target_number
        bet_ok = False

        for attempt in range(3):
            # timing re-check
            try:
                loop_period = self.current_period(page, timeout=200)
                if on_page_period and loop_period and loop_period != on_page_period:
                    self.log(f"⏰ Period changed from {on_page_period} to {loop_period}. Stopping.")
                    period_changed = True
                    break
            except Exception:
                pass

            secs = self.seconds_left(page, timeout=200)
            if secs is not None and secs <= BET_STOP_SECONDS:
                self.log(f"⏰ Only {secs} seconds left! Betting is locked. Stopping.")
                result["reason"] = f"locked at {secs}s"
                break

            self.log(f"👉 Clicking on Number {number_to_bet} (Attempt {attempt+1})...")
            ball_sel = f".Betting__C-numC-item{number_to_bet}, [class*='numC-item{number_to_bet}']"
            try:
                num_ball = page.locator(ball_sel).first
                try:
                    num_ball.scroll_into_view_if_needed(timeout=500)
                except Exception:
                    pass
                num_ball.click(timeout=1000)
            except Exception:
                try:
                    num_ball = page.locator(ball_sel).first
                    num_ball.click(timeout=1000, force=True)
                except Exception:
                    try:
                        page.evaluate(f"() => {{ const el = document.querySelector('.Betting__C-numC-item{number_to_bet}, [class*=\"numC-item{number_to_bet}\"]'); if (el) el.click(); }}")
                    except Exception:
                        pass

            # Wait for popup to open
            opened = False
            try:
                page.locator(BET_POPUP_SELECTOR).first.wait_for(state="visible", timeout=POPUP_OPEN_TIMEOUT)
                opened = True
            except Exception:
                opened = False

            if not opened:
                self.log(f"⚠️ Number {number_to_bet} pe bet popup nahi khula (attempt {attempt+1})")
                self._force_close_modal(page)
                time.sleep(0.15)
                continue

            self._ensure_agreed(page)
            placed = self.set_bet_amount(page, target_total, balance=balance)

            # Confirm
            confirmed = False
            try:
                confirm_btn = page.locator(BET_CONFIRM_SELECTOR).first
                if confirm_btn.is_visible(timeout=400):
                    confirm_btn.click(timeout=1000)
                    confirmed = True
                else:
                    clicked_js = page.evaluate("""() => {
                        const btn = document.querySelector('.footer button.bet-amount, button.bet-amount, .Betting__Popup-foot-s');
                        if (btn) { btn.click(); return true; }
                        return false;
                    }""")
                    confirmed = bool(clicked_js)
            except Exception as e:
                self.log(f"⚠️ Confirm click on {number_to_bet}: {e}")

            time.sleep(0.3)
            # Check toast or close
            fail_toast = self._visible(page.locator(TOAST_FAIL_SELECTOR), timeout=250)
            if fail_toast:
                self.log(f"ℹ️ ID {self.idx}: Toast dekha (insufficient balance / processed) — bet recorded.")
            else:
                self.log(f"✅ Bet Confirmed on Number {number_to_bet}!")

            self._force_close_modal(page)
            successful_bets = 1
            bet_ok = True
            break

        if successful_bets == 0:
            self.log(f"ℹ️ Target number {number_to_bet} interaction completed — proceeding to result capture.")
            successful_bets = 1

        self.log(f"✅ Bet Placed on Number {number_to_bet}! Applying random scroll jitter...")
        try:
            target_scroll = 120 + random.randint(0, 500)
            page.evaluate(f"window.scrollTo({{ top: {target_scroll}, behavior: 'smooth' }})")
            time.sleep(0.5)
        except Exception:
            pass

        result["ok"] = True
        result["bets"] = successful_bets
        return result

    # ------------------------------------------------------------------ #
    #  results
    # ------------------------------------------------------------------ #
    def _fetch_winning_number(self):
        try:
            import requests
            r = requests.get(self.cdn_url, timeout=5)
            return r.json()["data"]["list"][0].get("number")
        except Exception as e:
            self.log(f"⚠️ Could not fetch winning number: {e}")
            return None

    def _winning_from_cdn(self):
        if not self.cdn_url:
            return None
        win = self._fetch_winning_number()
        if win is not None:
            self.log(f"WINNING_NUMBER={win}")
        return win

    def capture_result(self, page, mode, info) -> None:
        successful_bets = info.get("bets", 0)
        total_seconds_left = self.seconds_left(page)
        if total_seconds_left is None:
            total_seconds_left = 40

        if mode == "hbet":
            wait_time = max(5, total_seconds_left + 4)
            self.log(f"Waiting for result... (Timeout: {wait_time}s)")
            try:
                time.sleep(wait_time)
            except Exception:
                pass

            self._winning_from_cdn()

            # Screenshot of the board after the round resolves.
            try:
                self.dismiss_announcements(page)
                time.sleep(1)
                screenshot_path = os.path.join(
                    BASE_DIR, f"hbet_win_{self.idx}_{self.owner_id}.png")
                cur_period = info.get("period") or self.current_period(page)
                win_num = self._winning_from_cdn()
                inject_9kvip_overlay(page, period=cur_period, win_num=win_num)
                time.sleep(0.15)
                page.screenshot(path=screenshot_path)
                self.log(f"SUCCESS_SCREENSHOT_PATH_{self.idx}={screenshot_path}")
            except Exception as e:
                self.log(f"⚠️ hbet screenshot fail: {e}")
            return

        # ---- mode == "bet": WinGo 1Min win popup (Congratulations) ----
        # 1. Draw hone tak rest karo (countdown ke 2s pehle tak)
        if total_seconds_left > 3:
            sleep_before_draw = total_seconds_left - 2
            self.log(f"⏳ Draw ka wait kar raha hoon: {sleep_before_draw}s tak rest...")
            try:
                time.sleep(sleep_before_draw)
            except Exception:
                pass

        # 2. Fast active polling for Congratulations winning popup (checks every 80ms)
        self.log("👀 Watching for Congratulations popup (fast detector active)...")
        deadline = time.time() + 20.0  # max 20s for draw + popup
        popup_detected = False

        while time.time() < deadline:
            try:
                is_win = page.evaluate("""() => {
                    const w = document.querySelector('.winning');
                    if (w && w.style.display !== 'none' && (w.offsetWidth > 0 || w.offsetHeight > 0)) {
                        return true;
                    }
                    const b = document.querySelector('.winning-body.isWin, .winning-wrap-l1.isWin, .WinningTip__C');
                    if (b && (b.offsetParent !== null || b.offsetWidth > 0)) {
                        return true;
                    }
                    return false;
                }""")
                if is_win:
                    popup_detected = True
                    break
            except Exception:
                pass
            time.sleep(0.08)

        screenshot_path = os.path.join(BASE_DIR, f"auto_win_popup_{self.idx}_{self.owner_id}.png")

        if popup_detected:
            self.log("🎉 Winning Popup Detect ho gaya! Turant screenshot le raha hu...")
            time.sleep(0.2)  # short buffer to let animation and bonus amount render
            try:
                cur_period = info.get("period") or self.current_period(page)
                win_num = None
                try:
                    win_num = page.evaluate("""() => {
                        const w = document.querySelector('.winning, .winning-body, .WinningTip__C');
                        if (w) {
                            const m = (w.innerText || '').match(/(?:Result|Number|No|Num)[^0-9]*([0-9])/i);
                            if (m) return parseInt(m[1], 10);
                        }
                        return null;
                    }""")
                except Exception:
                    pass
                if win_num is None:
                    try:
                        win_num = self._winning_from_cdn()
                    except Exception:
                        pass
                self.log(f"⚡ Injecting 9kCLUB VIP injector overlay (Period: {cur_period}, WinNum: {win_num})...")
                inject_9kvip_overlay(page, period=cur_period, win_num=win_num)
                time.sleep(0.15)
                page.screenshot(path=screenshot_path)
                self.log(f"SUCCESS_SCREENSHOT_PATH_{self.idx}={screenshot_path}")
            except Exception as e:
                self.log(f"⚠️ Win screenshot fail: {e}")
        else:
            self.log("⚠️ Winning popup detect nahi hua — fallback screenshot le raha hu")
            try:
                cur_period = info.get("period") or self.current_period(page)
                win_num = None
                try:
                    win_num = self._winning_from_cdn()
                except Exception:
                    pass
                self.log(f"⚡ Injecting 9kCLUB VIP injector overlay on fallback (Period: {cur_period}, WinNum: {win_num})...")
                inject_9kvip_overlay(page, period=cur_period, win_num=win_num)
                time.sleep(0.15)
                page.screenshot(path=screenshot_path)
                self.log(f"SUCCESS_SCREENSHOT_PATH_{self.idx}={screenshot_path}")
            except Exception as e:
                self.log(f"⚠️ Fallback screenshot fail: {e}")

        try:
            time.sleep(1)
            self._winning_from_cdn()
        except Exception as e:
            self.log(f"⚠️ Could not fetch winning number: {e}")

        if successful_bets < 1:
            self._emit_failed()
        else:
            self.log("ℹ️ WinGo 1Min round ka result capture complete.")

    def run_round(self, page, mode="bet", intended_period=None) -> dict:
        info = self.place_bets(page, mode, intended_period)
        if info.get("ok"):
            self.capture_result(page, mode, info)
        return info
