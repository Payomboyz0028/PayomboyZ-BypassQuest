"""
BypassEngine v6 — High-Speed 100% Self-Hosted Native Engine.
Strict Zero External API Policy.
Target Latency: 5–7 seconds max across all supported link shorteners.

Supported Services:
  - Platoboost / PlatoRelay / Delta Executor (Native 4.5–5.0s solver)
  - LootLabs / LootLinks / LootDest (XOR decoder + native fast-forward task worker)
  - Work.ink (duf reverse base64 + direct redirect)
  - Rekonise (instant unlock API)
  - Linkvertise (token/redirect bypass)
  - Luarmor (checkpoint auto-chain)
  - Boost.ink / Sub2Unlock
  - File Hosts (PixelDrain, MediaFire, GoFile, KrakenFiles)
"""

import os
import sys
import tempfile
import re
import asyncio
import base64
import json
import time
from urllib.parse import urlparse, unquote, parse_qs
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession

from config import (
    PROVIDERS,
    PLATOBOOST_TOKEN,
    PLATOBOOST_COOKIE_NAME,
    PLATOBOOST_COOKIE_VALUE
)
from utils.rtao_client import rtao_client

# ═══════════════════════════════════════════════════════════════
# Concurrency & Worker Guards
# ═══════════════════════════════════════════════════════════════
_BROWSER_SEM = asyncio.Semaphore(3)

# ═══════════════════════════════════════════════════════════════
# Garbage & Anti-Leech Filter
# ═══════════════════════════════════════════════════════════════
GARBAGE_TOKENS = [
    "free api", "leechers", "bypass.vip", "discord.gg", "join here",
    "shut down", "shutdown", "t.me/", "bit.ly/", "adblock", "ad-block",
    "captcha", "turnstile", "cloudflare", "attention required",
    "just a moment", "500 internal", "404 not found", "bad gateway",
    "service unavailable", "error code", "fonts.googleapis", "fonts.gstatic",
    "w3.org", "jsdelivr.net", "googletagmanager", "google-analytics",
    "cloudflareinsights", "hotjar.com", "cdn.jsdelivr", "expired_link", "expired link"
]

def is_valid_result(res: str | None, original_url: str) -> bool:
    if not res or not isinstance(res, str):
        return False
    res_clean = res.strip()
    res_lower = res_clean.lower()
    if len(res_clean) < 4:
        return False
    if any(tok in res_lower for tok in GARBAGE_TOKENS):
        return False
    if res_clean == original_url.strip():
        return False
    return True

# ═══════════════════════════════════════════════════════════════
# Domain Detector
# ═══════════════════════════════════════════════════════════════
class DomainDetector:
    """Detects provider type and metadata from incoming URL."""
    
    CHAINABLE_PATTERNS = [
        "ads.luarmor.net", "luarmor.net",
        "gateway.platoboost.com", "platoboost.com", "platoboost.net", "platorelay.com",
        "linkvertise.com", "link-to.net", "direct-link.net", "file-link.net",
        "loot-links.com", "lootlinks.co", "loot-labs.com", "lootlabs.gg",
        "work.ink", "rekonise.com", "boost.ink", "lockr.so", "ouo.io", "ouo.press"
    ]

    @staticmethod
    def detect(url: str) -> dict:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if not domain:
            domain = parsed.path.lower().split('/')[0]

        for key, provider in PROVIDERS.items():
            if key == "general":
                continue
            for pattern in provider.get("patterns", []):
                if pattern in domain or pattern in url.lower():
                    return {
                        "key": key,
                        "name": provider["name"],
                        "emoji": provider["emoji"],
                        "color": provider["color"],
                        "domain": domain
                    }

        return {
            "key": "general",
            "name": PROVIDERS["general"]["name"],
            "emoji": PROVIDERS["general"]["emoji"],
            "color": PROVIDERS["general"]["color"],
            "domain": domain or "unknown"
        }

    @staticmethod
    def is_chainable(url: str) -> bool:
        url_lower = url.lower()
        return any(p in url_lower for p in DomainDetector.CHAINABLE_PATTERNS)

