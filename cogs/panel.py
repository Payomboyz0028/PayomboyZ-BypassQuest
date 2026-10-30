"""
Panel Cog — /bypass-panel command + Modal-based bypass interface.
Upgraded to Discord Components V2 Container Panel with Zero-Hang Fast Pipeline.
"""
import time
import re
import asyncio
import aiohttp
from typing import Optional, Tuple, Any
import discord
from discord import app_commands
from discord.ext import commands
from config import COLOR_PRIMARY, COLOR_SUCCESS, COLOR_ERROR, COLOR_WARNING, DEFAULT_COOLDOWN
from utils.bypasser import bypass_engine, DomainDetector
from utils.embeds import EmbedFactory
from utils.stats_manager import stats_manager
from utils.config_manager import guild_config

DEFAULT_BYPASS_BANNER_URL = "https://cdn.discordapp.com/attachments/1555389925615079484/1565320390392156200/payomboyz_bypass_adlink.gif?ex=6ae5cb37&is=6ae479b7&hm=4e0efeac92f40136dfe873c704c523d7b452b5c07a4f830a7fa69fffebf27cdd&"


def build_bypass_v2_payload(banner_url: Optional[str] = None) -> dict:
    """Builds Discord Components V2 Container message (flags: 32768) matching Luxury Panel."""
    banner = banner_url or DEFAULT_BYPASS_BANNER_URL
    body_text = (
        "> <:payomboyz:1551064225974325318> **ระบบปลดล็อกลิงก์โฆษณาและคีย์สคริปต์อัตโนมัติ (Anti-Adwall Protocol)**\n"
        "> ⚡ **ประมวลผลความเร็วสูง ไร้การรอคอย • ส่งผลลัพธ์ส่วนตัว 100%**\n"
        "> 🛡️ **Zero-Retention Architecture • ไม่บันทึกข้อมูลลิงก์หรือ IP ของผู้ใช้**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🌐 **บริการที่รองรับ (Supported Providers):**\n"
        "• ⚡ **Linkvertise** (Dynamic Token / Direct Bypass)\n"
        "• 💎 **LootLabs & LootLinks** (Fast-Forward Task Engine)\n"
        "• 🪐 **Platoboost & PlatoRelay** (Delta Executor Key System)\n"
        "• 💼 **Work.ink** (Reverse DUF Decoder & Instant Redirect)\n"
        "• 🔓 **Rekonise & Boost.ink** (Social Unlock API)\n"
        "• 📁 **File Hosts** (MediaFire, PixelDrain, GoFile, KrakenFiles)\n\n"
        "🟢 **วิธีใช้งาน:** กดปุ่ม **\"🔓 Bypass Link\"** ด้านล่าง แล้ววางลิงก์ที่ต้องการปลดล็อกได้ทันที!"
    )
    return {
        "flags": 32768,
        "content": "",
        "embeds": [],
        "components": [
            {
                "type": 17,
                "accent_color": 65382,
                "components": [
                    {
                        "type": 10,
                        "content": "## <a:pbg_wing_l:1562553182859563150> **PAYOMBØYZ BYPASS SYSTEM** <a:pbg_wing_r:1562553185325940748>\n### 🔓 **AD-LINK & KEY SYSTEM BYPASS ENGINE**"
                    },
                    {"type": 14, "divider": True, "spacing": 1},
                    {"type": 10, "content": body_text},
                    {"type": 14, "divider": True, "spacing": 1},
                    {
                        "type": 1,
                        "components": [
                            {
                                "type": 2,
                                "custom_id": "panel:bypass_btn",
                                "style": 3,
                                "label": "Bypass Link",
                                "emoji": {"name": "🔓"}
                            },
                            {
                                "type": 2,
                                "custom_id": "panel:stats_btn",
                                "style": 2,
                                "label": "Stats",
                                "emoji": {"name": "📊"}
                            }
                        ]
                    },
                    {"type": 14, "divider": True, "spacing": 1},
                    {
                        "type": 10,
                        "content": "**POWERED BY PAYOMBØYZ BYPASS CORE • ZERO-WAIT ENGINE**"
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


async def send_bypass_v2_panel(channel_id: int, bot_token: str, banner_url: Optional[str] = None) -> Tuple[bool, Any]:
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json",
        "User-Agent": "DiscordBot (https://github.com/Payomboyz0028, 1.0)"
    }
    payload = build_bypass_v2_payload(banner_url=banner_url)
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as r:
            try:
                data = await r.json()
            except Exception:
                data = await r.text()
            return r.status in (200, 201), data


async def edit_bypass_v2_panel(channel_id: int, message_id: int, bot_token: str, banner_url: Optional[str] = None) -> Tuple[bool, Any]:
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}"
    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json",
        "User-Agent": "DiscordBot (https://github.com/Payomboyz0028, 1.0)"
    }
    payload = build_bypass_v2_payload(banner_url=banner_url)
    async with aiohttp.ClientSession() as session:
        async with session.patch(url, headers=headers, json=payload) as r:
            try:
                data = await r.json()
            except Exception:
                data = await r.text()
            return r.status == 200, data


# ─────────────────────────────────────────
# Modal — Link Input Popup
# ─────────────────────────────────────────
class BypassModal(discord.ui.Modal, title="🔓 Bypass Ad-Link"):
    link_input = discord.ui.TextInput(
        label="Paste your ad-link here",
        placeholder="https://linkvertise.com/... หรือ Platoboost, LootLabs, Work.ink",
        style=discord.TextStyle.short,
        required=True,
        max_length=1000
    )

    def __init__(self, result_channel_id: int | None):
        super().__init__(timeout=120)
        self.result_channel_id = result_channel_id

    async def on_submit(self, interaction: discord.Interaction):
        url = self.link_input.value.strip()

        if not (url.startswith("http://") or url.startswith("https://")):
            await interaction.response.send_message(
                "❌ **URL ไม่ถูกต้อง!** ต้องขึ้นต้นด้วย `http://` หรือ `https://`",
                ephemeral=True
            )
            return

        # 1. Immediate defer to prevent 3-second interaction expiration
        await interaction.response.defer(ephemeral=True, thinking=True)

        provider = DomainDetector.detect(url)
        loading_embed = EmbedFactory.create_loading(url, provider)
        await interaction.edit_original_response(embed=loading_embed)

        start_time = time.time()
        try:
            result = await asyncio.wait_for(bypass_engine.bypass_url(url), timeout=11.0)
        except asyncio.TimeoutError:
            result = {
                "success": False,
                "error": "⏱️ การ Bypass ใช้เวลานานเกินกำหนด (Timeout 11s) ลิงก์อาจติด Cloudflare Turnstile ชั้นสูง กรุณาลองใหม่อีกครั้ง",
                "provider": provider,
                "time_taken": 11.0
            }
        elapsed = time.time() - start_time
        guild_id = interaction.guild.id if interaction.guild else None

        if result.get("success"):
            direct_url = result["direct_url"]
            endpoint_used = result.get("endpoint_used", "unknown")
            chain_note = result.get("chain_note", "")
            is_key = result.get("is_key", False)

            # Record stats
            stats_manager.record_bypass(provider["key"], interaction.user.id, guild_id)

            # ── Ephemeral result to the user ────────────────────────────────
            success_embed = discord.Embed(
                title="🔑 Key / Direct Link" if is_key else "✅ Bypass สำเร็จ!",
                description=(
                    f"**นำลิงค์/Key ด้านล่างไปใช้เพื่อรับ Key ของคุณ:**\n"
                    f"```\n{direct_url}\n```"
                ),
                color=COLOR_SUCCESS
            )
            success_embed.add_field(name="⏱️ ใช้เวลา", value=f"`{elapsed:.2f}s`", inline=True)
            success_embed.add_field(name="🔌 Engine", value=f"`{endpoint_used}`", inline=True)
            if chain_note:
                success_embed.add_field(name="⛓️ Chain", value=f"`{chain_note}`", inline=True)
            success_embed.set_footer(text="ข้อความนี้มองเห็นได้เฉพาะคุณ • Zero Retention")

            # Button to copy link
            view = _ResultView(direct_url, interaction.user.id)
            await interaction.edit_original_response(embed=success_embed, view=view)

            # ── Public log to result channel ─────────────────────────────────
            if guild_id and self.result_channel_id:
                try:
                    log_channel = interaction.guild.get_channel(self.result_channel_id) if interaction.guild else None
                    if not log_channel and interaction.client:
                        try:
                            log_channel = await interaction.client.fetch_channel(self.result_channel_id)
                        except Exception:
                            log_channel = None
                    if log_channel:
                        log_embed = EmbedFactory.create_log(
                            user=interaction.user,
                            provider=provider,
                            original_url=url,
                            elapsed=elapsed,
                            success=True,
                            endpoint=endpoint_used
                        )
                        await log_channel.send(embed=log_embed)
                except Exception as e:
                    print(f"[Panel] Failed to send log: {e}")

        else:
            error_msg = result.get("error", "Unknown error")
            err_embed = EmbedFactory.create_error(url, provider, error_msg)
            await interaction.edit_original_response(embed=err_embed)

            # Log failure too
            if guild_id and self.result_channel_id:
                try:
                    log_channel = interaction.guild.get_channel(self.result_channel_id) if interaction.guild else None
                    if not log_channel and interaction.client:
                        try:
                            log_channel = await interaction.client.fetch_channel(self.result_channel_id)
                        except Exception:
                            log_channel = None
                    if log_channel:
                        log_embed = EmbedFactory.create_log(
                            user=interaction.user,
                            provider=provider,
                            original_url=url,
                            elapsed=elapsed,
                            success=False
                        )
                        await log_channel.send(embed=log_embed)
                except Exception as e:
                    print(f"[Panel] Failed to send error log: {e}")


# ─────────────────────────────────────────
# Result View — ephemeral buttons
# ─────────────────────────────────────────
class _ResultView(discord.ui.View):
    def __init__(self, direct_url: str, user_id: int):
        super().__init__(timeout=300)
        self.direct_url = direct_url
        self.user_id = user_id

        if len(direct_url) <= 512 and direct_url.startswith("http"):
            self.add_item(discord.ui.Button(
                label="เปิดลิงค์", style=discord.ButtonStyle.link, url=direct_url, emoji="🔗"
            ))

    @discord.ui.button(label="Copy Link", style=discord.ButtonStyle.primary, emoji="📋")
    async def copy_cb(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"📋 **ลิงค์สำหรับ Copy:**\n```{self.direct_url}```",
            ephemeral=True
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id


# ─────────────────────────────────────────
# Panel Persistent View (survives restarts)
# ─────────────────────────────────────────
class PanelView(discord.ui.View):
    """Persistent View — registered on bot startup."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔓  Bypass Link",
        style=discord.ButtonStyle.success,
        custom_id="panel:bypass_btn",
        row=0
    )
    async def bypass_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not hasattr(self, "_cooldowns"):
            self._cooldowns = {}
        now = time.time()
        last = self._cooldowns.get(interaction.user.id, 0)
        if now - last < DEFAULT_COOLDOWN:
            remaining = DEFAULT_COOLDOWN - (now - last)
            await interaction.response.send_message(
                f"⏳ รอ **{remaining:.1f}s** ก่อนกด bypass อีกครั้ง",
                ephemeral=True
            )
            return
        self._cooldowns[interaction.user.id] = now

        result_ch_id = None
        if interaction.guild:
            result_ch_id = guild_config.get_result_channel(interaction.guild.id)

        modal = BypassModal(result_channel_id=result_ch_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="📊  Stats",
        style=discord.ButtonStyle.secondary,
        custom_id="panel:stats_btn",
        row=0
    )
    async def stats_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        stats = stats_manager.get_summary()
        embed = EmbedFactory.create_stats(stats)
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ─────────────────────────────────────────
# Panel Cog
# ─────────────────────────────────────────
class PanelCog(commands.Cog):
    """Manages the interactive panel setup and lifecycle."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="bypass-panel", description="🔓 ติดตั้งหรืออัปเดตแผงควบคุม Bypass (Components V2 Luxury Panel)")
    @app_commands.describe(result_channel="ช่องที่จะแสดงผล Log ของการ Bypass (ถ้าไม่ระบุ = ช่องเดิม)")
    @app_commands.default_permissions(administrator=True)
    async def setup_panel(self, interaction: discord.Interaction, result_channel: discord.TextChannel = None):
        """Deploy or update the interactive bypass panel to Discord Components V2 Container."""
        await interaction.response.defer(ephemeral=True)
        try:
            target_channel = interaction.channel
            bot_token = self.bot.http.token

            if interaction.guild:
                if result_channel:
                    guild_config.set_result_channel(interaction.guild.id, result_channel.id)
                guild_config.set_bypass_channel(interaction.guild.id, target_channel.id)

            existing_msg_id = guild_config.get_panel_message(interaction.guild.id) if interaction.guild else None
            updated = False

            if existing_msg_id:
                ok, _ = await edit_bypass_v2_panel(target_channel.id, existing_msg_id, bot_token)
                if ok:
                    updated = True

            if not updated:
                ok, res = await send_bypass_v2_panel(target_channel.id, bot_token)
                if ok and isinstance(res, dict) and "id" in res:
                    if interaction.guild:
                        guild_config.set_panel_message(interaction.guild.id, int(res["id"]))

            await interaction.followup.send(
                f"✅ **ติดตั้ง / อัปเดตแผงควบคุม Bypass Components V2 สำเร็จ!** ในช่อง {target_channel.mention}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(f"❌ เกิดข้อผิดพลาดในการติดตั้ง Panel: `{e}`", ephemeral=True)

    @app_commands.command(name="config", description="แก้ไขการตั้งค่า Result/Log Channel")
    @app_commands.describe(result_channel="ช่องที่ต้องการรับ Log ใหม่")
    @app_commands.default_permissions(administrator=True)
    async def config_channel(self, interaction: discord.Interaction, result_channel: discord.TextChannel):
        guild_config.set_result_channel(interaction.guild.id, result_channel.id)
        await interaction.response.send_message(
            f"✅ Log channel ถูกเปลี่ยนเป็น {result_channel.mention} แล้ว!",
            ephemeral=True
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Auto-detects ad links pasted directly into the bypass channel and bypasses them immediately."""
        if message.author.bot or not message.guild:
            return

        bypass_ch_id = guild_config.get_bypass_channel(message.guild.id)
        if bypass_ch_id and message.channel.id != bypass_ch_id:
            return
        if not bypass_ch_id and "bypass" not in message.channel.name.lower():
            return

        content = message.content.strip()
        match = re.search(r"https?://[^\s]+", content)
        if not match:
            return

        url = match.group(0)
        provider = DomainDetector.detect(url)
        if provider["key"] == "general" and not DomainDetector.is_chainable(url):
            return

        # Start instant bypass with live status message
        status_msg = await message.reply(
            f"⏳ **[PAYOMBØYZ BYPASS]** กำลังปลดล็อกลิงก์ `{provider['name']}` กรุณารอสักครู่ (ไม่เกิน 5-9 วิ)...",
            mention_author=True
        )

        start_time = time.time()
        try:
            result = await asyncio.wait_for(bypass_engine.bypass_url(url), timeout=11.0)
        except asyncio.TimeoutError:
            result = {
                "success": False,
                "error": "⏱️ การ Bypass ใช้เวลานานเกินกำหนด (Timeout 11s) ลิงก์อาจติด Cloudflare ขั้นสูง",
                "provider": provider,
                "time_taken": 11.0
            }
        elapsed = time.time() - start_time

        guild_id = message.guild.id
        if result.get("success"):
            direct_url = result["direct_url"]
            endpoint_used = result.get("endpoint_used", "unknown")
            is_key = result.get("is_key", False)

            stats_manager.record_bypass(provider["key"], message.author.id, guild_id)

            embed = EmbedFactory.create_success(
                original_url=url,
                direct_url=direct_url,
                provider=provider,
                elapsed_time=elapsed,
                sent_dm=False,
                chain_note=result.get("chain_note", ""),
                is_key=is_key,
                endpoint_used=endpoint_used
            )
            view = _ResultView(direct_url, message.author.id)
            await status_msg.edit(content=None, embed=embed, view=view)

            # Public log channel if set
            result_ch_id = guild_config.get_result_channel(guild_id)
            if result_ch_id and result_ch_id != message.channel.id:
                try:
                    log_ch = message.guild.get_channel(result_ch_id)
                    if log_ch:
                        await log_ch.send(embed=EmbedFactory.create_log(
                            user=message.author,
                            provider=provider,
                            original_url=url,
                            elapsed=elapsed,
                            success=True,
                            endpoint=endpoint_used
                        ))
                except Exception:
                    pass
        else:
            err_embed = EmbedFactory.create_error(url, provider, result.get("error", "Bypass Failed"))
            await status_msg.edit(content=None, embed=err_embed)


async def setup(bot: commands.Bot):
    bot.add_view(PanelView())
    await bot.add_cog(PanelCog(bot))
