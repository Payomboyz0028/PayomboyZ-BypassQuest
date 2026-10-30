"""
/setup — ติดตั้งบอทแบบ "Hour" สไตล์
มี Script Search Panel + Bypass Panel + Welcome Message
"""
import discord
from discord.ext import commands
from discord import app_commands
import os, sys, time, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import TOKEN, API_PORT, COLOR_PRIMARY, COLOR_SUCCESS, COLOR_INFO


# ─────────────────────────────────────────
# Persistent View — Script Panel Buttons
# ─────────────────────────────────────────
class ScriptPanelView(discord.ui.View):
    """ปุ่มสำหรับค้นหาสคริปต์ — อยู่ถาวร"""

    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="🔍  ค้นหาสคริปต์",
        style=discord.ButtonStyle.primary,
        custom_id="panel:search_btn",
        row=0,
        emoji="🎮"
    )
    async def search_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """เปิด Modal ให้พิมพ์ชื่อเกม/แมพที่ต้องการค้นหา"""
        await interaction.response.send_modal(SearchModal(self.bot))

    @discord.ui.button(
        label="📋  รายชื่อเกมทั้งหมด",
        style=discord.ButtonStyle.secondary,
        custom_id="panel:games_btn",
        row=0,
        emoji="📚"
    )
    async def games_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """แสดงรายชื่อเกมทั้งหมดที่มีสคริปต์"""
        await interaction.response.defer(ephemeral=True)

        scripts_db = load_scripts_db()
        games = set()
        for cat, scripts in scripts_db.items():
            for s in scripts:
                if s.get("game"):
                    games.add(s["game"])

        games_sorted = sorted(games)
        lines = []
        emoji_list = [
            "🎮", "⚔️", "🌊", "🏴‍☠️", "👾", "🔫", "🗡️", "🛡️", "🐉", "🌟",
            "🎯", "💎", "🚀", "🔥", "⚡", "🍀", "🎲", "🎪", "🏰", "🌋"
        ]
        for i, game in enumerate(games_sorted[:25]):
            e = emoji_list[i % len(emoji_list)]
            count = sum(1 for cat in scripts_db.values() for s in cat if s.get("game") == game)
            lines.append(f"{e} **{game}** — `{count} สคริปต์`")

        embed = discord.Embed(
            title="📚 รายชื่อเกมทั้งหมด",
            description="\n".join(lines) if lines else "ยังไม่มีเกมในฐานข้อมูล",
            color=COLOR_INFO
        )
        embed.set_footer(text=f"ทั้งหมด {len(games_sorted)} เกม • พิมพ์ชื่อเกมเพื่อดูสคริปต์")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="🔓  Bypass Link",
        style=discord.ButtonStyle.success,
        custom_id="panel:bypass_panel_btn",
        row=1,
        emoji="🔗"
    )
    async def bypass_panel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Bypass ลิงค์โฆษณา"""
        from cogs.panel import BypassModal
        from utils.config_manager import guild_config
        res_ch = guild_config.get_result_channel(interaction.guild.id) if interaction.guild else None
        modal = BypassModal(result_channel_id=res_ch)
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="📊  สถิติ",
        style=discord.ButtonStyle.secondary,
        custom_id="panel:stats_panel_btn",
        row=1,
        emoji="📈"
    )
    async def stats_panel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """ดูสถิติการใช้งาน"""
        await interaction.response.defer(ephemeral=True)
        try:
            from utils.stats_manager import stats_manager
            stats = stats_manager.get_summary()
        except Exception:
            stats = {"total_bypassed": 0, "today_count": 0, "unique_users": 0}

        embed = discord.Embed(
            title="📊 สถิติ KeyBypass",
            color=COLOR_PRIMARY,
            description=f"**🚀 Bypass ทั้งหมด:** `{stats.get('total_bypassed', 0):,}`\n"
                        f"**📅 วันนี้:** `{stats.get('today_count', 0):,}`\n"
                        f"**👥 ผู้ใช้:** `{stats.get('unique_users', 0):,}`\n"
                        f"**🎮 สคริปต์ทั้งหมด:** `{count_total_scripts()}` รายการ"
        )
        embed.set_footer(text="KeyBypass • Self-hosted Engine")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="❓  วิธีใช้",
        style=discord.ButtonStyle.grey,
        custom_id="panel:help_btn",
        row=1,
        emoji="💡"
    )
    async def help_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """แสดงวิธีใช้บอท"""
        embed = discord.Embed(
            title="💡 วิธีใช้ KeyBypass Bot",
            description=(
                "**🎮 ค้นหาสคริปต์**\n"
                "กดปุ่ม `🔍 ค้นหาสคริปต์` แล้วพิมพ์ชื่อเกมหรือแมพที่ต้องการ\n"
                "เช่น: `Blox Fruits`, `Jailbreak`, `Arsenal`, `Fisch`\n\n"
                "**🔓 Bypass ลิงค์**\n"
                "กดปุ่ม `🔓 Bypass Link` วางลิงค์โฆษณาที่ต้องการ bypass\n"
                "รองรับ: Linkvertise, LootLabs, Platoboost, Work.ink ฯลฯ\n\n"
                "**📋 คำสั่ง Slash**\n"
                "`/rscript` — ค้นหาสคริปต์ RScript\n"
                "`/bloxscript` — ค้นหาสคริปต์ Blox\n"
                "`/script-search` — ค้นหาสคริปต์จากทุกแหล่ง\n"
                "`/bypass` — Bypass ลิงค์โดยตรง\n"
                "`/ping` — เช็คสถานะบอท"
            ),
            color=COLOR_INFO
        )
        embed.set_footer(text="พิมพ์ชื่อเกมเพื่อค้นหาสคริปต์ได้ทันที!")
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ─────────────────────────────────────────
# Search Modal — พิมพ์ชื่อเกม/แมพ
# ─────────────────────────────────────────
class SearchModal(discord.ui.Modal, title="🎮 ค้นหาสคริปต์"):
    search_input = discord.ui.TextInput(
        label="พิมพ์ชื่อเกม หรือ แมพ ที่ต้องการ",
        placeholder="เช่น: Blox Fruits, Jailbreak, Arsenal, Fisch, BedWars...",
        style=discord.TextStyle.short,
        required=True,
        max_length=100
    )

    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=120)
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        query = self.search_input.value.strip()
        if not query:
            await interaction.response.send_message("❌ กรุณาพิมพ์ชื่อเกม", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=False)

        # ค้นหาสคริปต์
        scripts_db = load_scripts_db()
        results = []
        for cat, scripts in scripts_db.items():
            for s in scripts:
                name = s.get("name", "").lower()
                game = s.get("game", "").lower()
                desc = s.get("description", "").lower()
                q = query.lower()
                if q in name or q in game or q in desc:
                    results.append({**s, "source": cat})

        if not results:
            embed = discord.Embed(
                title=f"❌ ไม่พบสคริปต์สำหรับ \"{query}\"",
                description=(
                    f"ลองค้นหาด้วยชื่ออื่น หรือดูรายชื่อเกมทั้งหมด\n\n"
                    f"**คำแนะนำ:**\n"
                    f"• ลองพิมพ์แค่ชื่อเกมสั้น ๆ เช่น `blox` แทน `blox fruits`\n"
                    f"• กด `📚 รายชื่อเกมทั้งหมด` เพื่อดูเกมที่มี\n"
                    f"• ใช้ `/script-search` ค้นหาแบบละเอียด"
                ),
                color=0xFF3860
            )
            embed.set_footer(text="พิมพ์ชื่อเกมเพื่อค้นหาสคริปต์ได้ทันที!")
            await interaction.followup.send(embed=embed)
            return

        # แสดงผลพร้อม Pagination
        view = ScriptResultsView(results, query, 0, interaction.user.id)
        await view.send_first_page(interaction)


# ─────────────────────────────────────────
# Bypass Link Modal
# ─────────────────────────────────────────
class BypassLinkModal(discord.ui.Modal, title="🔓 Bypass Ad-Link"):
    link_input = discord.ui.TextInput(
        label="วางลิงค์โฆษณาที่ต้องการ Bypass",
        placeholder="https://linkvertise.com/... หรือ gateway.platoboost.com/...",
        style=discord.TextStyle.short,
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        url = self.link_input.value.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            await interaction.response.send_message("❌ URL ต้องขึ้นต้นด้วย http:// หรือ https://", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            from utils.bypasser import bypass_engine, DomainDetector
            import time
            provider = DomainDetector.detect(url)
            start = time.time()
            result = await bypass_engine.bypass_url(url)
            elapsed = time.time() - start

            if result.get("success"):
                dest = result["direct_url"]
                embed = discord.Embed(
                    title="✅ Bypass สำเร็จ!" if not result.get("is_key") else "🔑 ได้ Key สำเร็จ!",
                    description=f"```\n{dest}\n```",
                    color=COLOR_SUCCESS
                )
                embed.add_field(name="ค่าย", value=f"{provider['emoji']} {provider['name']}", inline=True)
                embed.add_field(name="เวลา", value=f"`{elapsed:.2f}s`", inline=True)
                embed.add_field(name="Engine", value=f"`{result.get('endpoint_used', 'unknown')}`", inline=True)
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(
                    title="❌ Bypass ไม่สำเร็จ",
                    description=f"```{result.get('error', 'ไม่ทราบสาเหตุ')}```",
                    color=0xFF3860
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ เกิดข้อผิดพลาด: `{e}`", ephemeral=True)


# ─────────────────────────────────────────
# Results View with Pagination
# ─────────────────────────────────────────
class ScriptResultsView(discord.ui.View):
    """แสดงผลการค้นหาแบบมีปุ่มต่อไป/กลับ"""

    def __init__(self, results: list, query: str, page: int, user_id: int):
        super().__init__(timeout=180)
        self.results = results
        self.query = query
        self.page = page
        self.user_id = user_id
        self.per_page = 5

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    def _build_embed(self) -> discord.Embed:
        total = len(self.results)
        start = self.page * self.per_page
        end = min(start + self.per_page, total)
        page_items = self.results[start:end]

        embed = discord.Embed(
            title=f"🎮 ผลค้นหา \"{self.query}\"",
            description=f"พบ `{total}` รายการ (หน้า {self.page + 1}/{(total - 1) // self.per_page + 1})",
            color=COLOR_PRIMARY
        )

        emoji_map = {
            "farm": "🌾", "admin": "👑", "aimbot": "🎯", "mod": "🔧",
            "esp": "👁️", "tool": "🛠️", "raid": "⚔️", "hunt": "🏹",
            "stat": "📊", "shop": "🛒", "quest": "📜", "dungeon": "🏚️",
            "script": "📜", "universal": "🌐"
        }

        for s in page_items:
            type_emoji = emoji_map.get(s.get("type", ""), "📦")
            source_badge = "🔴 R" if s.get("source") == "rscript" else "🟦 B"
            game = s.get("game", "Unknown")
            executor = s.get("executor", s.get("source", "krnl"))
            desc = s.get("description", "")[:100]
            url = s.get("url", "")

            value = f"{source_badge} | 🎮 **{game}** | ⚙️ `{executor}`\n{desc}"
            if url:
                value += f"\n🔗 `{url[:80]}{'...' if len(url)>80 else ''}`"

            embed.add_field(
                name=f"{type_emoji} {s['name']}",
                value=value,
                inline=False
            )

        embed.set_footer(text=f"กดปุ่มด้านล่างเพื่อดูหน้าถัดไป • ใช้ /rscript หรือ /bloxscript เพื่อดูรายละเอียด")
        return embed

    async def send_first_page(self, interaction: discord.Interaction):
        """ส่งหน้าแรก"""
        self.clear_items()
        self._add_nav_buttons()
        embed = self._build_embed()
        await interaction.followup.send(embed=embed, view=self)

    @discord.ui.button(label="◀", style=discord.ButtonStyle.grey, custom_id="prev_page")
    async def prev_page_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = max(0, self.page - 1)
        await self._update(interaction)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.grey, custom_id="next_page")
    async def next_page_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        max_page = (len(self.results) - 1) // self.per_page
        self.page = min(max_page, self.page + 1)
        await self._update(interaction)

    def _add_nav_buttons(self):
        """เพิ่มปุ่ม navigation ให้เหมาะสม"""
        self.clear_items()
        max_page = (len(self.results) - 1) // self.per_page

        if self.page > 0:
            self.add_item(discord.ui.Button(label="◀ หน้าที่แล้ว", style=discord.ButtonStyle.grey, custom_id="prev_page_custom"))
        if self.page < max_page:
            self.add_item(discord.ui.Button(label="หน้าที่ต่อไป ▶", style=discord.ButtonStyle.grey, custom_id="next_page_custom"))

        self.add_item(discord.ui.Button(
            label=f"หน้า {self.page + 1}/{max_page + 1}",
            style=discord.ButtonStyle.grey,
            disabled=True,
            custom_id="page_indicator"
        ))

    async def _update(self, interaction: discord.Interaction):
        """อัปเดต embed และปุ่ม"""
        self._add_nav_buttons()
        embed = self._build_embed()
        await interaction.response.edit_message(embed=embed, view=self)


# ─────────────────────────────────────────
# Database helpers
# ─────────────────────────────────────────
SCRIPTS_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "scripts.json")

def load_scripts_db():
    if os.path.exists(SCRIPTS_DB_PATH):
        try:
            with open(SCRIPTS_DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def count_total_scripts():
    db = load_scripts_db()
    return sum(len(v) for v in db.values())


# ─────────────────────────────────────────
# Setup Cog — แบบ Hour Bot
# ─────────────────────────────────────────
class SetupCog(commands.Cog):
    """ติดตั้งบอทแบบ Hour — Script Search + Bypass + Welcome"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setup", description="🎮 ติดตั้งบอท — เลือกฟังค์ชั่นที่ต้องการ")
    @app_commands.describe(
        mode="เลือกติดตั้ง: full (ครบวงจร) / script (ค้นหาสคริปต์) / bypass (bypass ลิงค์)",
        channel="ช่องที่ต้องการติดตั้ง Panel (ไม่ระบุ = ช่องปัจจุบัน)",
        log_channel="ช่องที่จะส่ง Bypass Log / ผลลัพธ์ (ไม่ระบุ = ช่องเดียวกับ Panel)"
    )
    @app_commands.choices(mode=[
        app_commands.Choice(name="full (ครบวงจร — Script + Bypass)", value="full"),
        app_commands.Choice(name="script (ค้นหาสคริปต์)", value="script"),
        app_commands.Choice(name="bypass (Bypass Link)", value="bypass"),
    ])
    @app_commands.default_permissions(administrator=True)
    async def setup_cmd(
        self,
        interaction: discord.Interaction,
        mode: app_commands.Choice[str] = None,
        channel: discord.TextChannel = None,
        log_channel: discord.TextChannel = None
    ):
        """ติดตั้งบอทแบบ Hour — มีหลายโหมด: Full / Script / Bypass"""
        value = mode.value if mode else "full"
        target_channel = channel or interaction.channel
        from utils.config_manager import guild_config
        existing_log_id = guild_config.get_result_channel(interaction.guild.id) if interaction.guild else None
        if log_channel:
            result_log_channel = log_channel
        elif existing_log_id and interaction.guild:
            result_log_channel = interaction.guild.get_channel(existing_log_id) or target_channel
        else:
            result_log_channel = target_channel

        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            # Welcome Embed
            total_scripts = count_total_scripts()
            guild_name = interaction.guild.name if interaction.guild else "Server"
            mode_label = {"full": "ครบวงจร", "script": "ค้นหาสคริปต์", "bypass": "Bypass Link"}.get(value, value)

            # Build different panels based on mode
            try:
                if value == "bypass":
                    # Bypass-only Luxury Components V2 Panel
                    from cogs.panel import send_bypass_v2_panel, edit_bypass_v2_panel
                    bot_token = self.bot.http.token
                    existing_msg_id = guild_config.get_panel_message(interaction.guild.id) if interaction.guild else None
                    msg = None
                    if existing_msg_id:
                        ok, _ = await edit_bypass_v2_panel(target_channel.id, existing_msg_id, bot_token)
                        if ok:
                            try:
                                msg = await target_channel.fetch_message(existing_msg_id)
                            except Exception:
                                pass
                    if not msg:
                        ok, res = await send_bypass_v2_panel(target_channel.id, bot_token)
                        if ok and isinstance(res, dict) and "id" in res:
                            try:
                                msg = await target_channel.fetch_message(int(res["id"]))
                            except Exception:
                                pass

                elif value == "script":
                    # Script-only = NO PANEL, Q&A auto-reply handler only
                    welcome_embed = discord.Embed(
                        title="🎮 Script Search — Auto Q&A",
                        description="พิมพ์ชื่อเกม/แมพ → บอตตอบจาก RScript ทันที (Public)",
                        color=COLOR_INFO
                    )
                    msg = await target_channel.send(embed=welcome_embed)

                else:
                    # Full mode (default)
                    welcome_embed = discord.Embed(
                        title="🎮 KeyBypass — พร้อมใช้งาน!",
                        description=(
                            f"สวัสดี **{guild_name}**! 👋\n\n"
                            f"ยินดีต้อนรับสู่ **KeyBypass Bot** ระบบค้นหาสคริปต์ Roblox "
                            f"และ Bypass ลิงค์โฆษณาครบวงจร\n\n"
                            f"**🔹 สิ่งที่ทำได้:**\n"
                            f"• 🎮 ค้นหาสคริปต์ตามชื่อเกม/แมพ\n"
                            f"• 🔓 Bypass ลิงค์โฆษณา (Linkvertise, LootLabs, Platoboost)\n"
                            f"• 📊 ดูสถิติการใช้งาน\n\n"
                            f"**🔹 จำนวนสคริปต์ในระบบ:** `{total_scripts}+` รายการ\n"
                            f"**🔹 จำนวนเกมที่รองรับ:** `20+` เกม\n\n"
                            f"👇 **กดปุ่มด้านล่างเพื่อเริ่มใช้งาน!**"
                        ),
                        color=COLOR_PRIMARY
                    )
                    welcome_embed.set_thumbnail(url=interaction.client.user.display_avatar.url if interaction.client.user else None)
                    welcome_embed.set_footer(
                        text="KeyBypass • Self-hosted Engine",
                        icon_url=interaction.client.user.display_avatar.url if interaction.client.user else None
                    )
                    view = ScriptPanelView(self.bot)
                    msg = await target_channel.send(embed=welcome_embed, view=view)
            except discord.Forbidden:
                await interaction.followup.send(
                    f"❌ **บอทไม่มีสิทธิ์ส่งข้อความในช่อง {target_channel.mention}**\nโปรดตรวจสอบสิทธิ์ (Permission) ของบอทให้สามารถ Send Messages, Embed Links และ View Channel ในห้องนั้น",
                    ephemeral=True
                )
                return

            # Save config
            try:
                if interaction.guild:
                    guild_config.set_mode(interaction.guild.id, value)
                    if value == "bypass":
                        guild_config.set_bypass_channel(interaction.guild.id, target_channel.id)
                        guild_config.set_result_channel(interaction.guild.id, result_log_channel.id)
                        if 'msg' in locals() and msg:
                            guild_config.set_panel_message(interaction.guild.id, msg.id)
                    elif value == "script":
                        guild_config.set_script_channel(interaction.guild.id, target_channel.id)
                        if 'msg' in locals() and msg:
                            guild_config.set_panel_message(interaction.guild.id, msg.id)
                    else:  # full
                        guild_config.set_bypass_channel(interaction.guild.id, target_channel.id)
                        guild_config.set_script_channel(interaction.guild.id, target_channel.id)
                        guild_config.set_result_channel(interaction.guild.id, result_log_channel.id)
                        if 'msg' in locals() and msg:
                            guild_config.set_panel_message(interaction.guild.id, msg.id)
            except Exception as e:
                print(f"[Setup] Error saving guild config: {e}")

            # Tailor description based on mode
            if value == "bypass":
                mode_desc = (
                    f"✅ **โหมดที่เลือก:** `🔓 Bypass (Bypass Link เท่านั้น)`\n"
                    f"✅ **Bypass Panel ถูกติดตั้งที่:** {target_channel.mention}\n"
                    f"📝 **ห้องบันทึกผล (Log Channel):** {result_log_channel.mention}\n\n"
                    f"**คำสั่งที่เปิดใช้งานสำหรับโหมดนี้:**\n"
                    f"🔓 `/bypass` — Bypass ลิงค์ตรง (Linkvertise, LootLabs, Platoboost ฯลฯ)\n"
                    f"📊 `/stats` — สถิติการ Bypass ลิงค์\n"
                    f"🏓 `/ping` — เช็คสถานะและความเร็วบอท\n"
                    f"🎮 `/setup` — เปลี่ยนโหมดหรือตั้งค่าช่องใหม่\n\n"
                    f"*(คำสั่งและ Q&A ระบบค้นหาสคริปต์ถูกปิดการทำงานในเซิร์ฟเวอร์นี้ตามโหมดที่เลือก)*"
                )
            elif value == "script":
                mode_desc = (
                    f"✅ **โหมดที่เลือก:** `🎮 Script (ค้นหาสคริปต์เท่านั้น)`\n"
                    f"✅ **ห้องค้นหาสคริปต์:** {target_channel.mention}\n\n"
                    f"**คำสั่งที่เปิดใช้งานสำหรับโหมดนี้:**\n"
                    f"🔍 `/script-search` — ค้นหาสคริปต์ Roblox\n"
                    f"🔴 `/rscript` — ค้นหา RScript จาก API\n"
                    f"🟦 `/bloxscript` — ค้นหา Blox Script\n"
                    f"🏓 `/ping` — เช็คสถานะบอท\n"
                    f"🎮 `/setup` — เปลี่ยนโหมดหรือตั้งค่าช่องใหม่\n\n"
                    f"*(ระบบ Bypass ลิงค์ถูกปิดการทำงานในเซิร์ฟเวอร์นี้ตามโหมดที่เลือก)*"
                )
            else:
                mode_desc = (
                    f"✅ **โหมดที่เลือก:** `🌟 Full (ครบวงจร — Script + Bypass)`\n"
                    f"✅ **พาเนลถูกติดตั้งที่:** {target_channel.mention}\n"
                    f"📝 **ห้องบันทึกผล (Log Channel):** {result_log_channel.mention}\n\n"
                    f"**คำสั่งทั้งหมด:**\n"
                    f"🔓 `/bypass` — Bypass ลิงค์ตรง\n"
                    f"🔍 `/script-search` — ค้นหาสคริปต์\n"
                    f"🔴 `/rscript` — ค้นหา RScript\n"
                    f"🟦 `/bloxscript` — ค้นหา Blox Script\n"
                    f"📊 `/stats` — สถิติ\n"
                    f"🏓 `/ping` — เช็คสถานะ\n"
                    f"🎮 `/setup` — ติดตั้งบอทใหม่\n\n"
                    f"**หรือกดปุ่มใน Panel เพื่อใช้งาน!**"
                )

            success_embed = discord.Embed(
                title=f"✅ ติดตั้งระบบสำเร็จ ({mode_label})",
                description=mode_desc,
                color=COLOR_SUCCESS
            )
            await interaction.followup.send(embed=success_embed, ephemeral=True)

        except Exception as e:
            import traceback
            traceback.print_exc()
            await interaction.followup.send(
                f"❌ เกิดข้อผิดพลาด: `{e}`\nกรุณาตรวจสอบสิทธิ์ของบอท (ต้องมีสิทธิ์ส่งข้อความและ Embed)",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    # Register persistent view
    bot.add_view(ScriptPanelView(bot))
    await bot.add_cog(SetupCog(bot))