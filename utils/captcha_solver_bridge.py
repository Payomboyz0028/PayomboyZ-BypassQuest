"""
================================================================================
  PAYOMBOYZ CAPTCHA & BYPASS SOLVER BRIDGE
  Connects Discord Quests Engine to d:\Deobfuscate\Lerning\Bypass&slove
  Supports: Capsolver Core, EzSolver (Turnstile), ReCaptcha/hCaptcha
================================================================================
"""

import os
import sys
import json
import asyncio
from typing import Optional, Dict, Any

# Add Lerning paths to sys.path
_LERNING_DIR = r"d:\Deobfuscate\Lerning\Bypass&slove\Lerning"
_CAPSOLVER_DIR = os.path.join(_LERNING_DIR, "capsolver-core-main", "src")
_EZSOLVER_DIR = os.path.join(_LERNING_DIR, "Tunel", "EzSolver-main")

for p in [_LERNING_DIR, _CAPSOLVER_DIR, _EZSOLVER_DIR]:
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

CAPSOLVER_API_KEY = os.getenv("CAPSOLVER_API_KEY", "")


async def solve_discord_captcha(
    sitekey: str,
    service: str,
    rqdata: Optional[str] = None,
    rqtoken: Optional[str] = None,
    page_url: str = "https://discord.com/channels/@me"
) -> Optional[str]:
    """
    Attempts to solve Discord's captcha challenge using available solvers:
    1. Capsolver Core (API-based, handles hCaptcha, Turnstile, ReCaptcha)
    2. EzSolver (Local browser-based Turnstile solver via nodriver)
    """
    service_clean = str(service or "").lower().strip()
    print(f"[CaptchaBridge] Solving challenge: service={service_clean}, sitekey={sitekey[:10]}...", flush=True)

    # Strategy 1: Capsolver API Client (if API Key available)
    if CAPSOLVER_API_KEY:
        try:
            import capsolver_core
            from capsolver_core.capsolver import Capsolver
            from capsolver_core.core.types import CaptchaType

            solver = Capsolver(api_key=CAPSOLVER_API_KEY)
            
            task_data = {
                "websiteURL": page_url,
                "websiteKey": sitekey,
            }
            if rqdata:
                task_data["enterprisePayload"] = {"rqdata": rqdata}

            if "hcaptcha" in service_clean:
                task_type = CaptchaType.HCAPTCHA_ENTERPRISE if rqdata else CaptchaType.HCAPTCHA
            elif "turnstile" in service_clean:
                task_type = CaptchaType.CLOUDFLARE_TURNSTILE
            else:
                task_type = CaptchaType.RECAPTCHA_V2

            print(f"[CaptchaBridge] Dispatching to Capsolver API ({task_type})...", flush=True)
            res = await asyncio.to_thread(solver.solve, task_type, task_data)
            if res and hasattr(res, "solution"):
                token = res.solution.get("token") or res.solution.get("gRecaptchaResponse")
                if token:
                    print(f"[CaptchaBridge] Capsolver solved token successfully!", flush=True)
                    return token
        except Exception as e:
            print(f"[CaptchaBridge] Capsolver solve error: {e}", flush=True)

    # Strategy 2: EzSolver (Local Chrome Turnstile Solver for Discord Web)
    if "turnstile" in service_clean or "cloudflare" in service_clean:
        try:
            import solver as ez_solver
            print(f"[CaptchaBridge] Invoking EzSolver local Turnstile engine...", flush=True)
            loop = asyncio.get_event_loop()
            token = await loop.run_in_executor(None, ez_solver.solve, page_url, sitekey)
            if token:
                print(f"[CaptchaBridge] EzSolver solved token successfully!", flush=True)
                return token
        except Exception as e:
            print(f"[CaptchaBridge] EzSolver error: {e}", flush=True)

    print(f"[CaptchaBridge] No automated token produced for service: {service_clean}", flush=True)
    return None
