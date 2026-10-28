import asyncio
import os
import sys
import glob
import threading
import subprocess
import time

# Auto-detect and prepend .local site-packages for Bot-Hosting.net Linux containers
for _lp in [
    "/home/container/.local/lib/python3.11/site-packages",
    "/home/container/.local/lib/python3.10/site-packages",
    os.path.expanduser("~/.local/lib/python3.11/site-packages"),
    os.path.expanduser("~/.local/lib/python3.10/site-packages")
] + glob.glob("/home/container/.local/lib/python*/site-packages"):
    if os.path.isdir(_lp) and _lp not in sys.path:
        sys.path.insert(0, _lp)

# Fix Windows terminal encoding for UTF-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure base directory and DiscordAutoquest2 are in search path
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)
os.chdir(_BASE_DIR)
_AUTOQUEST2_DIR = os.path.join(_BASE_DIR, "DiscordAutoquest2")
if os.path.exists(_AUTOQUEST2_DIR) and _AUTOQUEST2_DIR not in sys.path:
    sys.path.insert(0, _AUTOQUEST2_DIR)

import discord
from discord.ext import commands
from config import TOKEN, BOT_PREFIX, API_PORT

# Ensure Python 3.8+
if sys.version_info < (3, 8):
    sys.exit("Python 3.8 or higher is required.")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


