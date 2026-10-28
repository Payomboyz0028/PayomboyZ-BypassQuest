"""
================================================================================
  PAYOMBOYZ AUTO QUEST - NEXT-GEN DISCORD QUEST AUTOMATION ENGINE
  Branding: PayomboyZ Auto Quest (by dj & ANON)
  Core Engine: High-Fidelity Discord Quests API v10 Protocol (Reversed from GHOST X)
  Features:
    - 100% Real API v10 Protocol (Enroll, Heartbeat, Video-Progress, Claim-Reward)
    - Browser/Desktop Fingerprint: Build 471091, Chrome 138, Electron 37.6.0
    - Multi-Token Support: Input 1 or multiple tokens (1 per line)
    - Fully Customizable / Editable Panel System (Title, Description, Banner, Color, Buttons)
    - Live In-Place Progress Editing & Dual-Channel Routing (#กำลังทำเควส & #รายการเควสเสร็จสิ้น)
    - VIP / Pro Role & Key Redemption System
    - Built-in Commercial REST API Server (Port 5050) for Web Shop Integration
================================================================================
"""

import os
import sys
import time
import json
import uuid
import base64
import secrets
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Set, Tuple, Union

# UTF-8 Console Encoding for Windows CP874 Thai
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass

import aiohttp
from aiohttp import web
import discord
from discord.ext import commands, tasks
from discord import ui, app_commands

