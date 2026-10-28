"""
RTaO High-Reliability Primary API Client & Quota Manager (Priority #1 Engine).
Target API: https://api.rtaoexe.xyz/bypass
Quota: 3,000 Requests
Alert: Terminal warning when remaining requests < 100
"""

import os
import json
import time
from urllib.parse import quote
from curl_cffi.requests import AsyncSession

QUOTA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "rtao_quota.json")
SUPPORTED_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "rtao_supported.json")
RTAO_API_KEY = os.getenv("RTAO_API_KEY", "rtao-864d7419ae7d506c")
RTAO_BASE_URL = "https://api.rtaoexe.xyz/bypass"
RTAO_SUPPORTED_URL = "https://api.rtaoexe.xyz/supported"
INITIAL_QUOTA = 3000
LOW_QUOTA_THRESHOLD = 100


class RtaoClient:
    """Manages RTaO Primary API calls and persistent quota tracking."""

    def __init__(self):
        self._ensure_data_dir()
        self.data = self._load_data()
        self.supported_domains = self._load_supported()

    def _ensure_data_dir(self):
        data_dir = os.path.dirname(QUOTA_FILE)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)

    def _load_supported(self) -> set:
        """Loads cached supported domains list from disk."""
        if os.path.exists(SUPPORTED_FILE):
            try:
                with open(SUPPORTED_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return set(data.get("domains", []))
            except Exception:
                pass
        return set()

    def _save_supported(self, domains: list):
        try:
            with open(SUPPORTED_FILE, "w", encoding="utf-8") as f:
                json.dump({"total": len(domains), "domains": domains}, f, indent=2)
            self.supported_domains = set(domains)
        except Exception as e:
            print(f"[RtaoClient] Error saving supported domains: {e}")

    async def sync_supported_domains(self) -> list:
        """Fetches the latest supported domains directly from https://api.rtaoexe.xyz/supported."""
        try:
            async with AsyncSession(impersonate="chrome124") as s:
                resp = await s.get(RTAO_SUPPORTED_URL, timeout=8)
                if resp.status_code == 200:
                    data = resp.json()
                    domains = data.get("domains", [])
                    if domains:
                        self._save_supported(domains)
                        return domains
        except Exception as e:
            print(f"[RtaoClient] Failed to fetch /supported: {e}")
        return list(self.supported_domains)

    def is_domain_supported(self, url: str) -> bool:
        """Checks if the URL's domain is in RTaO's 246+ supported domain list."""
        if not self.supported_domains:
            return True  # If not loaded yet, assume eligible
        url_lower = url.lower()
        return any(d in url_lower for d in self.supported_domains)

    def _load_data(self) -> dict:
        if os.path.exists(QUOTA_FILE):
            try:
                with open(QUOTA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "initial_quota": INITIAL_QUOTA,
            "requests_remaining": INITIAL_QUOTA,
            "total_calls": 0,
            "last_used": None,
            "history": []
        }

    def _save_data(self):
        try:
            with open(QUOTA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[RtaoClient] Error saving quota file: {e}")

    def get_remaining(self) -> int:
        return self.data.get("requests_remaining", INITIAL_QUOTA)

    def get_status(self) -> dict:
        return {
            "remaining": self.get_remaining(),
            "total_calls": self.data.get("total_calls", 0),
            "last_used": self.data.get("last_used")
        }

    def _check_and_warn_quota(self, remaining: int):
        """Prints high-visibility terminal warning if quota is below threshold."""
        if remaining < LOW_QUOTA_THRESHOLD:
            warn_box = (
                "\n" + "=" * 65 + "\n"
                f"  [!] [WARNING] [RTAO API QUOTA RUNNING LOW!]\n"
                f"  Remaining requests: {remaining} / {INITIAL_QUOTA}\n"
                f"  Quota is below threshold ({LOW_QUOTA_THRESHOLD})!\n"
                f"  Please renew or prepare backup to prevent service downtime.\n"
                + "=" * 65 + "\n"
            )
            try:
                print(f"\033[91m\033[1m{warn_box}\033[0m", flush=True)
            except Exception:
                try:
                    sys.stdout.buffer.write(warn_box.encode("utf-8", errors="replace"))
                    sys.stdout.flush()
                except Exception:
                    pass

    async def bypass(self, url: str) -> tuple[str | None, str]:
        """
        Calls RTaO API fallback for the given URL.
        Returns: (direct_url | None, engine_name)
        """
        key = os.getenv("RTAO_API_KEY", RTAO_API_KEY)
        if not key:
            return None, "rtao-no-key"

        req_url = f"{RTAO_BASE_URL}?key={key}&url={quote(url)}"
        
        try:
            async with AsyncSession(impersonate="chrome124") as s:
                resp = await s.get(
                    req_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Accept": "application/json"
                    },
                    timeout=15
                )

                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status")

                    # Extract remaining quota reported directly by server
                    server_remaining = data.get("requests_remaining")
                    if isinstance(server_remaining, int):
                        self.data["requests_remaining"] = server_remaining
                    else:
                        self.data["requests_remaining"] = max(0, self.get_remaining() - 1)

                    self.data["total_calls"] = self.data.get("total_calls", 0) + 1
                    self.data["last_used"] = time.strftime("%Y-%m-%d %H:%M:%S")

                    # Keep last 50 calls in history
                    history = self.data.setdefault("history", [])
                    history.append({
                        "time": self.data["last_used"],
                        "url": url,
                        "status": status,
                        "remaining": self.data["requests_remaining"]
                    })
                    if len(history) > 50:
                        self.data["history"] = history[-50:]

                    self._save_data()

                    # Check quota warning
                    curr_remaining = self.data["requests_remaining"]
                    self._check_and_warn_quota(curr_remaining)

                    if status == "success":
                        raw_result = str(data.get("result", ""))
                        # Clean quotes, trailing commas, whitespace repeatedly
                        clean_result = raw_result.strip()
                        for _ in range(5):
                            clean_result = clean_result.strip(" \t\n\r'\",`")
                        
                        time_taken = data.get("time_taken", "?")
                        print(f"[*] [RTAO API] Bypass SUCCESS in {time_taken}! Remaining Quota: {curr_remaining}/3000", flush=True)
                        return clean_result, "rtao-api"
                    else:
                        print(f"[-] [RTAO API] Server returned non-success: {data.get('result')}", flush=True)

                else:
                    print(f"[-] [RTAO API] HTTP error {resp.status_code}: {resp.text[:200]}", flush=True)

        except Exception as e:
            print(f"[!] [RTAO API] Request error: {e}", flush=True)

        return None, "rtao-api-failed"


# Global singleton
rtao_client = RtaoClient()