def clean_port_conflict(port: int = API_PORT):
    """Automatically kill any existing process holding the server port."""
    if sys.platform != "win32":
        return
    try:
        cmd = f'powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess"'
        out = subprocess.check_output(cmd, shell=True, text=True).strip()
        current_pid = os.getpid()
        for line in out.splitlines():
            line = line.strip()
            if line.isdigit():
                pid = int(line)
                if pid != current_pid and pid > 0:
                    subprocess.run(f"taskkill /f /pid {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print(f"[*] Auto-cleaned previous process on port {port} (PID: {pid})")
    except Exception:
        pass


def kill_duplicate_instances():
    """Kill any other running instances of main.py to prevent dual Gateway collisions."""
    if sys.platform != "win32":
        return
    try:
        current_pid = os.getpid()
        cmd = f'powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \\"Name = \'python.exe\'\\" | Where-Object {{ ($_.CommandLine -like \'*BotBypass*\' -or $_.CommandLine -like \'*discord_bot*main.py*\') -and $_.ProcessId -ne {current_pid} }} | Select-Object -ExpandProperty ProcessId"'
        out = subprocess.check_output(cmd, shell=True, text=True).strip()
        for line in out.splitlines():
            line = line.strip()
            if line.isdigit():
                pid = int(line)
                subprocess.run(f"taskkill /f /pid {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"[*] Terminated conflicting bot instance (PID: {pid})")
    except Exception:
        pass


def run_api_background():
    """Run Flask API Server and Web UI in a daemon thread."""
    try:
        from api_server import app, API_PORT
        import logging
        log = logging.getLogger("werkzeug")
        log.setLevel(logging.ERROR)
        app.run(host="0.0.0.0", port=API_PORT, debug=False, use_reloader=False, threaded=True)
    except Exception as e:
        print(f"[API ERR] Server error: {e}")


class KeyBypassBot(commands.Bot):
    """Self-hosted Bypass Discord Bot with unified console."""

    def __init__(self):
        super().__init__(
            command_prefix=BOT_PREFIX,
            intents=intents,
            help_command=None
        )
        self.synced_count = 0

    async def setup_hook(self):
        """Load all cogs and sync slash commands."""
        # Global slash command error handler
        async def on_tree_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
            import traceback
            traceback.print_exc()
            err_text = str(error)
            if hasattr(error, "original"):
                err_text = str(error.original)
            
            if "50001" in err_text or "Missing Access" in err_text:
                user_msg = (
                    "❌ **บอทขาดสิทธิ์การใช้งาน (403 Missing Access)**\n"
                    "• ตรวจสอบว่า ยศของบอท หรือช่องนี้อนุญาตให้บอท **ดูช่อง (View Channel)** และ **ส่งข้อความ/แทรกลิงก์ (Send Messages / Embed Links)** หรือไม่\n"
                    "• หรือให้ยศ **Administrator** แก่บอทในเซิร์ฟเวอร์"
                )
            elif "Failed to convert" in err_text and "TextChannel" in err_text:
                user_msg = (
                    "❌ **การระบุช่องไม่ถูกต้อง**\n"
                    "• ตอนเลือกช่อง `result_channel` กรุณากดเลือกช่องจากเมนูแท็ก `#ช่อง` ของ Discord (ห้ามพิมพ์ชื่อช่องลอยๆ)\n"
                    "• หรือบอทไม่มีสิทธิ์มองเห็นช่องดังกล่าว"
                )
            else:
                user_msg = f"❌ **เกิดข้อผิดพลาดในการประมวลผลคำสั่ง:** `{err_text}`"

            try:
                if interaction.response.is_done():
                    await interaction.followup.send(user_msg, ephemeral=True)
                else:
                    await interaction.response.send_message(user_msg, ephemeral=True)
            except Exception:
                pass

        self.tree.on_error = on_tree_error

        print("[*] Loading Cogs...")
        cogs_dir = os.path.join(os.path.dirname(__file__), "cogs")
        for filename in os.listdir(cogs_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                cog_name = f"cogs.{filename[:-3]}"
                try:
                    await self.load_extension(cog_name)
                    print(f"  [OK] Loaded: {cog_name}")
                except Exception as e:
                    print(f"  [ERR] Failed to load {cog_name}: {e}")

        # Register persistent views
        try:
            from cogs.panel import PanelView
            self.add_view(PanelView())
            print("  [OK] Registered persistent PanelView")
        except Exception as e:
            print(f"  [WARN] PanelView register error: {e}")
        try:
            from cogs.verification import VerifyPanelView
            self.add_view(VerifyPanelView())
            print("  [OK] Registered persistent VerifyPanelView")
        except Exception as e:
            print(f"  [WARN] VerifyPanelView register error: {e}")
        try:
            from cloner_engine import MainClonerPersistentView, InteractivePanelControlView
            self.add_view(MainClonerPersistentView())
            self.add_view(InteractivePanelControlView())
            print("  [OK] Registered persistent Cloner Views (MainClonerPersistentView, InteractivePanelControlView)")
        except Exception as e:
            print(f"  [WARN] Cloner views register error: {e}")
        try:
            from payomboyz_autoquest import PersistentQuestPanelView
            self.add_view(PersistentQuestPanelView(None))
            for gid in [1549398019970179152, 1553087781595775007]:
                self.add_view(PersistentQuestPanelView(gid))
            print("  [OK] Registered persistent Quest Panel Views")
        except Exception as e:
            print(f"  [WARN] Quest panel view register error: {e}")
        try:
            from cogs.status_map_sync import StatusMapPersistentView
            self.add_view(StatusMapPersistentView())
            print("  [OK] Registered persistent StatusMapPersistentView")
        except Exception as e:
            print(f"  [WARN] StatusMapPersistentView register error: {e}")

        print("[*] Syncing Slash Commands...")
        try:
            synced = await self.tree.sync()
            self.synced_count = len(synced)
            print(f"[OK] Synced {self.synced_count} command(s) globally!")
        except Exception as e:
            print(f"[ERR] Sync failed: {e}")

    async def on_ready(self):
        invite_url = (
            f"https://discord.com/oauth2/authorize?client_id={self.user.id}"
            f"&permissions=8&scope=bot%20applications.commands"
        )
        print("=" * 60)
        print("[+] Registered persistent PanelView into Bot.")
        print(f"[+] Logged in as: {self.user.name}#{self.user.discriminator} (ID: {self.user.id})")
        print(f"[+] Engine: Self-hosted Multi-Endpoint Bypass (Delta, Luarmor, 100+ Domains)")
        from utils.rtao_client import rtao_client
        quota = rtao_client.get_status()
        try:
            supported_list = await rtao_client.sync_supported_domains()
            supported_count = len(supported_list)
        except Exception:
            supported_count = len(rtao_client.supported_domains)
        print(f"[+] Primary Engine: RTaO API Active (Priority #1 - {supported_count} Supported Domains)")
        print(f"[+] RTaO Quota: {quota['remaining']}/3000 Requests Remaining")
        if quota['remaining'] < 100:
            rtao_client._check_and_warn_quota(quota['remaining'])
        print(f"[+] Prefix: {BOT_PREFIX}")
        print("[+] ลิ้งก์เชิญบอทเข้า Discord:")
        print(f"    {invite_url}")
        print("=" * 60)
        print(f"[+] Synced {self.synced_count} global slash commands for KeyBypass Bot.")
        # Prune redundant guild-level command copies so Discord only renders clean global commands
        for gid in [1549398019970179152, 1553087781595775007]:
            try:
                target_guild = self.get_guild(gid) or discord.Object(id=gid)
                self.tree.clear_commands(guild=target_guild)
                await self.tree.sync(guild=target_guild)
                print(f"[+] Pruned guild command duplicates for guild ({gid}) -> Clean single global command tree")
            except Exception as e:
                print(f"[!] Guild command prune note ({gid}): {e}")
        print(f"[RUNTIME CHECK] Python={sys.version.split()[0]} | Status=ONLINE | Web=http://localhost:{API_PORT}")
        print("=" * 60)

        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="🔓 /bypass • /setup"
        )
        await self.change_presence(status=discord.Status.online, activity=activity)

        if not getattr(self, "_heartbeat_started", False):
            self._heartbeat_started = True
            async def heartbeat_loop():
                import datetime
                while True:
                    await asyncio.sleep(60)
                    now_str = datetime.datetime.now().strftime("%H:%M:%S")
                    print(f"[*] [HEARTBEAT {now_str}] Bot active | Latency: {self.latency*1000:.1f}ms", flush=True)
            asyncio.create_task(heartbeat_loop())


async def main():
    if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("\n[ERR] DISCORD_BOT_TOKEN missing in .env!\n")
        return

    # Kill any duplicate bot processes running on this machine
    kill_duplicate_instances()

    # Clean port conflicts
    clean_port_conflict(API_PORT)
    clean_port_conflict(5050)

    # Start Flask Web/API Server in thread
    api_thread = threading.Thread(target=run_api_background, daemon=True)
    api_thread.start()

    # Terminal Banner matching reference
    print("=" * 60)
    print(f"[*] Listening on http://0.0.0.0:{API_PORT}")
    print("[*] Endpoints:")
    print("    - GET  /                  - Web UI")
    print("    - GET  /api/health        - Bridge status & uptime")
    print("    - GET  /api/stats         - Bypass statistics")
    print("    - GET  /api/supported     - Supported 100+ services catalog")
    print("    - POST /api/bypass        - Single bypass endpoint")
    print("    - POST /api/bypass/bulk   - Bulk bypass (API key)")
    print("    - GET  /api/docs          - HTML documentation")
    print("=" * 60)
    print("[*] Starting KeyBypass Discord Bot...")

    while True:
        bot = KeyBypassBot()
        try:
            async with bot:
                await bot.start(TOKEN)
        except discord.errors.PrivilegedIntentsRequired:
            print("\n[ERR] Privileged Intents Required!")
            print("-> Discord Developer Portal > Bot > Enable MESSAGE CONTENT + SERVER MEMBERS\n")
            break
        except discord.errors.LoginFailure:
            print("\n[ERR] Invalid Bot Token! Check DISCORD_BOT_TOKEN in .env\n")
            break
        except Exception as e:
            print(f"\n[WARN] Bot connection dropped: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot shutting down...")
