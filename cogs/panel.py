"""
Panel Cog — /setup panel command + Modal-based bypass interface.
Panel lives in one channel; results/logs appear in a separate configurable channel.
"""
import time
import discord
from discord import app_commands
from discord.ext import commands
from config import COLOR_PRIMARY, COLOR_SUCCESS, COLOR_ERROR, COLOR_WARNING, DEFAULT_COOLDOWN
from utils.bypasser import bypass_engine, DomainDetector
from utils.embeds import EmbedFactory
from utils.stats_manager import stats_manager
from utils.config_manager import guild_config


# ─────────────────────────────────────────
# Modal — Link Input Popup
# ─────────────────────────────────────────
class BypassModal(discord.ui.Modal, title="🔓 Bypass Ad-Link"):
    link_input = discord.ui.TextInput(
        label="Paste your ad-link here",
        placeholder="https://linkvertise.com/...",
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

        # Detect provider
        provider = DomainDetector.detect(url)

        # Ack with loading — ephemeral so only they see loading state
        loading_embed = EmbedFactory.create_loading(url, provider)
        await interaction.response.send_message(embed=loading_embed, ephemeral=True)

        start_time = time.time()
        result = await bypass_engine.bypass_url(url)
        elapsed = time.time() - start_time

        guild_id = interaction.guild.id if interaction.guild else None

        if result.get("success"):
            direct_url = result["direct_url"]
            endpoint_used = result.get("endpoint_used", "unknown")
            chain_note = result.get("chain_note", "")
            is_key = result.get("is_key", False)

            # Record stats
            stats_manager.record_bypass(provider["key"], interaction.user.id, guild_id)

            # ── Ephemeral result to the user (link they take back) ──────────
            success_embed = discord.Embed(
                title="🔑 Key / Direct Link" if result.get("is_key") else "✅ Bypass สำเร็จ!",
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
            success_embed.set_footer(text="ข้อความนี้มองเห็นได้เฉพาะคุณ")

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
                    else:
                        print(f"[Panel] Log channel {self.result_channel_id} not found in guild or via fetch.")
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
    """Persistent View — must be added to bot on startup."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔓  Bypass Link",
        style=discord.ButtonStyle.success,
        custom_id="panel:bypass_btn",
        row=0
    )
    async def bypass_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check cooldown via a simple in-memory dict
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

        # Get result channel config
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

    @app_commands.command(name="bypass-panel", description="🔓 สร้าง Bypass Panel ในช่องนี้ (ใช้ /setup สำหรับแบบครบวงจร)")
    @app_commands.describe(result_channel="ช่องที่จะแสดงผล Log ของการ Bypass (ถ้าไม่ระบุ = ช่องเดียวกัน)")
    @app_commands.default_permissions(administrator=True)
    async def setup_panel(self, interaction: discord.Interaction, result_channel: discord.TextChannel = None):
        """Deploy the interactive bypass panel embed in this channel."""
        try:
            # Save config
            if interaction.guild:
                if result_channel:
                    guild_config.set_result_channel(interaction.guild.id, result_channel.id)
                    result_ch = result_channel
                else:
                    existing_id = guild_config.get_result_channel(interaction.guild.id)
                    if existing_id:
                        result_ch = interaction.guild.get_channel(existing_id) or interaction.channel
                    else:
                        result_ch = interaction.channel
                        guild_config.set_result_channel(interaction.guild.id, interaction.channel.id)
                guild_config.set_bypass_channel(interaction.guild.id, interaction.channel.id)
            else:
                result_ch = interaction.channel

            # Build panel embed
            panel_embed = discord.Embed(
                title="🔓  Bypass Ad-Link Panel",
                description=(
                    "กด **Bypass Link** เพื่อเปิดหน้าต่างใส่ลิงค์\n"
                    "ระบบจะประมวลผลและส่งลิงค์ตรงกลับมาให้คุณ **แบบส่วนตัว** (เห็นแค่คุณคนเดียว)\n\n"
                    "**รองรับ:**\n"
                    "> ⚡ Linkvertise  •  💎 LootLabs  •  💼 Work.ink\n"
                    "> 🔓 Rekonise  •  🔒 Lockr  •  🚀 Boost.ink\n"
                    "> 🪐 Platoboost (Delta)  •  ▶️ Sub2Unlock  •  📁 MediaFire\n\n"
                    "📝 ผลลัพธ์การ Bypass จะถูก Log ใน "
                    f"{result_ch.mention if hasattr(result_ch, 'mention') else 'ช่องนี้'}"
                ),
                color=COLOR_PRIMARY
            )
            panel_embed.set_footer(text="Self-hosted Bypass Engine • No external API dependency")

            view = PanelView()

            # Send the Panel directly as the public response to the slash command
            await interaction.response.send_message(embed=panel_embed, view=view)
            msg = await interaction.original_response()
            if interaction.guild:
                guild_config.set_panel_message(interaction.guild.id, msg.id)

        except Exception as e:
            import traceback
            traceback.print_exc()
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"❌ **เกิดข้อผิดพลาดในการสร้าง Panel:** `{e}`",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❌ **เกิดข้อผิดพลาดในการสร้าง Panel:** `{e}`",
                    ephemeral=True
                )

    @app_commands.command(name="config", description="แก้ไขการตั้งค่า Result/Log Channel")
    @app_commands.describe(result_channel="ช่องที่ต้องการรับ Log ใหม่")
    @app_commands.default_permissions(administrator=True)
    async def config_channel(self, interaction: discord.Interaction, result_channel: discord.TextChannel):
        guild_config.set_result_channel(interaction.guild.id, result_channel.id)
        await interaction.response.send_message(
            f"✅ Log channel ถูกเปลี่ยนเป็น {result_channel.mention} แล้ว!",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    # Register persistent view so buttons work after restarts
    bot.add_view(PanelView())
    await bot.add_cog(PanelCog(bot))
