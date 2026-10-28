"""
Admin / Utility Cog — /ping, /about
"""
import os
import time
import discord
from discord import app_commands
from discord.ext import commands
from config import COLOR_PRIMARY, COLOR_INFO, COLOR_SUCCESS
from utils.embeds import EmbedFactory


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._start_time = time.time()

    @app_commands.command(name="ping", description="ตรวจสอบสถานะและ Latency ของบอท")
    async def ping_cmd(self, interaction: discord.Interaction):
        latency_ms = round(self.bot.latency * 1000)
        color = COLOR_SUCCESS if latency_ms < 150 else (0xFFDD57 if latency_ms < 300 else 0xFF3860)
        embed = discord.Embed(
            title="🏓 Pong!",
            color=color
        )
        embed.add_field(name="📡 WebSocket Latency", value=f"`{latency_ms}ms`", inline=True)
        embed.add_field(name="⚙️ Status", value="`Online`", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="about", description="ข้อมูลเกี่ยวกับบอทนี้")
    async def about_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🤖 KeyBypass Bot",
            description=(
                "ระบบ Bypass ลิงค์โฆษณา **Self-hosted** ไม่พึ่ง API ภายนอก\n"
                "ใช้ multi-endpoint cascade engine ที่พัฒนาเอง\n\n"
                "**Commands:**\n"
                "`/setup` — ติดตั้ง Panel ในช่อง\n"
                "`/config` — เปลี่ยน Log Channel\n"
                "`/stats` — สถิติการใช้งาน\n"
                "`/ping` — เช็ค Latency\n"
                "`/bypass` — Bypass ตรงๆ ไม่ผ่าน Panel"
            ),
            color=COLOR_PRIMARY
        )
        embed.add_field(name="🔌 Engine", value="`Self-hosted Multi-Endpoint`", inline=True)
        embed.add_field(name="📦 Version", value="`2.0.0`", inline=True)
        embed.set_footer(text="Self-hosted • No external API dependency")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="embid", description="Embed Info แบบละเอียด (Bot + Server + Pattern + Stats)")
    async def embid_cmd(self, interaction: discord.Interaction):
        """Embed info แบบละเอียด — ดูสถานะทั้งระบบ"""
        from config import TOKEN, API_PORT, PLATOBOOST_TOKEN, COLOR_PRIMARY, BYPASS_ENDPOINTS, PROVIDERS
        import time, os, socket
        try:
            provider_text = "\n".join([
                f"• `{k}`: {v.get('emoji','')} {v.get('name','')} — {len(v.get('patterns',[]))} patterns"
                for k, v in list(PROVIDERS.items())[:6]
            ])
        except Exception:
            provider_text = "`Self-hosted patterns`"

        latency_ms = round(self.bot.latency * 1000)
        server_ok = False; server_port = API_PORT
        try:
            s = socket.create_connection(("127.0.0.1", server_port), timeout=2)
            s.close(); server_ok = True
        except: pass
        stats_ok = False; total = 0
        try:
            from utils.stats_manager import stats_manager
            total = getattr(stats_manager, 'total_bypasses', 0)
            stats_ok = True
        except: pass
        db_path = os.path.join(os.path.dirname(__file__), "..", "data", "stats.json")
        db_ok = os.path.isfile(os.path.abspath(db_path))
        embed = discord.Embed(
            title="🤖 BotBypass — Full System Info",
            description="Self-hosted multi-endpoint engine • Zero external API dependency",
            color=COLOR_PRIMARY,
        )
        embed.add_field(name="📡 Discord Bot", value=f"`{self.bot.user.name}`\nLatency: `{latency_ms}ms`", inline=True)
        embed.add_field(name="🖥 Server (Port)", value=f"`:{API_PORT}` (aiohttp)\nStatus: `{'✅' if server_ok else '❌'}`", inline=True)
        embed.add_field(name="🔑 Auth / Token", value=f"TOKEN: `***` + `{TOKEN[-4:] if TOKEN else 'NONE'}`\nPLATO: `{PLATOBOOST_TOKEN[:3]}...`", inline=True)
        embed.add_field(name="📦 Supported Services", value=provider_text, inline=False)
        embed.add_field(name="🔧 Commands", value="`/setup` • `/ping` • `/about` • `/stats` • `/bypass` • `/script-search` • `/embid` • `/health_check`", inline=False)
        embed.add_field(name="📊 Stats", value=f"Total: `{total}` | DB: `{'✅' if stats_ok else '❌'}` | Config: `{'✅' if db_ok else '❌'}`", inline=True)
        embed.set_footer(text=f"BotBypass Phase 2 • Port 49288 • Zero external dependency • {time.strftime('%Y-%m-%d %H:%M')}")
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="health_check", description="ตรวจสอบสถานะครบถ้วน (Bot + Server + Engine + DB)")
    async def health_check_cmd(self, interaction: discord.Interaction):
        import time, socket, os
        from config import API_PORT, PLATOBOOST_TOKEN
        latency_ms = round(self.bot.latency * 1000)
        server_ok = False; server_port = API_PORT
        try:
            s = socket.create_connection(("127.0.0.1", server_port), timeout=2); s.close(); server_ok = True
        except: pass
        stats_ok = False; total = 0
        try:
            from utils.stats_manager import stats_manager
            total = getattr(stats_manager, 'total_bypasses', 0)
            stats_ok = True
        except: pass
        engine_ok = False
        try:
            from utils.bypasser import DomainDetector; engine_ok = True
        except: pass
        status_color = 0x00FF7F if (latency_ms < 200 and server_ok) else (0xFFDD57 if latency_ms < 500 else 0xFF3860)
        embed = discord.Embed(title="⚡ Health Check — Full System Status", description="BotBypass Self-Hosted System", color=status_color)
        embed.add_field(name="📡 WebSocket", value=f"`{latency_ms}ms` {'✅' if latency_ms < 300 else '⚠️' if latency_ms < 600 else '❌'}", inline=True)
        embed.add_field(name="🖥 Server Port", value=f"`:{server_port}` {'✅ On' if server_ok else '❌ Off'}", inline=True)
        embed.add_field(name="📊 Stats DB", value=f"`{total}` bypasses {'✅' if stats_ok else '❌'}", inline=True)
        embed.add_field(name="🔧 Bypass Engine", value=f"`DomainDetector` {'✅ Loaded' if engine_ok else '❌'}", inline=True)
        embed.add_field(name="💾 Config / .env", value=f"`TOKEN` / `API_PORT={API_PORT}` / `PLATOBOOST`", inline=True)
        embed.add_field(name="📦 Cogs", value="`bypass` • `panel` • `admin` • `setup` ✅", inline=True)
        embed.set_footer(text=f"BotBypass • {self.bot.user.name if self.bot.user else 'Unknown'} • {time.strftime('%Y-%m-%d %H:%M:%S')}")
        await interaction.response.send_message(embed=embed, ephemeral=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