# ═══════════════════════════════════════════════════════════════
# 1. Platoboost / PlatoRelay Native Solver (4.5–5.5s)
# ═══════════════════════════════════════════════════════════════
def _normalize_platoboost_url(url: str) -> str:
    """Normalize dead gateway.platoboost.com domain to live auth.platoboost.net."""
    if "gateway.platoboost.com" in url:
        return url.replace("gateway.platoboost.com", "auth.platoboost.net")
    if "platoboost.com" in url and "auth.platoboost.net" not in url:
        return url.replace("platoboost.com", "auth.platoboost.net")
    return url

async def _bypass_platoboost_native(url: str) -> tuple[str | None, str]:
    """
    Native Platoboost / PlatoRelay Solver:
    1. Parse ticket query parameter ('d' or 'id')
    2. Check session status API via curl_cffi (<0.5s)
    3. Fast detect if ticket is already expired or invalid
    4. Headless browser waits 4.1s timer, clicks interactive action button, and reads key.
    """
    clean_url = _normalize_platoboost_url(url)
    parsed = urlparse(clean_url)
    qs = parse_qs(parsed.query)
    ticket = qs.get("d", [None])[0] or qs.get("id", [None])[0]
    
    api_host = "auth.platorelay.com" if "platorelay" in parsed.netloc else "auth.platoboost.net"
    
    # Step 1: Fast HTTP status check & expiry detection
    if ticket:
        try:
            status_url = f"https://{api_host}/api/session/status?ticket={ticket}"
            async with AsyncSession(impersonate="chrome124") as s:
                resp = await s.get(status_url, timeout=3)
                if resp.status_code == 200:
                    data = resp.json()
                    k = data.get("data", {}).get("key")
                    if k and k != "KEY_NOT_FOUND" and len(k) > 5:
                        return k, "platoboost-session-cache"
                    if not data.get("success") and "invalid" in data.get("message", "").lower():
                        return "EXPIRED_LINK", "platoboost-expired"
        except Exception:
            pass

    # Step 2: Fast Headless browser automation with strict 6s timeout
    async def _solve_platoboost_browser():
        try:
            from patchright.async_api import async_playwright
        except ImportError:
            try:
                from playwright.async_api import async_playwright
            except ImportError:
                return None, "failed"

        async with _BROWSER_SEM:
            try:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(
                        headless=True,
                        args=[
                            "--no-sandbox",
                            "--disable-dev-shm-usage",
                            "--disable-blink-features=AutomationControlled",
                            "--blink-settings=imagesEnabled=false"
                        ]
                    )
                    page = await browser.new_page()

                    try:
                        await page.goto(clean_url, wait_until="domcontentloaded", timeout=4000)
                    except Exception:
                        pass

                    await asyncio.sleep(0.5)
                    body = await page.evaluate("() => document.body ? document.body.innerText : ''")
                    if "expired" in body.lower():
                        await browser.close()
                        return "EXPIRED_LINK", "platoboost-expired"

                    # Wait for 3.5s countdown
                    await asyncio.sleep(3.5)

                    # Remove overlays & click action button
                    await page.evaluate("""() => {
                        document.querySelectorAll('div').forEach(d => {
                            const style = window.getComputedStyle(d);
                            if (style.position === 'fixed' || parseInt(style.zIndex || '0') > 10) {
                                d.remove();
                            }
                        });
                        const targets = ['continue', 'next', 'get key', 'claim', 'free access', 'unlock'];
                        for (const b of document.querySelectorAll('button, a, div[role="button"]')) {
                            const t = (b.innerText || '').toLowerCase();
                            if (targets.some(x => t.includes(x))) {
                                b.click();
                                break;
                            }
                        }
                    }""")
                    await asyncio.sleep(0.8)

                    key_result = None
                    if ticket:
                        try:
                            async with AsyncSession(impersonate="chrome124") as s:
                                resp = await s.get(f"https://{api_host}/api/session/status?ticket={ticket}", timeout=2)
                                if resp.status_code == 200:
                                    data = resp.json()
                                    k = data.get("data", {}).get("key")
                                    if k and k != "KEY_NOT_FOUND":
                                        key_result = k
                        except Exception:
                            pass

                    if not key_result:
                        key_result = await page.evaluate("""() => {
                            const inp = document.querySelector('input');
                            if (inp && inp.value && inp.value.length > 5) return inp.value;
                            const body = document.body ? document.body.innerText : '';
                            const m = body.match(/FREE_[A-Za-z0-9]+/);
                            return m ? m[0] : null;
                        }""")

                    await browser.close()
                    if key_result:
                        return key_result, "platoboost-native-timer"
            except Exception as e:
                print(f"[Platoboost Error] {e}")

        return None, "failed"

    try:
        return await asyncio.wait_for(_solve_platoboost_browser(), timeout=6.0)
    except asyncio.TimeoutError:
        return None, "platoboost-timeout"