# ==============================================================================
# 0. CONFIGURATION & TOKEN RESOLVER
# ==============================================================================
def resolve_bot_token() -> str:
    # 1. CLI Arguments: --token <token> or -t <token>
    for i, arg in enumerate(sys.argv):
        if arg in ("--token", "-t") and i + 1 < len(sys.argv):
            return sys.argv[i + 1].strip()
        if arg.startswith("--token="):
            return arg.split("=", 1)[1].strip()
    # 2. Environment Variables
    env_token = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN")
    if env_token and env_token.strip():
        return env_token.strip()
    # 3. .env File in current or parent directory
    base_dirs = [
        os.path.dirname(os.path.abspath(__file__)),
        os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")),
        os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "GHOST X - AUTOQUEST"))
    ]
    for bdir in base_dirs:
        env_path = os.path.join(bdir, ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("DISCORD_TOKEN=") or line.startswith("DISCORD_BOT_TOKEN="):
                            return line.split("=", 1)[1].strip().strip('"').strip("'")
            except Exception:
                pass
    # 4. Default Verified Bot Token
    return os.getenv("DISCORD_BOT_TOKEN", "")

BOT_TOKEN = resolve_bot_token()
OWNER_ID  = int(os.getenv("OWNER_ID", os.getenv("BOT_OWNER_ID", 1465003898405130411)))

# API Server Settings
API_HOST          = os.getenv("PAYOMBOYZ_API_HOST", "0.0.0.0")
API_PORT          = int(os.getenv("PAYOMBOYZ_API_PORT", 5050))
MASTER_API_SECRET = os.getenv("PAYOMBOYZ_MASTER_SECRET", "PAYOMBOYZ-SECRET-2026")

# Asset Paths for Custom Logo & Upscaled Banner
ASSETS_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
LOGO_PATH   = os.path.join(ASSETS_DIR, "logo.png")
BANNER_PATH = os.path.join(ASSETS_DIR, "banner.png")


# ==============================================================================
# 1. EDITABLE PANEL CONFIGURATION & STATE STORE
# ==============================================================================
class PanelConfigStore:
    """Manages customizable panel UI, guild channel bindings, quotas, and VIP keys."""
    def __init__(self, data_file: Optional[str] = None):
        if data_file is None:
            data_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "payomboyz_quest_data.json")
        self.data_file = data_file
        self.guild_panels: Dict[str, Dict[str, Any]] = {}
        self.guild_settings: Dict[str, Dict[str, Any]] = {}
        self.user_quotas: Dict[str, Dict[str, Any]] = {}
        self.pro_users: Dict[str, str] = {}  # user_id -> iso_expiry
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        self.redeem_keys: Set[str] = {
            "PAYOMBOYZ-VIP-2026",
            "PAYOMBOYZ-LIFETIME-PREMIUM",
            "GHOSTX-PRO-PASS",
            "PAYOMBOYZ-SPECIAL-9999",
            "DEVIL-VIP-2026"
        }
        self.load()

    def get_default_panel(self) -> Dict[str, Any]:
        return {
            "title": "⚡ PAYOMBØYZ AUTO QUEST SYSTEM ⚡",
            "description": (
                "```ansi\n"
                "\u001b[1;31m[PAYOMBØYZ]\u001b[0m \u001b[1;32m● AUTO QUEST ENGINE ACTIVE\u001b[0m \u001b[1;36mv10.0\u001b[0m\n"
                "\u001b[2;37mPREMIUM CYBER EDITION • DISCORD QUESTS API v10\u001b[0m\n"
                "```\n"
                "**✨ ระบบทำเควส Discord ออโต้ความเร็วสูง (High-Speed Engine)**\n"
                "**🚀 รองรับการใส่หลาย Token พร้อมกัน** `(1 บรรทัดต่อ 1 Token)`\n"
                "**🛡️ ระบบ Anti-Stuck & Real-Time Heartbeat ปลอดภัย 100%**\n"
                "**🎁 ตรวจสอบเควสและกดรับของรางวัล (Claim Reward) ให้อัตโนมัติ**\n\n"
                "────────────────────────────────────────────\n"
                "**📌 เมนูคำสั่งลัด / แผงควบคุมด่วน:**\n"
                "> • เลือกทำรายการผ่าน **Dropdown Menu** ด้านล่างได้ทันที\n"
                "> • หรือคลิกปุ่มลัด **[🚀 เริ่มทำเควส]** เพื่อเริ่มส่ง Token\n"
                "> • ติดตามความคืบหน้าแบบ Real-Time ได้ที่ห้องสถานะ\n"
                "────────────────────────────────────────────"
            ),
            "logo_path": LOGO_PATH,
            "banner_path": BANNER_PATH,
            "banner_url": "",
            "logo_url": "",
            "color": 0x0B0C10,
            "button_label": "🚀 เริ่มทำเควส (Start Quest)",
            "button_emoji": "🚀",
            "is_open": True,
            "closed_reason": "ระบบปิดปรับปรุงชั่วคราว กรุณารอเปิดรอบใหม่"
        }

    def load(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.guild_panels = data.get("panels", {})
                    self.guild_settings = data.get("guilds", {})
                    self.user_quotas = data.get("quotas", {})
                    self.pro_users = data.get("pro", {})
                    self.api_keys = data.get("api_keys", {})
                    saved_keys = data.get("keys", [])
                    if saved_keys:
                        self.redeem_keys.update(saved_keys)
            except Exception as e:
                print(f"[PanelStore] Load failed, starting clean: {e}")

    def save(self):
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump({
                    "panels": self.guild_panels,
                    "guilds": self.guild_settings,
                    "quotas": self.user_quotas,
                    "pro": self.pro_users,
                    "api_keys": self.api_keys,
                    "keys": list(self.redeem_keys)
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[PanelStore] Save error: {e}")

    def get_panel(self, guild_id: int) -> Dict[str, Any]:
        gid = str(guild_id)
        if gid not in self.guild_panels:
            self.guild_panels[gid] = self.get_default_panel()
            self.save()
        return self.guild_panels[gid]

    def update_panel(self, guild_id: int, **kwargs):
        gid = str(guild_id)
        panel = self.get_panel(guild_id)
        for k, v in kwargs.items():
            if v is not None:
                panel[k] = v
        self.guild_panels[gid] = panel
        self.save()

    def get_guild(self, guild_id: int) -> Dict[str, Any]:
        return self.guild_settings.get(str(guild_id), {})

    def set_guild_channels(self, guild_id: int, status_ch_id: int, result_ch_id: int):
        gid = str(guild_id)
        if gid not in self.guild_settings:
            self.guild_settings[gid] = {}
        self.guild_settings[gid]["status_channel_id"] = status_ch_id
        self.guild_settings[gid]["result_channel_id"] = result_ch_id
        self.save()

    KNOWN_VIP_ROLES = {1560952877726302218, 1549785782330593330}
    OWNER_IDS = {1351000216228331551}

    def set_pro_role(self, guild_id: int, role_id: int):
        gid = str(guild_id)
        if gid not in self.guild_settings:
            self.guild_settings[gid] = {}
        self.guild_settings[gid]["pro_role_id"] = role_id
        self.save()

    def is_user_pro(self, user_id: int, member: Optional[discord.Member] = None, guild_id: Optional[int] = None) -> bool:
        try:
            if int(user_id) in self.OWNER_IDS:
                return True
        except Exception:
            pass
        uid = str(user_id)
        if uid in self.pro_users:
            try:
                exp = datetime.fromisoformat(self.pro_users[uid])
                if exp > datetime.now():
                    return True
            except Exception:
                pass
        if member:
            if getattr(getattr(member, "guild_permissions", None), "administrator", False):
                return True
            roles = getattr(member, "roles", [])
            if any(getattr(r, "id", None) in self.KNOWN_VIP_ROLES for r in roles):
                return True
            if guild_id:
                cfg = self.get_guild(guild_id)
                pro_role_id = cfg.get("pro_role_id")
                if pro_role_id and any(getattr(r, "id", None) == pro_role_id for r in roles):
                    return True
        return False

    def check_and_increment_quota(self, user_id: int, is_pro: bool) -> Tuple[bool, int]:
        if is_pro:
            return True, 0
        uid = str(user_id)
        now_ts = time.time()
        record = self.user_quotas.get(uid, {"count": 0, "reset_ts": now_ts})
        if now_ts - record.get("reset_ts", 0) > 86400:
            record = {"count": 0, "reset_ts": now_ts}
        if record["count"] >= 3:
            return False, record["count"]
        record["count"] += 1
        self.user_quotas[uid] = record
        self.save()
        return True, record["count"]

    def grant_pro(self, user_id: int, days: int = 30) -> datetime:
        uid = str(user_id)
        exp = datetime.now() + timedelta(days=days)
        self.pro_users[uid] = exp.isoformat()
        self.save()
        return exp

    def set_user_pro(self, user_id: int, days: int) -> Optional[datetime]:
        uid = str(user_id)
        if days <= 0:
            self.pro_users.pop(uid, None)
            self.save()
            return None
        else:
            exp = datetime.now() + timedelta(days=days)
            self.pro_users[uid] = exp.isoformat()
            self.save()
            return exp

    def reset_all_quotas(self):
        self.user_quotas.clear()
        self.save()

    def get_user_status(self, user_id: int, member: Optional[discord.Member] = None, guild_id: Optional[int] = None) -> Dict[str, Any]:
        is_pro = self.is_user_pro(user_id, member, guild_id)
        uid = str(user_id)
        expiry_str = self.pro_users.get(uid)
        now_ts = time.time()
        rec = self.user_quotas.get(uid, {"count": 0, "reset_ts": now_ts})
        if now_ts - rec.get("reset_ts", 0) > 86400:
            rec = {"count": 0, "reset_ts": now_ts}
        used = rec.get("count", 0)
        return {
            "user_id": str(user_id),
            "is_pro": is_pro,
            "pro_expiry": expiry_str,
            "quota_used": used,
            "quota_limit": "UNLIMITED" if is_pro else 3,
            "quota_remaining": 9999 if is_pro else max(0, 3 - used)
        }

    def redeem_key(self, user_id: int, key: str) -> bool:
        clean_key = key.strip()
        if clean_key in self.redeem_keys:
            self.grant_pro(user_id, 30)
            self.redeem_keys.discard(clean_key)
            self.save()
            return True
        return False

    def generate_api_key(self, credits: int = 50, days: int = 30, tier: str = "Standard", note: str = "") -> Dict[str, Any]:
        raw_key = f"PAYOMBOYZ-API-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"
        expiry = (datetime.now() + timedelta(days=days)).isoformat() if days > 0 else None
        record = {
            "key": raw_key,
            "credits": credits,
            "tier": tier.upper(),
            "note": note,
            "created_at": datetime.now().isoformat(),
            "expires_at": expiry,
            "is_active": True,
            "total_used": 0
        }
        self.api_keys[raw_key] = record
        self.save()
        return record

state = PanelConfigStore()

# ==============================================================================
# 2. DISCORD QUESTS API V10 REVERSED CLIENT (GHOST X RECONSTRUCTION)
# ==============================================================================
class DiscordQuestV10Handler:
    """
    High-fidelity Discord Quests Client reverse-engineered from GHOST X & Discord Web Build 643186.
    Handles real REST enrollment, heartbeats, video progression, and reward claiming.
    """
    API_BASE = "https://discord.com/api/v10"
    DEFAULT_UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    )

    @classmethod
    def get_super_properties(cls) -> str:
        props = {
            "os": "Windows",
            "browser": "Chrome",
            "device": "",
            "system_locale": "en-US",
            "browser_user_agent": cls.DEFAULT_UA,
            "browser_version": "128.0.0.0",
            "os_version": "10",
            "referrer": "https://www.google.com/",
            "referring_domain": "www.google.com",
            "referrer_current": "",
            "referring_domain_current": "",
            "release_channel": "stable",
            "client_build_number": 643186,
            "client_event_source": None
        }
        return base64.b64encode(json.dumps(props).encode("utf-8")).decode("utf-8")

    @classmethod
    def get_headers(cls, user_token: str) -> Dict[str, str]:
        clean_token = user_token.strip().strip('"').strip("'").replace("Bot ", "")
        return {
            "Authorization": clean_token,
            "Content-Type": "application/json",
            "User-Agent": cls.DEFAULT_UA,
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://discord.com",
            "Referer": "https://discord.com/channels/@me",
            "X-Super-Properties": cls.get_super_properties(),
            "X-Discord-Locale": "en-US",
            "X-Debug-Options": "bugReporterEnabled"
        }

    @classmethod
    async def validate_token(cls, token: str) -> Optional[Dict[str, Any]]:
        clean_token = token.strip().strip('"').strip("'").replace("Bot ", "")
        headers = {
            "Authorization": clean_token,
            "User-Agent": cls.DEFAULT_UA,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{cls.API_BASE}/users/@me", headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as r:
                    if r.status == 200:
                        return await r.json()
                    else:
                        print(f"[QuestAPI] validate_token failed HTTP {r.status}: {await r.text()}", flush=True)
        except Exception as e:
            print(f"[QuestAPI] validate_token exception: {e}", flush=True)
        return None

    @classmethod
    async def fetch_quests(cls, token: str) -> Dict[str, Any]:
        headers = cls.get_headers(token)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{cls.API_BASE}/quests/@me", headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    if r.status == 200:
                        return await r.json()
        except Exception as e:
            print(f"[QuestAPI] Fetch quests error: {e}")
        return {"quests": []}

    @classmethod
    async def enroll(cls, token: str, quest_id: str) -> Dict[str, Any]:
        headers = cls.get_headers(token)
        body = {
            "location": 11,
            "is_targeted": False,
            "metadata_raw": None
        }
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{cls.API_BASE}/quests/{quest_id}/enroll"
                async with session.post(url, headers=headers, json=body, timeout=aiohttp.ClientTimeout(total=8)) as r:
                    return await r.json()
        except Exception as e:
            return {"code": -1, "message": str(e)}

    @classmethod
    async def heartbeat(cls, token: str, quest_id: str, application_id: str, terminal: bool = False) -> Dict[str, Any]:
        headers = cls.get_headers(token)
        body = {
            "application_id": str(application_id),
            "terminal": terminal
        }
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{cls.API_BASE}/quests/{quest_id}/heartbeat"
                async with session.post(url, headers=headers, json=body, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    return await r.json()
        except Exception as e:
            return {"code": -1, "message": str(e)}

    @classmethod
    async def video_progress(cls, token: str, quest_id: str, timestamp: float) -> Dict[str, Any]:
        headers = cls.get_headers(token)
        body = {"timestamp": timestamp}
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{cls.API_BASE}/quests/{quest_id}/video-progress"
                async with session.post(url, headers=headers, json=body, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    return await r.json()
        except Exception as e:
            return {"code": -1, "message": str(e)}

    @classmethod
    async def _try_solve_captcha(cls, captcha_data: Dict[str, Any], headers: Dict[str, str]) -> Optional[str]:
        sitekey = captcha_data.get("captcha_sitekey")
        service = captcha_data.get("captcha_service") or "hcaptcha"
        rqdata = captcha_data.get("captcha_rqdata")
        rqtoken = captcha_data.get("captcha_rqtoken")
        if not sitekey:
            return None
        try:
            from utils.captcha_solver_bridge import solve_discord_captcha
            return await solve_discord_captcha(sitekey, service, rqdata, rqtoken)
        except Exception as e:
            print(f"[QuestAPI] _try_solve_captcha error: {e}", flush=True)
            return None

    @classmethod
    async def claim_reward(cls, token: str, quest_id: str, platform: int = 0) -> Dict[str, Any]:
        """
        High-reliability Reward Claim with multi-payload fallback, platform negotiation,
        and automated captcha solving bridge.
        """
        headers = cls.get_headers(token)
        url = f"{cls.API_BASE}/quests/{quest_id}/claim-reward"

        candidate_payloads = [
            {"platform": platform, "location": 11},
            {"location": 11},
            {"platform": 0, "location": 11},
            {"platform": 1, "location": 11},
            {}
        ]

        last_resp = None
        for body in candidate_payloads:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, headers=headers, json=body, timeout=aiohttp.ClientTimeout(total=12)) as r:
                        raw_text = await r.text()
                        try:
                            data = json.loads(raw_text)
                        except Exception:
                            data = {"status_code": r.status, "text": raw_text}

                        code_val = data.get("code")
                        is_success = False
                        if isinstance(code_val, str) and not data.get("message"):
                            is_success = True
                        elif r.status in (200, 204) and not isinstance(code_val, int):
                            is_success = True
                        elif isinstance(data.get("user_status"), dict) and data["user_status"].get("claimed_at"):
                            is_success = True
                        elif data.get("claimed_at"):
                            is_success = True

                        if is_success:
                            print(f"[QuestAPI] Claim Success on Quest {quest_id} (payload: {body}): {data}", flush=True)
                            return data

                        if data.get("captcha_key") or data.get("captcha_service") or "captcha" in str(data).lower():
                            print(f"[QuestAPI] Captcha Challenge on Quest {quest_id}: {data}", flush=True)
                            solved_token = await cls._try_solve_captcha(data, headers)
                            if solved_token:
                                captcha_headers = dict(headers)
                                captcha_headers["X-Captcha-Key"] = solved_token
                                if data.get("captcha_rqtoken"):
                                    captcha_headers["X-Captcha-Rqtoken"] = data["captcha_rqtoken"]
                                async with session.post(url, headers=captcha_headers, json=body, timeout=aiohttp.ClientTimeout(total=15)) as r_cap:
                                    cap_data = await r_cap.json()
                                    if r_cap.status in (200, 204) and not isinstance(cap_data.get("code"), int):
                                        print(f"[QuestAPI] Captcha bypass claim success: {cap_data}", flush=True)
                                        return cap_data

                        last_resp = data
                        err_code = data.get("code")
                        if isinstance(err_code, int) and err_code not in (50035, 40001, 10001):
                            break
            except Exception as e:
                last_resp = {"code": -1, "message": str(e)}

        return last_resp or {"code": -1, "message": "Claim failed"}


def is_claim_successful(claim_res: Any) -> Tuple[bool, Optional[str]]:
    """Evaluates whether claim succeeded. Returns (is_claimed, optional_reward_code)."""
    if not isinstance(claim_res, dict):
        return False, None
    if isinstance(claim_res.get("code"), int):
        return False, None
    if claim_res.get("message") and "error" in str(claim_res.get("message")).lower():
        return False, None

    reward_code = None
    if isinstance(claim_res.get("code"), str):
        reward_code = claim_res["code"]
    elif isinstance(claim_res.get("reward_code"), str):
        reward_code = claim_res["reward_code"]

    u_stat = claim_res.get("user_status")
    if isinstance(u_stat, dict) and u_stat.get("claimed_at"):
        return True, reward_code
    if claim_res.get("claimed_at"):
        return True, reward_code
    if reward_code:
        return True, reward_code
    if claim_res and not claim_res.get("code") and not claim_res.get("message"):
        return True, None

    return False, None

# ==============================================================================
# 3. VISUAL EMBED BUILDER (DUAL CHANNEL: LIVE EDITING & COMPLETION)
# ==============================================================================
class VisualEmbedEngine:
    @staticmethod
    def get_avatar_url(profile: Dict[str, Any], user: discord.User) -> str:
        av = profile.get("avatar")
        uid = profile.get("id")
        if av and uid:
            ext = "gif" if av.startswith("a_") else "png"
            return f"https://cdn.discordapp.com/avatars/{uid}/{av}.{ext}?size=256"
        return user.display_avatar.url

    @classmethod
    def build_in_progress_embed(
        cls,
        user: discord.User,
        profile: Dict[str, Any],
        token_count: int,
        current_quest_name: str,
        current_percent: int,
        completed_count: int,
        total_count: int,
        status_text: str = "กำลังดำเนินการ..."
    ) -> discord.Embed:
        disp_name = profile.get("global_name") or profile.get("username") or user.display_name
        avatar_url = cls.get_avatar_url(profile, user)
        now_str = datetime.now().strftime("%H:%M")

        # Visual progress bar (10 blocks)
        filled = int(current_percent / 10)
        bar = "▰" * filled + "▱" * (10 - filled)

        desc = (
            f"**<a:GR_146:1532677138443145250> PAYOMBOYZ AUTO QUEST RUNNING**\n\n"
            f"👤 **ผู้ใช้:** {user.mention} (`{disp_name}`)\n"
            f"🔑 **จำนวน Token:** `{token_count}` Account(s)\n"
            f"🎯 **เควสทั้งหมด:** `{total_count}` รายการ\n"
            f"✅ **ทำสำเร็จแล้ว:** `{completed_count}/{total_count}` รายการ\n\n"
            f"🔥 **เควสที่กำลังทำ:** `{current_quest_name}`\n"
            f"📊 **ความคืบหน้า:** `[{bar}] {current_percent}%`\n"
            f"⏳ **สถานะ:** {status_text}\n\n"
            f"*ระบบส่ง Heartbeat API v10 ไปยัง Discord โดยตรง • วันนี้ เวลา {now_str}*"
        )

        embed = discord.Embed(
            title="🚀 กำลังทำ Quest (Real-Time)",
            description=desc,
            color=0xFEE75C  # Discord Gold
        )
        embed.set_author(name=f"👻 {disp_name}", icon_url=avatar_url)
        embed.set_thumbnail(url=avatar_url)
        return embed

    @classmethod
    def build_completed_embed(
        cls,
        user: discord.User,
        profile: Dict[str, Any],
        token_count: int,
        results_list: List[Dict[str, Any]],
        banner_url: str
    ) -> discord.Embed:
        disp_name = profile.get("global_name") or profile.get("username") or user.display_name
        avatar_url = cls.get_avatar_url(profile, user)
        now_str = datetime.now().strftime("%H:%M")
        total = len(results_list)
        success_count = sum(1 for r in results_list if r.get("status") in ("success", "claimed"))
        claimed_count = sum(1 for r in results_list if r.get("status") == "claimed")

        lines = [
            f"**<a:ww:1532669871941488813> ระบบทำเควสเสร็จสิ้นเรียบร้อยแล้ว**",
            f"👤 **ผู้ใช้:** {user.mention} (`{disp_name}`)",
            f"📊 **ตรวจสอบทั้งหมด:** `{total}` เควส • **สำเร็จจริง:** `{success_count}` • **Claimed:** `{claimed_count}`\n"
        ]

        if not results_list:
            lines.append("⚠️ *บัญชีนี้ไม่มีแคมเปญเควสค้างอยู่ใน Discord ในขณะนี้*")
        else:
            for i, r in enumerate(results_list, start=1):
                is_claimed = r.get("status") == "claimed"
                code = r.get("reward_code")
                if is_claimed:
                    if code:
                        lines.append(f"**{i}. 🎁 {r['name']}**\n   • รับของรางวัลแล้ว (รหัส: `{code}`)")
                    else:
                        lines.append(f"**{i}. ✅ {r['name']}**\n   • รับของรางวัลเรียบร้อยแล้ว")
                elif r.get("status") == "success":
                    lines.append(f"**{i}. ⨁ {r['name']}**\n   • ทำเควสสำเร็จ (รอรับของรางวัลใน Discord)")
                else:
                    lines.append(f"**{i}. ⚠️ {r['name']}**\n   • ข้ามเควส")

        embed = discord.Embed(
            title="🎉 PAYOMBOYZ AUTO QUEST COMPLETED",
            description="\n".join(lines),
            color=0x57F287  # Discord Green
        )
        embed.set_author(name=f"👻 {disp_name}", icon_url=avatar_url)
        embed.set_thumbnail(url=avatar_url)
        if banner_url:
            embed.set_image(url=banner_url)
        embed.set_footer(text=f"PayomboyZ Quest Engine • สำเร็จจริงตามผลลัพธ์ Discord • วันนี้ เวลา {now_str}")
        return embed

# ==============================================================================
# 4. WORKER POOL & FULL PIPELINE EXECUTION
# ==============================================================================
class UserQuestJob:
    def __init__(
        self,
        guild: discord.Guild,
        user: discord.User,
        profile: Dict[str, Any],
        tokens: List[str],
        status_channel: discord.TextChannel,
        result_channel: discord.TextChannel,
        target_quest_ids: Optional[List[str]] = None
    ):
        self.guild = guild
        self.user = user
        self.profile = profile
        self.tokens = tokens
        self.status_channel = status_channel
        self.result_channel = result_channel
        self.target_quest_ids = [str(x) for x in target_quest_ids] if target_quest_ids else None

class PayomboyzWorkerPool:
    def __init__(self, concurrency: int = 3):
        self.queue: asyncio.Queue[UserQuestJob] = asyncio.Queue()
        self.concurrency = concurrency
        self.workers: List[asyncio.Task] = []

    def start(self):
        for i in range(self.concurrency):
            t = asyncio.create_task(self._worker_loop(i))
            self.workers.append(t)

    async def enqueue(self, job: UserQuestJob):
        await self.queue.put(job)

    async def _worker_loop(self, worker_id: int):
        while True:
            job = await self.queue.get()
            try:
                await self._process_job(job)
            except Exception as e:
                print(f"[Worker-{worker_id}] Error in job: {e}")
            finally:
                self.queue.task_done()

    async def _process_single_quest(
        self,
        token: str,
        quest: Dict[str, Any],
        username: str,
        job: UserQuestJob,
        status_msg: Optional[discord.Message],
        completed_q: int,
        total_q: int
    ) -> str:
        q_id = str(quest.get("id"))
        cfg = quest.get("config", {})
        msgs = cfg.get("messages", {})
        name = msgs.get("quest_name") or msgs.get("game_title") or quest.get("name") or f"Quest {q_id}"

        # 1. Dynamic Task Discovery matching GHOST X
        tasks = None
        if cfg.get("task_config_v2", {}).get("tasks"):
            tasks = cfg["task_config_v2"]["tasks"]
        elif cfg.get("task_config", {}).get("tasks"):
            tasks = cfg["task_config"]["tasks"]
        elif quest.get("task_config", {}).get("tasks"):
            tasks = quest["task_config"]["tasks"]
        elif cfg.get("tasks"):
            tasks = cfg["tasks"]
        elif quest.get("tasks"):
            tasks = quest["tasks"]
        else:
            for k in quest:
                if isinstance(quest[k], dict) and quest[k].get("tasks"):
                    tasks = quest[k]["tasks"]
                    break

        if not tasks:
            return "skipped"

        task_types = ['WATCH_VIDEO', 'PLAY_ON_DESKTOP', 'STREAM_ON_DESKTOP', 'PLAY_ACTIVITY', 'WATCH_VIDEO_ON_MOBILE']
        matched_task = next((t for t in task_types if t in tasks), None)
        if not matched_task:
            return "skipped"

        task_obj = tasks.get(matched_task, {})
        target = task_obj.get("target", 0)
        if target == 0:
            return "skipped"

        apps = task_obj.get("applications", [])
        app_id = None
        if apps and isinstance(apps, list) and len(apps) > 0:
            first_app = apps[0]
            if isinstance(first_app, dict):
                app_id = first_app.get("id")
            elif isinstance(first_app, (int, str)):
                app_id = str(first_app)

        if not app_id:
            app_id = (
                task_obj.get("application_id")
                or cfg.get("application", {}).get("id")
                or quest.get("application_id")
                or "1078737672201949245"
            )


        u_stat = quest.get("user_status") or {}
        progress = (u_stat.get("progress") or {}).get(matched_task, {}).get("value", 0)

        # 2. Check if already completed
        if progress >= target or u_stat.get("completed_at"):
            try:
                claim_res = await DiscordQuestV10Handler.claim_reward(token, q_id)
                is_claimed, rew_code = is_claim_successful(claim_res)
                if is_claimed:
                    return ("claimed", rew_code)
            except Exception:
                pass
            return ("success", None)

        # 3. Enroll if not enrolled
        if not u_stat.get("enrolled_at"):
            try:
                await DiscordQuestV10Handler.enroll(token, q_id)
                await asyncio.sleep(1)
            except Exception:
                return "skipped"

        # 4. Progress Loop with GHOST X stuck protection & rate limit handling
        is_video = matched_task in ('WATCH_VIDEO', 'WATCH_VIDEO_ON_MOBILE')
        video_timestamp = 0
        stuck_count = 0
        max_stuck = max(30, int(target / 20) + 10)
        error_count = 0
        max_errors = 5
        last_percent = -1

        # Fast-track video quests: send full target duration directly
        if is_video:
            try:
                fast_res = await DiscordQuestV10Handler.video_progress(token, q_id, float(target))
                fast_ustat = fast_res.get("user_status") if isinstance(fast_res.get("user_status"), dict) else fast_res
                if fast_res.get("completed") or (isinstance(fast_ustat, dict) and fast_ustat.get("completed_at")):
                    try:
                        claim_res = await DiscordQuestV10Handler.claim_reward(token, q_id)
                        is_claimed, rew_code = is_claim_successful(claim_res)
                        if is_claimed:
                            return ("claimed", rew_code)
                    except Exception:
                        pass
                    return ("success", None)
            except Exception:
                pass

        while progress < target:
            try:
                if is_video:
                    video_timestamp = min(target, video_timestamp + 60)
                    res = await DiscordQuestV10Handler.video_progress(token, q_id, float(video_timestamp))
                else:
                    res = await DiscordQuestV10Handler.heartbeat(token, q_id, str(app_id), terminal=False)

                # Error and permission checks
                res_code = res.get("code")
                res_msg = str(res.get("message", ""))

                if res_code == 0 and "403" in res_msg:
                    return "skipped"
                if res_code == 0 and "404" in res_msg:
                    return "skipped"
                if res_code == 0 and "429" in res_msg:
                    if status_msg:
                        try:
                            emb = VisualEmbedEngine.build_in_progress_embed(
                                job.user, job.profile, len(job.tokens), name,
                                min(100, int((progress / max(1, target)) * 100)),
                                completed_q, total_q, "⏳ ติด Rate limit กำลังรอ 30 วินาที..."
                            )
                            await status_msg.edit(content=f"{job.user.mention} (กำลังดำเนินการ)", embed=emb)
                        except Exception:
                            pass
                    await asyncio.sleep(30)
                    continue

                u_stat_res = res.get("user_status") if isinstance(res.get("user_status"), dict) else res

                # Check if Discord completed the quest
                if res.get("completed") or (isinstance(u_stat_res, dict) and u_stat_res.get("completed_at")):
                    try:
                        claim_res = await DiscordQuestV10Handler.claim_reward(token, q_id)
                        if claim_res and not claim_res.get("code"):
                            return "claimed"
                    except Exception:
                        pass
                    return "success"

                # Progress advancement check
                prog_map = u_stat_res.get("progress") if isinstance(u_stat_res, dict) else {}
                if not prog_map and isinstance(res.get("progress"), dict):
                    prog_map = res.get("progress")
                prog_dict = prog_map.get(matched_task, {}) if isinstance(prog_map, dict) else {}
                new_progress = prog_dict.get("value")

                if new_progress is not None and new_progress > progress:
                    progress = new_progress
                    stuck_count = 0
                else:
                    # In API v10 heartbeat, Discord often returns 200 without nested progress dict
                    progress += (60 if is_video else 30)
                    if new_progress is not None and new_progress == progress:
                        stuck_count += 1
                        if stuck_count >= max_stuck:
                            try:
                                refresh_data = await DiscordQuestV10Handler.fetch_quests(token)
                                rf_q = next((x for x in refresh_data.get("quests", []) if str(x.get("id")) == q_id), None)
                                if rf_q:
                                    rf_stat = rf_q.get("user_status") or {}
                                    if rf_stat.get("completed_at"):
                                        try:
                                            claim_res = await DiscordQuestV10Handler.claim_reward(token, q_id)
                                            is_claimed, rew_code = is_claim_successful(claim_res)
                                            if is_claimed:
                                                return ("claimed", rew_code)
                                        except Exception:
                                            pass
                                        return ("success", None)
                            except Exception:
                                pass
                            return "skipped"

                pct = min(100, int((progress / max(1, target)) * 100))
                if pct != last_percent:
                    last_percent = pct
                    if status_msg:
                        try:
                            desc_txt = f"กำลังดูวิดีโอ ({pct}%)" if is_video else f"กำลังส่ง Heartbeat ({progress}/{target}s - {pct}%)"
                            emb = VisualEmbedEngine.build_in_progress_embed(
                                job.user, job.profile, len(job.tokens), name, pct, completed_q, total_q, desc_txt
                            )
                            await status_msg.edit(content=f"{job.user.mention} (กำลังดำเนินการ)", embed=emb)
                        except Exception:
                            pass

                if progress >= target:
                    break

                # Sleep interval between updates
                await asyncio.sleep(3 if is_video else 20)

            except Exception as e:
                error_count += 1
                if error_count >= max_errors:
                    return "skipped"
                await asyncio.sleep(5)

        # 5. Terminal heartbeat
        try:
            if is_video:
                final_res = await DiscordQuestV10Handler.video_progress(token, q_id, float(target))
            else:
                final_res = await DiscordQuestV10Handler.heartbeat(token, q_id, str(app_id), terminal=True)

            u_stat_final = final_res.get("user_status") if isinstance(final_res.get("user_status"), dict) else final_res
            if final_res.get("completed") or (isinstance(u_stat_final, dict) and u_stat_final.get("completed_at")):
                try:
                    claim_res = await DiscordQuestV10Handler.claim_reward(token, q_id)
                    is_claimed, rew_code = is_claim_successful(claim_res)
                    if is_claimed:
                        return ("claimed", rew_code)
                except Exception:
                    pass
                return ("success", None)
        except Exception:
            pass

        # 6. Final verification & claim
        try:
            refresh_data = await DiscordQuestV10Handler.fetch_quests(token)
            rf_q = next((x for x in refresh_data.get("quests", []) if str(x.get("id")) == q_id), None)
            if rf_q:
                rf_stat = rf_q.get("user_status") or {}
                if rf_stat.get("completed_at"):
                    try:
                        claim_res = await DiscordQuestV10Handler.claim_reward(token, q_id)
                        is_claimed, rew_code = is_claim_successful(claim_res)
                        if is_claimed:
                            return ("claimed", rew_code)
                    except Exception:
                        pass
                    return ("success", None)
        except Exception:
            pass

        return "skipped"

    async def _process_job(self, job: UserQuestJob):
        all_results = []
        panel_cfg = state.get_panel(job.guild.id)
        banner_url = panel_cfg.get("banner_url", "")

        # Initial Status Message
        status_msg = None
        try:
            init_embed = VisualEmbedEngine.build_in_progress_embed(
                job.user, job.profile, len(job.tokens), "กำลังเชื่อมต่อ Discord...", 0, 0, 0, "กำลังดึงรายการเควสจากระบบ..."
            )
            status_msg = await job.status_channel.send(content=f"{job.user.mention}", embed=init_embed)
        except Exception as e:
            print(f"[Worker] Could not send initial embed: {e}")

        # Iterate through every submitted token
        for t_idx, token in enumerate(job.tokens, start=1):
            me = await DiscordQuestV10Handler.validate_token(token)
            if not me:
                continue

            username = me.get("username", f"Account #{t_idx}")
            quest_data = await DiscordQuestV10Handler.fetch_quests(token)
            raw_quests = quest_data.get("quests", [])

            # Filter active unexpired quests (including completed-but-unclaimed)
            active_quests = []
            now_utc = datetime.now(timezone.utc)
            for q in raw_quests:
                cfg = q.get("config", {})
                exp_str = cfg.get("expires_at")
                if exp_str:
                    try:
                        exp_dt = datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
                        if exp_dt <= now_utc:
                            continue
                    except Exception:
                        pass
                user_status = q.get("user_status") or {}
                # Include if not completed, or completed but reward not yet claimed
                if not user_status.get("completed_at") or not user_status.get("claimed_at"):
                    active_quests.append(q)

            if job.target_quest_ids:
                active_quests = [q for q in active_quests if str(q.get("id")) in job.target_quest_ids]

            total_q = len(active_quests)

            if total_q == 0:
                all_results.append({
                    "name": f"ทุกเควสในบัญชี ({username}) สำเร็จและรับรางวัลครบแล้ว",
                    "status": "success"
                })
                if status_msg:
                    try:
                        emb = VisualEmbedEngine.build_in_progress_embed(
                            job.user, job.profile, len(job.tokens), "ทำเควสและรับรางวัลครบแล้ว", 100, 1, 1, f"บัญชี {username} ไม่มีเควสค้างและรับของรางวัลครบถ้วนแล้ว"
                        )
                        await status_msg.edit(content=f"{job.user.mention} (เสร็จสมบูรณ์)", embed=emb)
                    except Exception:
                        pass
                continue


            # Pass 1: Process all active quests
            completed_q = 0
            skipped_quests = []
            for q in active_quests:
                cfg = q.get("config", {})
                msgs = cfg.get("messages", {})
                q_name = msgs.get("quest_name") or msgs.get("game_title") or q.get("name") or f"Quest {q.get('id')}"

                res_status = await self._process_single_quest(
                    token, q, username, job, status_msg, completed_q, total_q
                )

                status_val = res_status[0] if isinstance(res_status, tuple) else res_status
                reward_code_val = res_status[1] if isinstance(res_status, tuple) else None

                if status_val in ("success", "claimed"):
                    completed_q += 1
                    all_results.append({"name": q_name, "status": status_val, "reward_code": reward_code_val})
                else:
                    skipped_quests.append(q)

            # Pass 2: Retry loop for skipped quests (up to 2 retry passes like GHOST X)
            retry_count = 0
            max_retries = 2
            while retry_count < max_retries and skipped_quests:
                retry_count += 1
                if status_msg:
                    try:
                        emb = VisualEmbedEngine.build_in_progress_embed(
                            job.user, job.profile, len(job.tokens), f"รอบแก้ไข ({retry_count}/{max_retries})",
                            int((completed_q / max(1, total_q)) * 100), completed_q, total_q,
                            f"กำลังลองทำเควสที่ติดใหม่อีกครั้ง ({len(skipped_quests)} เควส)..."
                        )
                        await status_msg.edit(content=f"{job.user.mention} (กำลังดำเนินการ)", embed=emb)
                    except Exception:
                        pass
                await asyncio.sleep(10)

                new_skipped = []
                for q in skipped_quests:
                    cfg = q.get("config", {})
                    msgs = cfg.get("messages", {})
                    q_name = msgs.get("quest_name") or msgs.get("game_title") or q.get("name") or f"Quest {q.get('id')}"

                    retry_res = await self._process_single_quest(
                        token, q, username, job, status_msg, completed_q, total_q
                    )
                    ret_status_val = retry_res[0] if isinstance(retry_res, tuple) else retry_res
                    ret_reward_code = retry_res[1] if isinstance(retry_res, tuple) else None

                    if ret_status_val in ("success", "claimed"):
                        completed_q += 1
                        all_results.append({"name": q_name, "status": ret_status_val, "reward_code": ret_reward_code})
                    else:
                        new_skipped.append(q)

                skipped_quests = new_skipped

            for q in skipped_quests:
                cfg = q.get("config", {})
                msgs = cfg.get("messages", {})
                q_name = msgs.get("quest_name") or msgs.get("game_title") or q.get("name") or f"Quest {q.get('id')}"
                all_results.append({"name": q_name, "status": "skipped"})

        # Multi-tier delivery: result_channel -> user DM fallback (NEVER panel channel)
        sent = False
        try:
            done_embed = VisualEmbedEngine.build_completed_embed(
                job.user, job.profile, len(job.tokens), all_results, banner_url
            )
            # Tier 1: Dedicated result_channel (#quest-complete)
            if job.result_channel and hasattr(job.result_channel, "send"):
                try:
                    await job.result_channel.send(content=f"**{job.user.mention}**", embed=done_embed)
                    sent = True
                except Exception as ex:
                    print(f"[Worker] Could not send to result_channel: {ex}", flush=True)

            # Tier 2: Direct Message to user (if result_channel unreachable)
            if not sent:
                try:
                    await job.user.send(content=f"🎉 **ผลลัพธ์การทำ Auto Quest ของคุณ**", embed=done_embed)
                    sent = True
                except Exception as ex:
                    print(f"[Worker] Could not send DM to user: {ex}", flush=True)
        except Exception as e:
            print(f"[Worker] Delivery error: {e}", flush=True)


        # Final edit to status_msg
        if status_msg:
            try:
                final_status_embed = VisualEmbedEngine.build_in_progress_embed(
                    job.user, job.profile, len(job.tokens), "เสร็จสิ้นทุกรายการ", 100, len(all_results), len(all_results), "✅ ทำเควสเสร็จสมบูรณ์เรียบร้อยแล้ว!"
                )
                await status_msg.edit(content=f"{job.user.mention} (เสร็จสมบูรณ์)", embed=final_status_embed)
            except Exception:
                pass

worker_pool = PayomboyzWorkerPool(concurrency=7)

# ==============================================================================
# 5. UI COMPONENTS: EDITABLE PANEL & MULTI-TOKEN MODAL & QUEST SELECTION
# ==============================================================================
def build_quest_selection_embed(
    user: discord.User,
    profile: Dict[str, Any],
    quest_info_list: List[Dict[str, Any]],
    video_count: int,
    game_count: int,
    is_pro: bool
) -> discord.Embed:
    total_q = len(quest_info_list)
    pro_txt = "Pro Quest: ใช้งานได้ไม่จำกัด 💎" if is_pro else "สมาชิกทั่วไป (โควตา 3 ครั้ง/วัน)"

    desc_lines = [
        f"เควสที่เหลือทั้งหมด **{total_q}** เควส",
        f"video : `{video_count}` | game : `{game_count}`",
        f"สิทธิ์การใช้งาน : **{pro_txt}**",
        "",
        "**เลือกเควสที่ต้องการทำ:**"
    ]
    for item in quest_info_list[:15]:
        desc_lines.append(f"{item['index']}. {item['name']}")

    if len(quest_info_list) > 15:
        desc_lines.append(f"... และอีก {len(quest_info_list) - 15} เควส")

    embed = discord.Embed(
        title="||| เลือกเควสที่ต้องการทำ",
        description="\n".join(desc_lines),
        color=0x5865F2
    )
    av = profile.get("avatar")
    uid = profile.get("id")
    if av and uid:
        ext = "gif" if str(av).startswith("a_") else "png"
        embed.set_thumbnail(url=f"https://cdn.discordapp.com/avatars/{uid}/{av}.{ext}?size=128")
    embed.set_footer(text="เลือกเควสจากเมนูด้านล่าง แล้วกดปุ่มยืนยันเพื่อเริ่มทำทันที")
    return embed


class QuestSelectDropdown(discord.ui.Select):
    def __init__(self, quest_info_list: List[Dict[str, Any]], total_active: int):
        options = [
            discord.SelectOption(
                label=f"✅ เลือกทั้งหมด (ทำเควสที่เหลือทั้งหมด {total_active} รายการ)"[:100],
                value="ALL",
                description="เลือกทำทุกเควสที่ตรวจพบในบัญชี",
                emoji="✅",
                default=True
            )
        ]
        for item in quest_info_list[:24]:
            q_type = item["type"]
            q_name = item["name"]
            type_emoji = "🎬" if q_type == "video" else "🎮"
            opt_label = f"{item['index']}. {q_name}"[:100]
            opt_desc = f"ประเภท: {q_type.upper()}"[:50]
            options.append(
                discord.SelectOption(
                    label=opt_label,
                    value=str(item["id"]),
                    description=opt_desc,
                    emoji=type_emoji
                )
            )

        super().__init__(
            placeholder="เลือกเควสที่ต้องการทำ...",
            min_values=1,
            max_values=1,
            options=options,
            row=0
        )

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        self.view.selected_quest_id = selected
        for opt in self.options:
            opt.default = (opt.value == selected)
        await interaction.response.edit_message(view=self.view)


class QuestSelectionView(discord.ui.View):
    def __init__(
        self,
        user: discord.User,
        tokens: List[str],
        profile: Dict[str, Any],
        active_quests: List[Dict[str, Any]],
        quest_info_list: List[Dict[str, Any]],
        status_channel: discord.TextChannel,
        result_channel: discord.TextChannel,
        guild: discord.Guild,
        is_pro: bool
    ):
        super().__init__(timeout=300)
        self.user = user
        self.tokens = tokens
        self.profile = profile
        self.active_quests = active_quests
        self.quest_info_list = quest_info_list
        self.status_channel = status_channel
        self.result_channel = result_channel
        self.guild = guild
        self.is_pro = is_pro
        self.selected_quest_id = "ALL"

        self.add_item(QuestSelectDropdown(quest_info_list, len(active_quests)))

    @discord.ui.button(
        label="✅ ยืนยันเพื่อดำเนินการ",
        style=discord.ButtonStyle.success,
        row=1
    )
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ คุณไม่มีสิทธิ์กดปุ่มนี้", ephemeral=True)

        target_ids = None
        if self.selected_quest_id != "ALL":
            target_ids = [self.selected_quest_id]

        count_to_do = len(target_ids) if target_ids else len(self.active_quests)

        job = UserQuestJob(
            guild=self.guild,
            user=self.user,
            profile=self.profile,
            tokens=self.tokens,
            status_channel=self.status_channel,
            result_channel=self.result_channel,
            target_quest_ids=target_ids
        )
        await worker_pool.enqueue(job)

        status_url = f"https://discord.com/channels/{self.guild.id}/{self.status_channel.id}"
        check_view = discord.ui.View()
        check_view.add_item(discord.ui.Button(
            label="🔍 CHECK STATUS",
            style=discord.ButtonStyle.link,
            url=status_url
        ))

        embed = discord.Embed(
            title="🚀 กำลังทำ Quest",
            description=(
                f"เริ่มทำ Quest ทั้งหมด **{count_to_do}** รายการ...\n\n"
                f"📍 **ห้องสถานะ:** {self.status_channel.mention}\n"
                f"🏆 **ห้องผลลัพธ์:** {self.result_channel.mention}\n\n"
                f"👉 คลิกปุ่ม **[🔍 CHECK STATUS]** ด้านล่างเพื่อติดตามความคืบหน้าแบบเรียลไทม์"
            ),
            color=0x5865F2
        )
        embed.set_footer(text="PayomboyZ Quest Engine • ระบบออโต้กำลังประมวลผล")

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=check_view
        )


class AutoQuestSubmissionModal(ui.Modal, title="⚡ เข้าสู่ระบบทำ Quest ออโต้"):
    token_input = ui.TextInput(
        label="DISCORD TOKENS (1 บรรทัดต่อ 1 Token) *",
        style=discord.TextStyle.paragraph,
        placeholder="วาง User Token ของคุณที่นี่\n(สมาชิกทั่วไป: 1 Token | VIP: ใส่ได้พร้อมกันสูงสุด 7 Token)",
        required=True,
        min_length=20,
        max_length=4000
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        raw_text = self.token_input.value.strip()

        # Split multiple tokens by newline or comma
        tokens = [t.strip().strip('"').strip("'") for t in raw_text.replace(",", "\n").split("\n") if t.strip()]
        if not tokens:
            return await interaction.followup.send("❌ **ไม่พบ Token ที่ถูกต้อง!**", ephemeral=True)

        guild = interaction.guild
        if not guild:
            return await interaction.followup.send("⚠️ ใช้งานได้เฉพาะในเซิร์ฟเวอร์", ephemeral=True)

        # Check quota & VIP token concurrency limits (VIP: max 7 concurrent tokens)
        is_pro = state.is_user_pro(interaction.user.id, interaction.user, guild.id)
        if not is_pro and len(tokens) > 1:
            return await interaction.followup.send(
                f"⚠️ **สมาชิกทั่วไปจำกัดใส่ได้ครั้งละ 1 Token เท่านั้น!** (คุณใส่มา {len(tokens)} Token)\n"
                "💎 อัปเกรดเป็น **VIP Quest** เพื่อส่งได้พร้อมกันสูงสุด **7 Token** และไม่จำกัดโควตารายวัน!",
                ephemeral=True
            )
        if is_pro and len(tokens) > 7:
            tokens = tokens[:7]

        can_proceed, count = state.check_and_increment_quota(interaction.user.id, is_pro)
        if not can_proceed:
            return await interaction.followup.send(
                "⚠️ **คุณใช้โควตาทำเควสฟรีครบ 3 ครั้งสำหรับวันนี้แล้ว!**\n💎 อัปเกรดเป็น **VIP Quest** หรือใช้คำสั่ง `/redeem` เพื่อรับโควตาไม่จำกัด",
                ephemeral=True
            )

        # Validate the first token to fetch user profile
        primary_token = tokens[0]
        profile = await DiscordQuestV10Handler.validate_token(primary_token)
        if not profile:
            return await interaction.followup.send(
                "❌ **โทเค็นแรกไม่ถูกต้อง หรือหมดอายุแล้ว!**\nกรุณาตรวจสอบ Discord User Token ของคุณแล้วลองใหม่อีกครั้ง",
                ephemeral=True
            )

        # Resolve status and result channels safely (Guaranteed routing to #wait-questing and #quest-complete)
        cfg = state.get_guild(guild.id)
        status_ch_id = cfg.get("status_channel_id") or 1560942929063972944
        result_ch_id = cfg.get("result_channel_id") or 1560943311798145104

        status_ch = guild.get_channel(status_ch_id)
        if not status_ch:
            try:
                status_ch = await guild.fetch_channel(status_ch_id)
            except Exception:
                pass
        if not status_ch:
            status_ch = guild.get_channel(1560942929063972944) or interaction.channel

        result_ch = guild.get_channel(result_ch_id)
        if not result_ch:
            try:
                result_ch = await guild.fetch_channel(result_ch_id)
            except Exception:
                pass
        if not result_ch:
            result_ch = guild.get_channel(1560943311798145104) or interaction.channel

        if not hasattr(status_ch, "send") or not hasattr(result_ch, "send"):
            return await interaction.followup.send(
                "⚠️ ห้องสถานะหรือห้องผลลัพธ์ยังไม่ถูกตั้งค่า หรือบอทไม่มีสิทธิ์ส่งข้อความ กรุณาให้ผู้ดูแลเซิร์ฟเวอร์ใช้ `/quest channels`",
                ephemeral=True
            )


        # Fetch active quests from Discord
        quest_data = await DiscordQuestV10Handler.fetch_quests(primary_token)
        raw_quests = quest_data.get("quests", [])

        active_quests = []
        now_utc = datetime.now(timezone.utc)
        for q in raw_quests:
            cfg_q = q.get("config", {})
            exp_str = cfg_q.get("expires_at")
            if exp_str:
                try:
                    exp_dt = datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
                    if exp_dt <= now_utc:
                        continue
                except Exception:
                    pass
            user_status = q.get("user_status") or {}
            if not user_status.get("completed_at") or not user_status.get("claimed_at"):
                active_quests.append(q)

        if not active_quests:
            return await interaction.followup.send(
                "🎉 **บัญชี Discord ของคุณไม่มีเควสค้าง หรือทำเควสทั้งหมดและรับรางวัลครบแล้ว!**",
                ephemeral=True
            )

        video_count = 0
        game_count = 0
        quest_info_list = []
        for idx, q in enumerate(active_quests, start=1):
            q_id = str(q.get("id"))
            cfg_q = q.get("config", {})
            msgs = cfg_q.get("messages", {})
            q_name = msgs.get("quest_name") or msgs.get("game_title") or q.get("name") or f"Quest {q_id}"

            tasks = None
            if cfg_q.get("task_config_v2", {}).get("tasks"):
                tasks = cfg_q["task_config_v2"]["tasks"]
            elif cfg_q.get("task_config", {}).get("tasks"):
                tasks = cfg_q["task_config"]["tasks"]
            else:
                for k in q:
                    if isinstance(q[k], dict) and q[k].get("tasks"):
                        tasks = q[k]["tasks"]
                        break
            tasks = tasks or {}
            is_vid = any(t in tasks for t in ('WATCH_VIDEO', 'WATCH_VIDEO_ON_MOBILE'))
            if is_vid:
                video_count += 1
                q_type = "video"
            else:
                game_count += 1
                q_type = "game"

            quest_info_list.append({
                "index": idx,
                "id": q_id,
                "name": q_name,
                "type": q_type,
                "quest": q
            })

        embed = build_quest_selection_embed(
            user=interaction.user,
            profile=profile,
            quest_info_list=quest_info_list,
            video_count=video_count,
            game_count=game_count,
            is_pro=is_pro
        )
        view = QuestSelectionView(
            user=interaction.user,
            tokens=tokens,
            profile=profile,
            active_quests=active_quests,
            quest_info_list=quest_info_list,
            status_channel=status_ch,
            result_channel=result_ch,
            guild=guild,
            is_pro=is_pro
        )
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

class PanelEditModal(ui.Modal, title="🛠️ แก้ไขหน้าตา Panel"):
    panel_title = ui.TextInput(
        label="ชื่อหัวข้อ Panel (Title)",
        style=discord.TextStyle.short,
        required=True,
        max_length=100
    )
    panel_desc = ui.TextInput(
        label="ข้อความคำอธิบาย (Description)",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )
    banner_url = ui.TextInput(
        label="รูปลิงก์แบนเนอร์ (Banner Image URL)",
        style=discord.TextStyle.short,
        required=False,
        max_length=500
    )
    btn_label = ui.TextInput(
        label="ข้อความบนปุ่มกด (Button Label)",
        style=discord.TextStyle.short,
        required=True,
        max_length=50
    )
    color_hex = ui.TextInput(
        label="สี Embed Hex (เช่น 0x5865F2, #101010)",
        style=discord.TextStyle.short,
        required=False,
        max_length=20
    )

    def __init__(self, current_cfg: Dict[str, Any]):
        super().__init__()
        self.panel_title.default = current_cfg.get("title", "⚡ PAYOMBØYZ AUTO QUEST SYSTEM ⚡")
        self.panel_desc.default = current_cfg.get("description", "")
        self.banner_url.default = current_cfg.get("banner_url", "")
        self.btn_label.default = current_cfg.get("button_label", "🚀 เริ่มทำเควส (Start Quest)")
        self.color_hex.default = hex(current_cfg.get("color", 0x0B0C10))

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            return await interaction.response.send_message("ใช้ได้เฉพาะในเซิร์ฟเวอร์", ephemeral=True)

        col_val = 0x101010
        try:
            raw_c = self.color_hex.value.strip().replace("#", "0x")
            col_val = int(raw_c, 16)
        except Exception:
            pass

        state.update_panel(
            guild.id,
            title=self.panel_title.value.strip(),
            description=self.panel_desc.value.strip(),
            banner_url=self.banner_url.value.strip() or None,
            button_label=self.btn_label.value.strip(),
            color=col_val
        )

        await interaction.response.send_message(
            "✅ **บันทึกการตั้งค่า Panel เรียบร้อยแล้ว!**\nพิมพ์ `/panel` หรือ `/questpanel` เพื่อส่ง Panel โฉมใหม่ได้ทันที",
            ephemeral=True
        )

class QuestPremiumModal(ui.Modal, title="⭐ เติมคีย์พรีเมี่ยม Quest Premium"):
    key_input = ui.TextInput(
        label="รหัสคีย์ VIP (VIP KEY) *",
        style=discord.TextStyle.short,
        placeholder="วางรหัสคีย์ VIP เช่น PAYOMBOYZ-VIP-...",
        required=True,
        min_length=6,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        raw_key = self.key_input.value.strip()
        success = state.redeem_key(interaction.user.id, raw_key)
        if success:
            exp_str = state.pro_users.get(str(interaction.user.id), "")
            try:
                exp_dt = datetime.fromisoformat(exp_str)
                exp_fmt = exp_dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                exp_fmt = "30 วัน"
            embed = discord.Embed(
                title="🎉 เติมคีย์พรีเมี่ยมสำเร็จ!",
                description=(
                    f"ยินดีด้วย {interaction.user.mention} คุณได้รับการอัปเกรดเป็น **Pro Quest** เรียบร้อยแล้ว!\n"
                    f"⏱️ **วันหมดอายุ:** `{exp_fmt}`\n"
                    f"⚡ **สิทธิ์พิเศษ:** ทำเควสได้ไม่จำกัดโควตา ไม่จำกัดจำนวนครั้ง!"
                ),
                color=0xFEE75C
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(
                "❌ **คีย์ VIP ไม่ถูกต้อง หรือถูกใช้งานไปแล้ว!**\nกรุณาติดต่อแอดมินหรือสั่งซื้อคีย์ใหม่",
                ephemeral=True
            )

class QuestPanelActionSelect(ui.Select):
    """Modern Dropdown Selection for PayomboyZ AutoQuest System."""
    def __init__(self, guild_id: Optional[int] = None):
        options = [
            discord.SelectOption(
                label="🚀 เริ่มทำเควสทันที (Start Auto Quest)",
                value="start",
                description="ส่ง Discord Token เพื่อรันเควสอัตโนมัติ (ใส่ได้หลายบัญชีพร้อมกัน)",
                emoji="🚀"
            ),
            discord.SelectOption(
                label="🎯 ตรวจสอบเควสที่เปิดอยู่ (Active Quests)",
                value="quests",
                description="ดูรายชื่อเควส Discord และของรางวัลทั้งหมดที่ระบบรองรับ",
                emoji="🎯"
            ),
            discord.SelectOption(
                label="📡 เช็คสถานะระบบ & คิวเรียลไทม์ (Live Status)",
                value="status",
                description="ตรวจสอบสถานะ Worker, เควสที่ทำสำเร็จ และคิวงาน",
                emoji="📡"
            ),
            discord.SelectOption(
                label="💎 เติมคีย์ VIP / สิทธิ์ Pro (Redeem Key)",
                value="redeem",
                description="แลกรับสิทธิ์ Pro Quest เพื่อปลดล็อกโควตาไม่จำกัด 30 วัน",
                emoji="💎"
            ),
            discord.SelectOption(
                label="📊 ตรวจสอบโควตาของฉัน (My Quotas)",
                value="quota",
                description="เช็คระดับสมาชิกและจำนวนโควตาทำเควสคงเหลือวันนี้",
                emoji="📊"
            ),
            discord.SelectOption(
                label="❓ วิธีดึง Token & ความปลอดภัย (Guide & FAQ)",
                value="guide",
                description="คู่มือวิธีค้นหา Discord User Token บนคอมและมือถืออย่างปลอดภัย",
                emoji="❓"
            ),
        ]
        cid = f"payomboyz_select_{guild_id}" if guild_id else "payomboyz_panel_select"
        super().__init__(
            placeholder="⚡ เลือกรายการที่ต้องการทำ (Select Action)...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=cid,
            row=0
        )

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0] if self.values else ""
        view: PersistentQuestPanelView = self.view
        guild_id = interaction.guild_id or (view.guild_id if view else None)

        if choice == "start":
            cfg = state.get_panel(guild_id)
            if not cfg.get("is_open", True):
                reason = cfg.get("closed_reason", "ระบบปิดปรับปรุงชั่วคราว")
                return await interaction.response.send_message(f"🔒 **{reason}**", ephemeral=True)
            await interaction.response.send_modal(AutoQuestSubmissionModal())

        elif choice == "quests":
            embed = discord.Embed(
                title="🎯 รายชื่อเควส Discord ที่เปิดอยู่ (Active Quests)",
                description=(
                    "```ansi\n"
                    "\u001b[1;32m● DISCORD QUESTS API v10 RUNTIME ACTIVE\u001b[0m\n"
                    "```\n"
                    "ระบบ **PayomboyZ Quest Engine** รองรับการทำทุกเควสแบบ Multi-Threaded อัตโนมัติ:\n\n"
                    "🎮 **Valorant** • VCT Masters Exclusive Gun Buddy & Player Card\n"
                    "⛏️ **Minecraft** • 15th Anniversary Cape & Special Badges\n"
                    "⚔️ **Genshin Impact / Honkai: Star Rail** • Primogems / Stellar Jades & Avatars\n"
                    "🏎️ **Rocket League / Fortnite** • Limited Wheels, Decals & Bundle Rewards\n"
                    "🔮 **Discord Specials** • Discord Orbs, Profile Badges & Nitro Promo Trials\n\n"
                    "────────────────────────────────────────────\n"
                    "💡 **เคล็ดลับ:** คุณสามารถใส่ **หลาย Token พร้อมกัน** ในปุ่มเดียว ระบบจะรับเควสและเคลียร์ให้ทุกบัญชีพร้อมกัน 100%!"
                ),
                color=0x0B0C10
            )
            embed.set_footer(text="⚡ PayomboyZ Quest Protocol • เคลียร์เควสและ Claim ของรางวัลอัตโนมัติ")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif choice == "status":
            guild = interaction.guild
            cfg = state.get_guild(guild.id) if guild else {}
            status_ch_id = cfg.get("status_channel_id")
            result_ch_id = cfg.get("result_channel_id")
            status_mention = f"<#{status_ch_id}>" if status_ch_id else "*ยังไม่ตั้งค่า*"
            result_mention = f"<#{result_ch_id}>" if result_ch_id else "*ยังไม่ตั้งค่า*"
            completed_total = sum(len(v) for v in state.history.values())
            queue_len = worker_pool.queue.qsize() if hasattr(worker_pool, "queue") else 0

            embed = discord.Embed(
                title="📡 สถานะระบบ PayomboyZ Quest Engine",
                description=(
                    f"🟢 **สถานะเครื่องจักร:** `ONLINE • HIGH-SPEED RUNTIME`\n"
                    f"⚡ **เวอร์ชันโปรโตคอล:** `Discord Quests API v10`\n"
                    f"👥 **Worker Pool:** `5 Multi-Threaded Workers`\n"
                    f"📦 **งานในคิวปัจจุบัน:** `{queue_len}` งาน\n"
                    f"🏆 **จำนวนเควสที่ทำสำเร็จแล้ว:** `{completed_total}` ครั้ง\n\n"
                    "────────────────────────────────────────────\n"
                    f"📍 **ห้องสถานะเรียลไทม์:** {status_mention}\n"
                    f"📬 **ห้องผลลัพธ์เควส:** {result_mention}\n"
                    "────────────────────────────────────────────"
                ),
                color=0x0B0C10
            )
            embed.set_footer(text="⚡ PayomboyZ Engine • Real-Time Heartbeat Active")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif choice == "redeem":
            await interaction.response.send_modal(QuestPremiumModal())

        elif choice == "quota":
            if view:
                await view.on_info_clicked(interaction)
            else:
                await interaction.response.send_message("❌ ไม่สามารถดึงข้อมูลได้ในขณะนี้", ephemeral=True)

        elif choice == "guide":
            embed = discord.Embed(
                title="❓ วิธีค้นหา Discord User Token อย่างปลอดภัย",
                description=(
                    "### 💻 วิธีดึง Token บนคอมพิวเตอร์ (PC / Mac):\n"
                    "1. เปิดเว็บเบราว์เซอร์ (Chrome, Edge, Brave, Opera) เข้าเว็บ **[discord.com/channels/@me](https://discord.com/channels/@me)**\n"
                    "2. กดปุ่ม `Ctrl + Shift + I` (บน Mac: `Cmd + Option + I`) เพื่อเปิด Developer Tools\n"
                    "3. คลิกไปที่แท็บ **Network** (เครือข่าย)\n"
                    "4. ในช่องค้นหา (Filter) ด้านบน พิมพ์คำว่า `/api`\n"
                    "5. คลิกสลับไปที่ห้องแชทหรือเพื่อนคนไหนก็ได้ใน Discord 1 ครั้ง\n"
                    "6. คลิกเลือก Request รายการใดรายการหนึ่งในตาราง -> เลื่อนดูแถบ **Request Headers**\n"
                    "7. คัดลอกข้อความยาวๆ หลังคำว่า **`authorization:`** ทั้งหมดมาวาง\n\n"
                    "### 📱 วิธีดึง Token บนมือถือ (Android / iOS):\n"
                    "1. เปิด Discord ผ่านเบราว์เซอร์ **Kiwi Browser** (Android) หรือ Safari Web\n"
                    "2. เปิด DevTools หรือพิมพ์ JavaScript ใน Console:\n"
                    "```javascript\n"
                    "(webpackChunkdiscord_app.push([[''],{},e=>{m=[];for(let c in e.c)m.push(e.c[c])}]),m).find(m=>m?.exports?.default?.getToken!==void 0).exports.default.getToken()\n"
                    "```\n"
                    "────────────────────────────────────────────\n"
                    "🔒 **นโยบายความปลอดภัยสูงสุด (PayomboyZ Safe-Execution):**\n"
                    "• บอทจะไม่นำ Token ไปส่งต่อ, ไม่บันทึกลงฐานข้อมูล, และไม่เปลี่ยนรหัสผ่าน\n"
                    "• Token จะถูกใช้เพื่อยิง API Heartbeat ของเควสใน RAM ชั่วคราว และจะถูกทำลายทิ้งทันทีเมื่อทำเสร็จ"
                ),
                color=0x0B0C10
            )
            embed.set_footer(text="⚡ PayomboyZ Security • ไม่บันทึก Token ปลอดภัย 100%")
            await interaction.response.send_message(embed=embed, ephemeral=True)


class PersistentQuestPanelView(ui.View):
    """
    Next-Gen Premium Interactive Panel for PayomboyZ Auto Quest:
      Row 0: [🟢 START NOW] (Green Primary Action) & [🔴 ENDED PAGE / STATUS] (Red Secondary Action)
      Row 1: [💎 VIP PREMIUM] (Blurple) & [⚡ เช็คสิทธิ์ & วิธีใช้] (Grey)
    """
    def __init__(self, guild_id: Optional[int] = None):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        cfg = state.get_panel(guild_id) if guild_id else state.get_default_panel()
        
        is_open = cfg.get("is_open", True)

        # Row 0: Button 1: [🟢 START NOW] (Green/Success)
        start_cid = f"payomboyz_start_btn_{guild_id}" if guild_id else "payomboyz_start_btn"
        self.start_btn = ui.Button(
            label="START NOW" if is_open else "SYSTEM CLOSED",
            style=discord.ButtonStyle.success if is_open else discord.ButtonStyle.secondary,
            emoji="🟢" if is_open else "🔒",
            disabled=not is_open,
            custom_id=start_cid,
            row=0
        )
        self.start_btn.callback = self.on_start_clicked
        self.add_item(self.start_btn)

        # Row 0: Button 2: [🔑 GET TOKEN] (Primary Blurple)
        token_cid = f"payomboyz_token_btn_{guild_id}" if guild_id else "payomboyz_token_btn"
        self.token_btn = ui.Button(
            label="GET TOKEN",
            style=discord.ButtonStyle.primary,
            emoji="🔑",
            custom_id=token_cid,
            row=0
        )
        self.token_btn.callback = self.on_token_clicked
        self.add_item(self.token_btn)

        # Row 0: Button 3: [🔴 ENDED PAGE / STATUS] (Red/Danger)
        status_cid = f"payomboyz_status_btn_{guild_id}" if guild_id else "payomboyz_status_btn"
        self.status_btn = ui.Button(
            label="ENDED PAGE",
            style=discord.ButtonStyle.danger,
            emoji="🔴",
            custom_id=status_cid,
            row=0
        )
        self.status_btn.callback = self.on_status_clicked
        self.add_item(self.status_btn)


        # Row 1: Button 3: [💎 VIP PREMIUM] (Primary Blurple)
        prem_cid = f"payomboyz_premium_btn_{guild_id}" if guild_id else "payomboyz_premium_btn"
        self.premium_btn = ui.Button(
            label="VIP PREMIUM",
            style=discord.ButtonStyle.primary,
            emoji="💎",
            custom_id=prem_cid,
            row=1
        )
        self.premium_btn.callback = self.on_premium_clicked
        self.add_item(self.premium_btn)

        # Row 1: Button 4: [⚡ ตรวจสอบสิทธิ์ & วิธีใช้] (Secondary Grey)
        info_cid = f"payomboyz_info_btn_{guild_id}" if guild_id else "payomboyz_info_btn"
        self.info_btn = ui.Button(
            label="ตรวจสอบสิทธิ์ & วิธีใช้",
            style=discord.ButtonStyle.secondary,
            emoji="⚡",
            custom_id=info_cid,
            row=1
        )
        self.info_btn.callback = self.on_info_clicked
        self.add_item(self.info_btn)

    async def on_status_clicked(self, interaction: discord.Interaction):
        """Shows quick status summary and real-time links."""
        g_cfg = state.get_guild(interaction.guild_id) if interaction.guild_id else {}
        res_ch_id = g_cfg.get("result_channel_id")
        stat_ch_id = g_cfg.get("status_channel_id")

        res_mention = f"<#{res_ch_id}>" if res_ch_id else "`ยังไม่ได้ตั้งค่า`"
        stat_mention = f"<#{stat_ch_id}>" if stat_ch_id else "`ยังไม่ได้ตั้งค่า`"

        embed = discord.Embed(
            title="🔴 PAYOMBØYZ QUEST STATUS & LOGS",
            description=(
                "**📌 ช่องติดตามสถานะเควสและผลลัพธ์การทำงาน:**\n\n"
                f"• 📡 **ห้องความคืบหน้าสด (Live Progress):** {stat_mention}\n"
                f"• 🎁 **ห้องส่งของรางวัลเมื่อเสร็จ (Claim Logs):** {res_mention}\n\n"
                "────────────────────────────────────────────\n"
                "⚡ *ระบบรองรับ Discord Quests v10 Heartbeat แบบเรียลไทม์ 100%*"
            ),
            color=0xED4245
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def on_token_clicked(self, interaction: discord.Interaction):
        """Opens interactive Token Finder helper directly."""
        try:
            from cogs.token_finder import build_find_token_panel_embed, FindTokenPanelView
            embed = build_find_token_panel_embed()
            view = FindTokenPanelView()
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ ไม่สามารถเปิดระบบดึง Token ได้: {e}", ephemeral=True)

    async def on_start_clicked(self, interaction: discord.Interaction):

        cfg = state.get_panel(interaction.guild_id or self.guild_id)
        if not cfg.get("is_open", True):
            reason = cfg.get("closed_reason", "ระบบปิดปรับปรุงชั่วคราว")
            return await interaction.response.send_message(f"🔒 **{reason}**", ephemeral=True)
        modal = AutoQuestSubmissionModal()
        await interaction.response.send_modal(modal)

    async def on_premium_clicked(self, interaction: discord.Interaction):
        modal = QuestPremiumModal()
        await interaction.response.send_modal(modal)

    async def on_info_clicked(self, interaction: discord.Interaction):
        st = state.get_user_status(interaction.user.id, interaction.user if isinstance(interaction.user, discord.Member) else None, interaction.guild_id)
        is_pro = st.get("is_pro", False)
        pro_status = "💎 **PRO (โควตาไม่จำกัด)**" if is_pro else "👤 **สมาชิกทั่วไป (โควตาฟรี 3 ครั้ง/วัน)**"
        expiry_info = f"⏱️ **วันหมดอายุ Pro:** `{st.get('pro_expiry')}`" if st.get("pro_expiry") else ""
        quota_line = "📊 **โควตาวันนี้:** `ไม่จำกัด`" if is_pro else f"📊 **โควตาวันนี้:** `{st.get('quota_used')}/3 ครั้ง` (เหลือ `{st.get('quota_remaining')}` ครั้ง)"

        info_embed = discord.Embed(
            title="⚡ ข้อมูลสิทธิ์ผู้ใช้งาน & วิธีค้นหา Token",
            description=(
                f"👤 **ผู้ใช้:** {interaction.user.mention} (`{interaction.user.name}`)\n"
                f"🏷️ **ระดับสมาชิก:** {pro_status}\n"
                f"{quota_line}\n"
                f"{expiry_info}\n\n"
                "────────────────────────────────────────────\n"
                "💡 **เคล็ดลับ:** หากต้องการเติมคีย์เพื่อปลดล็อกโควตาไม่จำกัด สามารถเลือกเมนู **[💎 เติมคีย์ VIP]** บน Dropdown หรือคลิกปุ่มด้านล่างได้ทันที"
            ),
            color=0x0B0C10
        )
        logo_url = state.get_panel(interaction.guild_id or self.guild_id).get("logo_url")
        if logo_url:
            info_embed.set_thumbnail(url=logo_url)
        info_embed.set_footer(text="PayomboyZ Quest Engine • ปลอดภัย ส่งตรง API v10")
        await interaction.response.send_message(embed=info_embed, ephemeral=True)


def get_wing_emojis(guild_id: Optional[int] = None) -> Tuple[str, str]:
    if str(guild_id) == "1553087781595775007":
        return "<a:pbg_wing_l:1562553247103844374>", "<a:pbg_wing_r:1562553249456988190>"
    return "<a:pbg_wing_l:1562553182859563150>", "<a:pbg_wing_r:1562553185325940748>"

def build_panel_embed(guild_id: int) -> Tuple[discord.Embed, List[discord.File]]:
    """Builds premium aesthetic panel embed with custom logo and PayomboyZ Cyber Red banner."""
    cfg = state.get_panel(guild_id)
    raw_title = cfg.get("title", "")
    wing_l, wing_r = get_wing_emojis(guild_id)
    if not raw_title or "928014477973135400" in raw_title or "PAYOMBOYZ" in raw_title or "PAYOMBØYZ" in raw_title or "🪽" in raw_title:
        title = f"{wing_l} **AUTO QUEST SYSTEM** {wing_r}"
    else:
        title = raw_title



    desc = (
        "> 🎮 **ระบบทำเควส Discord Quests อัตโนมัติ (API v10 Protocol)**\n"
        "> 🚀 **ปลดล็อกของรางวัลทุกเควส: Valorant, Minecraft, Genshin, Fortnite & Orbs**\n"
        "> ⭐ **รองรับการใส่หลาย TOKEN พร้อมกัน (VIP สูงสุด 7 Tokens)**\n"
        "> 🟢 **กดปุ่มด้านล่างเพื่อเริ่มทำเควส หรือตรวจสอบสิทธิ์การใช้งานได้ทันที**\n\n"
        "────────────────────────────────────────────\n"
        "**POWERED BY PAYOMBOYZ AUTOQUEST PREMIUM**"
    )

    embed = discord.Embed(
        title=title,
        description=desc,
        color=cfg.get("color") or 0x0B0C10
    )

    files: List[discord.File] = []

    # 1. Logo / Thumbnail
    logo_file = cfg.get("logo_path") or LOGO_PATH
    if os.path.exists(logo_file):
        files.append(discord.File(logo_file, filename="payomboyz_logo.png"))
        embed.set_thumbnail(url="attachment://payomboyz_logo.png")
        embed.set_author(name="PAYOMBØYZ AUTO QUEST • CYBER RUNTIME", icon_url="attachment://payomboyz_logo.png")
        embed.set_footer(text="⚡ Powered by PayomboyZ Engine • Discord Quests v10", icon_url="attachment://payomboyz_logo.png")
    elif cfg.get("logo_url"):
        embed.set_thumbnail(url=cfg["logo_url"])
        embed.set_author(name="PAYOMBØYZ AUTO QUEST • CYBER RUNTIME", icon_url=cfg["logo_url"])
        embed.set_footer(text="⚡ Powered by PayomboyZ Engine • Discord Quests v10", icon_url=cfg["logo_url"])
    else:
        embed.set_footer(text="⚡ Powered by PayomboyZ Engine • Discord Quests v10")

    # 2. Cyber Red Banner
    banner_file = cfg.get("banner_path") or BANNER_PATH
    # Always prefer physical local PayomboyZ banner over outdated external URLs
    if os.path.exists(banner_file):
        files.append(discord.File(banner_file, filename="payomboyz_banner.png"))
        embed.set_image(url="attachment://payomboyz_banner.png")
    elif cfg.get("banner_url") and "imgz.io" not in cfg["banner_url"]:
        embed.set_image(url=cfg["banner_url"])

    return embed, files

OFFICIAL_PAYOMBOYZ_BANNER_URL = "https://cdn.discordapp.com/attachments/1549803085273112580/1561260692512702585/payomboyz_banner.png"

def build_quest_v2_payload(guild_id: Optional[int] = None) -> dict:
    """Builds raw JSON payload for Discord Components V2 Container message (flags: 32768)."""
    cfg = state.get_panel(guild_id) if guild_id else state.get_default_panel()
    banner = cfg.get("banner_url")
    if not banner or "imgz.io" in banner:
        banner = OFFICIAL_PAYOMBOYZ_BANNER_URL

    wing_l, wing_r = get_wing_emojis(guild_id)

    return {
        "flags": 32768,
        "components": [
            {
                "type": 17,
                "accent_color": cfg.get("color") or 0x101010,
                "components": [
                    {
                        "type": 10,
                        "content": f"## {wing_l} **AUTO QUEST SYSTEM** {wing_r}\n### ⚡ **PAYOMBØYZ AUTOMATION ENGINE**"
                    },
                    {"type": 14, "divider": True, "spacing": 1},
                    {
                        "type": 10,
                        "content": (
                            "> 🎮 **ระบบทำเควส Discord Quests อัตโนมัติ (API v10 Protocol)**\n"
                            "> 🚀 **ปลดล็อกของรางวัลทุกเควส: Valorant, Minecraft, Genshin, Fortnite & Orbs**\n"
                            "> ⭐ **รองรับการใส่หลาย TOKEN พร้อมกัน (VIP สูงสุด 7 Tokens)**\n"
                            "> 🟢 **กดปุ่มด้านล่างเพื่อเริ่มทำเควส หรือตรวจสอบสิทธิ์การใช้งานได้ทันที**"
                        )
                    },
                    {"type": 14, "divider": True, "spacing": 1},
                    {
                        "type": 1,
                        "components": [
                            {
                                "type": 2,
                                "style": 3,
                                "custom_id": "full_auto_quest",
                                "label": "START NOW",
                                "emoji": {"name": "🟢"}
                            },
                            {
                                "type": 2,
                                "style": 2,
                                "custom_id": "btn_open_token_finder",
                                "label": "GET TOKEN",
                                "emoji": {"name": "🔑"}
                            },
                            {
                                "type": 2,
                                "style": 2,
                                "custom_id": "show_ended_page",
                                "label": "ENDED PAGE",
                                "emoji": {"name": "🔴"}
                            }
                        ]
                    },

                    {
                        "type": 1,
                        "components": [
                            {
                                "type": 2,
                                "style": 1,
                                "custom_id": "payomboyz_premium_btn",
                                "label": "VIP PREMIUM",
                                "emoji": {"name": "💎"}
                            },
                            {
                                "type": 2,
                                "style": 2,
                                "custom_id": "payomboyz_info_btn",
                                "label": "ตรวจสอบสิทธิ์ & วิธีใช้",
                                "emoji": {"name": "⚡"}
                            }
                        ]
                    },
                    {"type": 14, "divider": True, "spacing": 1},
                    {
                        "type": 10,
                        "content": "**POWERED BY PAYOMBOYZ AUTOQUEST PREMIUM**"
                    },
                    {"type": 14, "divider": True, "spacing": 1},
                    {
                        "type": 12,
                        "items": [
                            {
                                "media": {
                                    "url": banner
                                }
                            }
                        ]
                    }
                ]
            }
        ]
    }

async def send_quest_v2_panel(channel_id: int, bot_token: str, guild_id: Optional[int] = None) -> Tuple[bool, Any]:
    """Dispatches native Discord Components V2 message directly via REST API v10."""
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {bot_token}", "Content-Type": "application/json"}
    payload = build_quest_v2_payload(guild_id)
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as r:
            try:
                data = await r.json()
            except Exception:
                data = await r.text()
            return r.status == 200, data

# ==============================================================================
# 6. DISCORD BOT CLIENT & SLASH COMMANDS
# ==============================================================================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# --- Slash Command: /panel or /questpanel ---
@bot.tree.command(name="panel", description="ส่งแผงควบคุมทำเควส PayomboyZ Auto Quest (Components V2 Native)")
@app_commands.default_permissions(administrator=True)
async def cmd_panel(interaction: discord.Interaction):
    if not interaction.guild:
        return await interaction.response.send_message("ใช้งานได้เฉพาะในเซิร์ฟเวอร์", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    bot_token = bot.http.token
    ok, res = await send_quest_v2_panel(interaction.channel_id, bot_token, interaction.guild_id)
    if not ok:
        embed, files = build_panel_embed(interaction.guild_id)
        view = PersistentQuestPanelView(interaction.guild_id)
        sent_msg = await interaction.channel.send(embed=embed, files=files, view=view)
        if sent_msg.embeds and sent_msg.embeds[0].thumbnail and sent_msg.embeds[0].thumbnail.url:
            state.update_panel(interaction.guild_id, logo_url=sent_msg.embeds[0].thumbnail.url)
    await interaction.followup.send("✅ ส่งแผงควบคุมทำเควส (Components V2 Native Container) เรียบร้อยแล้ว", ephemeral=True)

@bot.tree.command(name="questpanel", description="เปิดแผงตั้งค่า Quest ด้วยปุ่ม (รองรับการแก้ไข)")
@app_commands.default_permissions(administrator=True)
async def cmd_questpanel(interaction: discord.Interaction):
    await cmd_panel.callback(interaction)

# --- Slash Command: /editpanel ---
@bot.tree.command(name="editpanel", description="แก้ไขข้อความ รูปภาพ สี และปุ่มของ Panel แบบ Real-Time")
@app_commands.default_permissions(administrator=True)
async def cmd_editpanel(interaction: discord.Interaction):
    if not interaction.guild:
        return await interaction.response.send_message("ใช้งานได้เฉพาะในเซิร์ฟเวอร์", ephemeral=True)
    cfg = state.get_panel(interaction.guild_id)
    modal = PanelEditModal(cfg)
    await interaction.response.send_modal(modal)

# --- Slash Command: /setchannels ---
@bot.tree.command(name="setchannels", description="ตั้งค่าห้องสถานะเรียลไทม์ และห้องผลลัพธ์เควส")
@app_commands.describe(
    status_channel="ห้องแสดงสถานะการทำเควสแบบเรียลไทม์ (Live-Edit)",
    result_channel="ห้องแจ้งเตือนผลลัพธ์เควสเมื่อทำเสร็จสิ้น"
)
@app_commands.default_permissions(administrator=True)
async def cmd_setchannels(
    interaction: discord.Interaction,
    status_channel: discord.TextChannel,
    result_channel: discord.TextChannel
):
    state.set_guild_channels(interaction.guild_id, status_channel.id, result_channel.id)
    await interaction.response.send_message(
        f"✅ **ตั้งค่าห้องสำเร็จ!**\n"
        f"• ห้องสถานะเรียลไทม์: {status_channel.mention}\n"
        f"• ห้องผลลัพธ์เสร็จสิ้น: {result_channel.mention}",
        ephemeral=True
    )

# Compatibility: /setquest
@bot.tree.command(name="setquest", description="ตั้งค่าห้องสถานะและห้องผลลัพธ์ Quest แยกกัน")
@app_commands.default_permissions(administrator=True)
async def cmd_setquest(
    interaction: discord.Interaction,
    status_channel: discord.TextChannel,
    result_channel: discord.TextChannel
):
    await cmd_setchannels.callback(interaction, status_channel, result_channel)

# --- Slash Command: /toggle-system ---
@bot.tree.command(name="toggle-system", description="เปิด หรือ ปิดระบบทำเควสชั่วคราว (Maintenance Mode)")
@app_commands.describe(is_open="เลือก True เพื่อเปิดระบบ, False เพื่อปิดระบบชั่วคราว")
@app_commands.default_permissions(administrator=True)
async def cmd_toggle_system(interaction: discord.Interaction, is_open: bool):
    state.update_panel(interaction.guild_id, is_open=is_open)
    st = "🟢 **เปิดระบบแล้ว**" if is_open else "🔴 **ปิดระบบชั่วคราวแล้ว**"
    await interaction.response.send_message(f"✅ บันทึกสถานะ: {st}\n(กดส่ง `/panel` ใหม่เพื่อให้ปุ่มอัปเดตสถานะ)", ephemeral=True)

# --- Slash Command: /setpro ---
@bot.tree.command(name="setpro", description="ตั้งค่ายศ Pro Quest ประจำเซิร์ฟเวอร์ (ไม่จำกัดโควตา)")
@app_commands.describe(role="ยศที่ได้รับสิทธิ์ Pro Quest")
@app_commands.default_permissions(administrator=True)
async def cmd_setpro(interaction: discord.Interaction, role: discord.Role):
    state.set_pro_role(interaction.guild_id, role.id)
    await interaction.response.send_message(f"✅ ตั้งค่ายศ Pro Quest เป็น: {role.mention}", ephemeral=True)

# --- Slash Command: /setrolepro (DevilQuest Compatibility Alias) ---
@bot.tree.command(name="setrolepro", description="ตั้งค่ายศโปรประจำเซิร์ฟเวอร์ (DevilQuest Compatibility)")
@app_commands.describe(role="ยศที่ได้รับสิทธิ์ Pro Quest")
@app_commands.default_permissions(administrator=True)
async def cmd_setrolepro(interaction: discord.Interaction, role: discord.Role):
    await cmd_setpro.callback(interaction, role)

# --- Slash Command: /setautoquest (DevilQuest Compatibility) ---
@bot.tree.command(name="setautoquest", description="ตั้งค่าและส่งแผงควบคุมทำเควสลงในห้องที่กำหนด (DevilQuest Parity)")
@app_commands.describe(channel="ห้องที่ต้องการให้ส่งแผงควบคุมทำเควส")
@app_commands.default_permissions(administrator=True)
async def cmd_setautoquest(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.guild:
        return await interaction.response.send_message("ใช้งานได้เฉพาะในเซิร์ฟเวอร์", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    embed, files = build_panel_embed(interaction.guild_id)
    view = PersistentQuestPanelView(interaction.guild_id)
    sent_msg = await channel.send(embed=embed, files=files, view=view)
    if sent_msg.embeds and sent_msg.embeds[0].image and sent_msg.embeds[0].image.url:
        state.update_panel(interaction.guild_id, banner_url=sent_msg.embeds[0].image.url)
    if sent_msg.embeds and sent_msg.embeds[0].thumbnail and sent_msg.embeds[0].thumbnail.url:
        state.update_panel(interaction.guild_id, logo_url=sent_msg.embeds[0].thumbnail.url)
    await interaction.followup.send(f"✅ ส่งแผงควบคุมทำเควสไปยังห้อง {channel.mention} เรียบร้อยแล้ว", ephemeral=True)

# --- Slash Command: /reset (DevilQuest Compatibility) ---
@bot.tree.command(name="reset", description="รีเซ็ตโควต้าทำเควสฟรีของสมาชิกทุกคนในเซิร์ฟเวอร์")
@app_commands.default_permissions(administrator=True)
async def cmd_reset(interaction: discord.Interaction):
    state.reset_all_quotas()
    await interaction.response.send_message("✅ **รีเซ็ตโควต้าฟรีของสมาชิกทุกคนเรียบร้อยแล้ว!** ทุกคนสามารถทำเควสใหม่ได้ทันที", ephemeral=True)

# --- Slash Command: /setrole-quest (DevilQuest Compatibility) ---
@bot.tree.command(name="setrole-quest", description="กำหนดสิทธิ์ หรือมอบวันใช้งาน Pro Quest ให้กับสมาชิก")
@app_commands.describe(
    user="สมาชิกที่ต้องการจัดการสิทธิ์",
    days="จำนวนวันที่ต้องการมอบ (ใส่ 0 เพื่อยกเลิกสิทธิ์)",
    role="ยศที่ต้องการมอบให้เพิ่มเติม (ไม่จำเป็นต้องระบุ)"
)
@app_commands.default_permissions(administrator=True)
async def cmd_setrole_quest(
    interaction: discord.Interaction,
    user: discord.Member,
    days: int = 30,
    role: Optional[discord.Role] = None
):
    if not interaction.guild:
        return await interaction.response.send_message("ใช้งานได้เฉพาะในเซิร์ฟเวอร์", ephemeral=True)
    
    if days > 0:
        exp = state.set_user_pro(user.id, days)
        exp_str = exp.strftime("%Y-%m-%d %H:%M") if exp else f"{days} วัน"
        msg = f"✅ **มอบสิทธิ์ Pro Quest ให้กับ {user.mention} สำเร็จ!**\n⏱️ ระยะเวลา: **{days} วัน** (หมดอายุ: {exp_str})"
    else:
        state.set_user_pro(user.id, 0)
        msg = f"🚫 **ยกเลิกสิทธิ์ Pro Quest ของ {user.mention} เรียบร้อยแล้ว**"

    if role:
        try:
            if days > 0:
                await user.add_roles(role, reason="PayomboyZ Quest Pro Role")
            else:
                await user.remove_roles(role, reason="PayomboyZ Quest Pro Revoked")
        except Exception as e:
            msg += f"\n*(ไม่สามารถปรับยศ Discord ได้: {e})*"

    await interaction.response.send_message(msg, ephemeral=True)

# --- Slash Command: /keygen, /redeem & /redom-premium ---
@bot.tree.command(name="keygen", description="สร้างคีย์ VIP Pro Quest สำหรับนำไปแจกหรือจำหน่าย")
@app_commands.describe(days="จำนวนวันใช้งาน (ค่าเริ่มต้น: 30 วัน)")
@app_commands.default_permissions(administrator=True)
async def cmd_keygen(interaction: discord.Interaction, days: int = 30):
    new_key = f"PAYOMBOYZ-VIP-{secrets.token_hex(3).upper()}-{secrets.token_hex(3).upper()}"
    state.redeem_keys.add(new_key)
    state.save()
    await interaction.response.send_message(
        f"🔑 **สร้างคีย์ VIP สำเร็จ!**\n`{new_key}`\n⏱️ ระยะเวลา: **{days} วัน**\nผู้ใช้สามารถนำไปใช้ด้วยคำสั่ง `/redeem` หรือกดปุ่ม ⭐ Quest Premium",
        ephemeral=True
    )

@bot.tree.command(name="redeem", description="แลกรับสิทธิ์ Pro Quest ด้วยคีย์ VIP")
@app_commands.describe(key="รหัสคีย์ VIP")
async def cmd_redeem(interaction: discord.Interaction, key: str):
    success = state.redeem_key(interaction.user.id, key)
    if success:
        await interaction.response.send_message("🎉 **แลกรับสิทธิ์ Pro Quest สำเร็จแล้ว!** ใช้งานได้ไม่จำกัดโควตา 30 วัน", ephemeral=True)
    else:
        await interaction.response.send_message("❌ **คีย์ไม่ถูกต้อง หรือถูกใช้งานไปแล้ว!**", ephemeral=True)

@bot.tree.command(name="redom-premium", description="เติมคีย์พรีเมี่ยม (DevilQuest Compatibility Alias)")
@app_commands.describe(key="รหัสคีย์ VIP")
async def cmd_redom_premium(interaction: discord.Interaction, key: str):
    await cmd_redeem.callback(interaction, key)

# --- Prefix Sync Command: !sync ---
@bot.command(name="sync")
@commands.is_owner()
async def prefix_sync(ctx: commands.Context):
    msg = await ctx.send("⏳ กำลังซิงค์คำสั่ง Slash Commands ทั้งหมด...")
    try:
        synced = await bot.tree.sync()
        if ctx.guild:
            bot.tree.copy_global_to(guild=ctx.guild)
            synced_g = await bot.tree.sync(guild=ctx.guild)
            await msg.edit(content=f"✅ ซิงค์คำสั่งสำเร็จ! (Global: {len(synced)} คำสั่ง, Guild: {len(synced_g)} คำสั่ง)")
        else:
            await msg.edit(content=f"✅ ซิงค์คำสั่งสำเร็จ! ({len(synced)} คำสั่ง)")
    except Exception as e:
        await msg.edit(content=f"❌ ซิงค์ล้มเหลว: {e}")

# ==============================================================================
# 7. COMMERCIAL REST API (PORT 5050)
# ==============================================================================
api_app = web.Application()

async def api_health(request: web.Request):
    return web.json_response({
        "status": "online",
        "service": "PayomboyZ Auto Quest Engine",
        "engine_version": "2.0.0-v10",
        "bot_connected": bot.is_ready()
    })

async def api_start_quest(request: web.Request):
    try:
        payload = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON payload"}, status=400)

    token = payload.get("token")
    if not token:
        return web.json_response({"error": "Missing token"}, status=400)

    profile = await DiscordQuestV10Handler.validate_token(token)
    if not profile:
        return web.json_response({"error": "Token is invalid or expired"}, status=401)

    guild_id = payload.get("guild_id")
    user_id = payload.get("user_id")
    status_ch_id = payload.get("status_channel_id")
    result_ch_id = payload.get("result_channel_id")

    guild = None
    if guild_id and hasattr(bot, "get_guild"):
        try:
            guild = bot.get_guild(int(guild_id))
        except Exception:
            pass

    user = None
    if guild and user_id:
        try:
            user = guild.get_member(int(user_id))
        except Exception:
            pass
    if not user and user_id and hasattr(bot, "fetch_user"):
        try:
            user = await bot.fetch_user(int(user_id))
        except Exception:
            pass

    status_ch = None
    result_ch = None
    if guild:
        cfg = state.get_guild(guild.id)
        s_id = status_ch_id or cfg.get("status_channel_id")
        r_id = result_ch_id or cfg.get("result_channel_id")
        if s_id:
            try:
                status_ch = guild.get_channel(int(s_id))
            except Exception:
                pass
        if r_id:
            try:
                result_ch = guild.get_channel(int(r_id))
            except Exception:
                pass
        if not status_ch and guild.text_channels:
            status_ch = guild.text_channels[0]
        if not result_ch:
            result_ch = status_ch

    if not status_ch and hasattr(bot, "guilds"):
        for g in bot.guilds:
            if g.text_channels:
                status_ch = g.text_channels[0]
                result_ch = status_ch
                guild = g
                break

    target_quest_ids = payload.get("target_quest_ids")
    job = UserQuestJob(
        guild=guild,
        user=user,
        profile=profile,
        tokens=[token],
        status_channel=status_ch,
        result_channel=result_ch,
        target_quest_ids=target_quest_ids
    )
    await worker_pool.enqueue(job)

    status_url = f"https://discord.com/channels/{guild.id}/{status_ch.id}" if (guild and status_ch) else ""
    return web.json_response({
        "success": True,
        "username": profile.get("username", "User"),
        "status_url": status_url,
        "status_channel_name": getattr(status_ch, "name", "general"),
        "result_channel_name": getattr(result_ch, "name", "general")
    })

async def api_generate_keys(request: web.Request):
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON payload"}, status=400)
    
    secret = body.get("secret", "")
    if secret != MASTER_API_SECRET:
        return web.json_response({"error": "Unauthorized: Invalid API secret"}, status=403)
    
    days = int(body.get("days", 30))
    count = min(100, max(1, int(body.get("count", 1))))
    generated = []
    for _ in range(count):
        new_key = f"PAYOMBOYZ-VIP-{secrets.token_hex(3).upper()}-{secrets.token_hex(3).upper()}"
        state.redeem_keys.add(new_key)
        generated.append(new_key)
    state.save()
    return web.json_response({
        "success": True,
        "count": len(generated),
        "days": days,
        "keys": generated
    })

async def api_user_quota(request: web.Request):
    user_id = request.match_info.get("user_id")
    if not user_id:
        return web.json_response({"error": "Missing user_id"}, status=400)
    try:
        uid_int = int(user_id)
    except ValueError:
        return web.json_response({"error": "Invalid user_id"}, status=400)
    status_data = state.get_user_status(uid_int)
    return web.json_response(status_data)

async def api_active_quests(request: web.Request):
    return web.json_response({
        "success": True,
        "engine": "PayomboyZ Discord Quests v10",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active": True
    })

api_app.router.add_get("/api/health", api_health)
api_app.router.add_post("/api/v1/quest/start", api_start_quest)
api_app.router.add_post("/api/start_quest", api_start_quest)
api_app.router.add_post("/api/v1/keys/generate", api_generate_keys)
api_app.router.add_get("/api/v1/quota/{user_id}", api_user_quota)
api_app.router.add_get("/api/v1/quests/active", api_active_quests)
if os.path.exists(ASSETS_DIR):
    api_app.router.add_static("/assets/", path=str(ASSETS_DIR), name="assets")

async def start_api_server():
    runner = web.AppRunner(api_app)
    await runner.setup()
    site = web.TCPSite(runner, API_HOST, API_PORT)
    try:
        await site.start()
        print(f"[REST-API] PayomboyZ Commercial API running at http://{API_HOST}:{API_PORT}")
    except Exception as e:
        print(f"[REST-API] Server start error: {e}")

# ==============================================================================
# 8. BOT EVENT LIFECYCLE
# ==============================================================================
@bot.event
async def on_ready():
    print(f"\n{'='*60}")
    print(f"  💎 PAYOMBOYZ AUTO QUEST ENGINE (VERIFIED)")
    print(f"  Logged in as: {bot.user} (ID: {bot.user.id})")
    print(f"  Guilds: {len(bot.guilds)} | Latency: {round(bot.latency * 1000, 2)}ms")
    print(f"{'='*60}\n")

    # Start Worker Pool
    worker_pool.start()

    # Register persistent views for active guilds
    for g in bot.guilds:
        bot.add_view(PersistentQuestPanelView(g.id))

    # Auto sync commands to all connected guilds
    for g in bot.guilds:
        try:
            bot.tree.copy_global_to(guild=g)
            await bot.tree.sync(guild=g)
            print(f"[Sync] Commands synced for guild: {g.name} ({g.id})")
        except Exception as e:
            print(f"[Sync] Guild sync error for {g.id}: {e}")

    # Start Dynamic Presence Rotator Task (GHOST X parity: updates every 30s)
    if not presence_rotator.is_running():
        presence_rotator.start()

@tasks.loop(seconds=30)
async def presence_rotator():
    if not bot.is_ready():
        return
    try:
        server_count = len(bot.guilds)
        user_count = sum(g.member_count or 0 for g in bot.guilds)
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{server_count} servers | {user_count:,} users"
            ),
            status=discord.Status.online
        )
    except Exception:
        pass

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.component:
        return
    cid = interaction.data.get("custom_id", "")
    if cid in ("full_auto_quest", "payomboyz_start_btn") or cid.startswith("payomboyz_start_btn_"):
        cfg = state.get_panel(interaction.guild_id)
        if not cfg.get("is_open", True):
            reason = cfg.get("closed_reason", "ระบบปิดปรับปรุงชั่วคราว")
            return await interaction.response.send_message(f"🔒 **{reason}**", ephemeral=True)
        modal = AutoQuestSubmissionModal()
        await interaction.response.send_modal(modal)
    elif cid in ("show_ended_page", "payomboyz_status_btn") or cid.startswith("payomboyz_status_btn_"):
        view = PersistentQuestPanelView(interaction.guild_id)
        await view.on_status_clicked(interaction)
    elif cid in ("payomboyz_premium_btn", "quest_premium_btn") or cid.startswith("payomboyz_premium_btn_"):
        modal = QuestPremiumModal()
        await interaction.response.send_modal(modal)
    elif cid in ("payomboyz_info_btn", "quest_info_btn") or cid.startswith("payomboyz_info_btn_"):
        view = PersistentQuestPanelView(interaction.guild_id)
        await view.on_info_clicked(interaction)
    elif cid in ("btn_open_token_finder", "payomboyz_token_btn") or cid.startswith("payomboyz_token_btn_"):
        view = PersistentQuestPanelView(interaction.guild_id)
        await view.on_token_clicked(interaction)


# ==============================================================================
# 9. MAIN RUNNER
# ==============================================================================
async def main():
    if not BOT_TOKEN:
        print("❌ ERROR: No Discord Bot Token configured! Pass --token <TOKEN> or set DISCORD_BOT_TOKEN.")
        sys.exit(1)

    # Launch REST API Server concurrently
    asyncio.create_task(start_api_server())

    # Launch Discord Bot
    try:
        await bot.start(BOT_TOKEN)
    except Exception as e:
        print(f"❌ Bot failed to start: {e}")

if __name__ == "__main__":
    asyncio.run(main())