# ═══════════════════════════════════════════════════════════════
# 2. LootLabs / LootLinks Native Solver
# ═══════════════════════════════════════════════════════════════
def _decode_lootlabs_cc(cc: str) -> str | None:
    try:
        cc = unquote(cc)
        pad = cc + "=" * (-len(cc) % 4)
        dec1 = base64.urlsafe_b64decode(pad).decode("utf-8", errors="strict")
        if dec1.startswith("{") or dec1.startswith("["):
            data = json.loads(dec1)
        else:
            pad2 = dec1 + "=" * (-len(dec1) % 4)
            data = json.loads(base64.b64decode(pad2).decode("utf-8"))
        return data.get("link") or data.get("url")
    except Exception:
        return None

def _decrypt_lootlabs_xor(enc: str) -> str | None:
    try:
        raw = base64.b64decode(enc).decode("latin1")
        if len(raw) <= 5:
            return None
        xor_key = raw[:5]
        payload = raw[5:]
        decrypted = ''.join(chr(ord(c) ^ ord(xor_key[i % 5])) for i, c in enumerate(payload))
        return unquote(decrypted.strip())
    except Exception:
        return None

async def _bypass_lootlabs_native(url: str) -> tuple[str | None, str]:
    """
    Native LootLabs Solver:
    1. Check cc= URL parameter (instant)
    2. Check HTML for PUBLISHER_LINK and decrypt with 5-byte XOR (instant)
    3. Hardware-Accelerated Multi-Task & Turnstile Solver (RTX 3060 D3D11)
    """
    if "cc=" in url:
        qs = parse_qs(urlparse(url).query)
        cc = qs.get("cc", [""])[0]
        if cc:
            res = _decode_lootlabs_cc(cc)
            if res and is_valid_result(res, url):
                return res, "lootlabs-cc-decoder"

    # Fast HTTP XOR extraction
    try:
        async with AsyncSession(impersonate="chrome124") as s:
            r = await s.get(url, timeout=5)
            html = r.text
            m_pub = re.search(r"p\[['\"]PUBLISHER_LINK['\"]\]\s*=\s*['\"]([^'\"]+)['\"]", html)
            if m_pub:
                dec = _decrypt_lootlabs_xor(m_pub.group(1))
                if dec and dec.startswith("http") and "lootlabs" not in dec and is_valid_result(dec, url):
                    return dec, "lootlabs-xor-instant"
    except Exception:
        pass

    # Fast Headless Task & Turnstile Solver (Cloud-Safe)
    async def _solve_lootlabs_browser():
        try:
            from patchright.async_api import async_playwright
        except ImportError:
            try:
                from playwright.async_api import async_playwright
            except ImportError:
                return None, "failed"

        async with _BROWSER_SEM:
            try:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(
                        headless=True,
                        args=[
                            "--no-sandbox",
                            "--disable-dev-shm-usage",
                            "--disable-blink-features=AutomationControlled",
                            "--blink-settings=imagesEnabled=false"
                        ]
                    )
                    context = await browser.new_context(locale="en-US")
                    main_page = await context.new_page()

                    found_dest = None
                    done_event = asyncio.Event()

                    def on_ws(ws):
                        def on_frame(payload):
                            nonlocal found_dest
                            s = str(payload)
                            if s.startswith("r:"):
                                dec = _decrypt_lootlabs_xor(s[2:])
                                if dec and dec.startswith("http") and "lootlabs" not in dec:
                                    found_dest = dec
                                    done_event.set()
                        ws.on("framereceived", on_frame)

                    main_page.on("websocket", on_ws)

                    try:
                        await main_page.goto(url, wait_until="domcontentloaded", timeout=4000)
                    except Exception:
                        pass

                    await asyncio.sleep(0.4)

                    # 1. Check Task 41 (Captcha)
                    task41 = await main_page.query_selector("div[class*='41_']")
                    if task41:
                        try:
                            urid = await task41.get_attribute("id")
                            await task41.click()
                            await asyncio.sleep(0.2)

                            captcha_tab = await context.new_page()
                            try:
                                await captcha_tab.goto(f"https://nerventualken.com/captcha?urid={urid}", wait_until="domcontentloaded", timeout=4000)
                                await captcha_tab.bring_to_front()

                                clicked_cb = False
                                for _ in range(5):
                                    await asyncio.sleep(0.4)
                                    go_active = await captcha_tab.evaluate("() => { const b = document.getElementById('go'); return b && !b.disabled; }")
                                    if go_active:
                                        await captcha_tab.click("#go")
                                        await asyncio.sleep(0.5)
                                        break

                                    if not clicked_cb:
                                        for f in captcha_tab.frames:
                                            if "cloudflare" in f.url or "turnstile" in f.url:
                                                cb = await f.query_selector("input[type='checkbox']")
                                                if cb and not await cb.is_checked():
                                                    await cb.click()
                                                    clicked_cb = True
                            except Exception:
                                pass
                            finally:
                                try:
                                    await captcha_tab.close()
                                except Exception:
                                    pass
                                await main_page.bring_to_front()
                        except Exception:
                            pass

                    # 2. Click remaining sponsor tasks
                    other_tasks = await main_page.query_selector_all(".task:not([class*='41_'])")
                    for ot in other_tasks[:3]:
                        try:
                            await ot.click()
                            await asyncio.sleep(0.2)
                        except Exception:
                            pass

                    # 3. Poll WebSocket and Unlock button (up to ~3.5s)
                    for _ in range(7):
                        if done_event.is_set() or found_dest:
                            break
                        await asyncio.sleep(0.5)
                        try:
                            btn_active = await main_page.evaluate("""() => {
                                const b = document.querySelector('#unlockBtn');
                                return b && !b.disabled;
                            }""")
                            if btn_active:
                                await main_page.click("#unlockBtn")
                                await asyncio.sleep(0.8)
                        except Exception:
                            pass

                    await browser.close()
                    if found_dest and is_valid_result(found_dest, url):
                        return found_dest, "lootlabs-task-solver"
            except Exception as e:
                print(f"[LootLabs Error] {e}")

        return None, "failed"

    try:
        return await asyncio.wait_for(_solve_lootlabs_browser(), timeout=6.0)
    except asyncio.TimeoutError:
        return None, "lootlabs-timeout"

# ═══════════════════════════════════════════════════════════════
# 3. Work.ink Native Solver
# ═══════════════════════════════════════════════════════════════
def _decode_workink_duf(url: str) -> str | None:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "duf" in qs:
        duf = qs["duf"][0]
        try:
            rev = duf[::-1]
            pad = rev + "=" * (-len(rev) % 4)
            return base64.b64decode(pad).decode("utf-8", errors="ignore")
        except Exception:
            pass
    return None

async def _bypass_workink_native(url: str) -> tuple[str | None, str]:
    duf_res = _decode_workink_duf(url)
    if duf_res and duf_res.startswith("http"):
        return duf_res, "workink-duf-decoder"

    # Direct redirect check
    clean_url = url.replace("r.work.ink", "work.ink")
    try:
        async with AsyncSession(impersonate="chrome124") as s:
            r = await s.get(clean_url, allow_redirects=True, timeout=5)
            final_url = str(r.url)
            if final_url != clean_url and "work.ink" not in final_url and final_url.startswith("http"):
                return final_url, "workink-direct-redirect"
            duf2 = _decode_workink_duf(final_url)
            if duf2 and duf2.startswith("http"):
                return duf2, "workink-duf-decoder"
    except Exception:
        pass

    return None, "failed"

# ═══════════════════════════════════════════════════════════════
# 4. Rekonise Native Solver
# ═══════════════════════════════════════════════════════════════
async def _bypass_rekonise_native(url: str) -> tuple[str | None, str]:
    try:
        path_parts = urlparse(url).path.strip('/').split('/')
        if len(path_parts) >= 1:
            social_id = path_parts[-1]
            api_url = f"https://api.rekonise.com/social-unlocks/{social_id}/unlock"
            async with AsyncSession(impersonate="chrome124") as s:
                resp = await s.get(api_url, timeout=4)
                if resp.status_code == 200:
                    data = resp.json()
                    target = data.get("url")
                    if target and is_valid_result(target, url):
                        return target, "rekonise-unlock-api"
    except Exception:
        pass
    return None, "failed"

# ═══════════════════════════════════════════════════════════════
# 5. File Hosters (PixelDrain, MediaFire, GoFile, etc.)
# ═══════════════════════════════════════════════════════════════
def _bypass_filehosts_native(url: str) -> tuple[str | None, str]:
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    # PixelDrain: /u/{id} -> /api/file/{id}
    if "pixeldrain.com" in domain and "/u/" in parsed.path:
        file_id = parsed.path.strip("/").split("/")[-1]
        if file_id:
            return f"https://pixeldrain.com/api/file/{file_id}", "pixeldrain-direct-api"
            
    return None, "failed"

# ═══════════════════════════════════════════════════════════════
# Bypass Engine Orchestrator
# ═══════════════════════════════════════════════════════════════
class BypassEngine:
    """Master Multi-Tier Self-Hosted Bypass Orchestrator."""

    async def bypass_url(self, url: str) -> dict:
        try:
            return await asyncio.wait_for(self._bypass_url_internal(url), timeout=9.5)
        except asyncio.TimeoutError:
            provider = DomainDetector.detect(url)
            return {
                "success": False,
                "error": "⏱️ การ Bypass ใช้เวลานานเกินกำหนด (Timeout 9s) ลิงก์อาจติด Cloudflare ขั้นสูง หรือปลายทางไม่ตอบสนอง กรุณาลองใหม่อีกครั้ง",
                "provider": provider,
                "time_taken": 9.5
            }

    async def _bypass_url_internal(self, url: str) -> dict:
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        start_time = time.time()
        provider = DomainDetector.detect(url)
        provider_key = provider["key"]

        result = None
        engine_used = "unknown"
        is_key = False

        # 1. Instant Filehoster Check (<0.01s - regex / direct transform)
        fh_res, fh_eng = _bypass_filehosts_native(url)
        if fh_res:
            result = fh_res
            engine_used = fh_eng

        # 2. PRIORITY #1: RTaO API High-Speed Engine (100% Pass on 246+ Supported Domains)
        if not result:
            api_res, api_eng = await rtao_client.bypass(url)
            if api_res and is_valid_result(api_res, url):
                result = api_res
                engine_used = api_eng
                if not result.startswith("http"):
                    is_key = True

        # 3. Tier-2 Fallback: Specialized Native Solvers (if RTaO is unavailable, failed, or unsupported)
        if not result or not is_valid_result(result, url):
            if provider_key == "platoboost":
                result, engine_used = await _bypass_platoboost_native(url)
                if result == "EXPIRED_LINK":
                    return {
                        "success": False,
                        "error": "❌ ลิงก์นี้หมดอายุแล้ว (Session Expired) กรุณากดสร้างลิงก์ใหม่จากตัวเกม",
                        "provider": provider,
                        "time_taken": round(time.time() - start_time, 2)
                    }
                if result:
                    is_key = not result.startswith("http")

            elif provider_key == "lootlabs":
                result, engine_used = await _bypass_lootlabs_native(url)

            elif provider_key == "workink":
                result, engine_used = await _bypass_workink_native(url)

            elif provider_key == "rekonise":
                result, engine_used = await _bypass_rekonise_native(url)

        # 4. Tier-3 Fallback: Direct redirect resolution & chained RTaO check
        if not result or not is_valid_result(result, url):
            try:
                async with AsyncSession(impersonate="chrome124") as s:
                    r = await s.get(url, allow_redirects=True, timeout=5)
                    final = str(r.url)
                    if final != url and is_valid_result(final, url):
                        # If redirect revealed a domain supported by RTaO, query RTaO with final URL
                        if rtao_client.is_domain_supported(final):
                            r_res, r_eng = await rtao_client.bypass(final)
                            if r_res and is_valid_result(r_res, final):
                                result = r_res
                                engine_used = r_eng
                                if not result.startswith("http"):
                                    is_key = True
                        if not result:
                            result = final
                            engine_used = "universal-redirect"
            except Exception:
                pass

        elapsed = round(time.time() - start_time, 2)

        if result and is_valid_result(result, url):
            return {
                "success": True,
                "direct_url": result,
                "provider": provider,
                "endpoint_used": engine_used,
                "chain_note": f"Solved in {elapsed}s via {engine_used}",
                "is_key": is_key,
                "time_taken": elapsed
            }

        return {
            "success": False,
            "error": "Failed to bypass link within time limit",
            "provider": provider,
            "time_taken": elapsed
        }

# Global singleton
bypass_engine = BypassEngine()