"""
Bypass Cog — /bypass slash command (direct, no panel needed).
"""
import time
import discord
from discord import app_commands
from discord.ext import commands
from config import DEFAULT_COOLDOWN
from utils.bypasser import bypass_engine, DomainDetector
from utils.stats_manager import stats_manager
from utils.embeds import EmbedFactory, BypassButtonsView
from utils.config_manager import guild_config


class BypassCog(commands.Cog):
    """Cog handling /bypass slash command."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """ตรวจสอบว่าเซิร์ฟเวอร์นี้เปิดโหมด Bypass หรือไม่"""
        if interaction.guild and not guild_config.is_bypass_enabled(interaction.guild.id):
            await interaction.response.send_message(
                "❌ **คำสั่งนี้ถูกปิดการใช้งานในเซิร์ฟเวอร์นี้**\n"
                "• ปัจจุบันเซิร์ฟเวอร์ถูกตั้งค่าเป็นโหมด `🎮 Script Only`\n"
                "• แอดมินสามารถเปิดใช้งานได้โดยใช้คำสั่ง `/setup mode:full` หรือ `/setup mode:bypass`",
                ephemeral=True
            )
            return False
        return True

    @app_commands.command(name="bypass", description="Bypass ลิงค์โฆษณาโดยตรง (Linkvertise, LootLabs, Work.ink ฯลฯ)")
    @app_commands.describe(
        url="ลิงค์โฆษณาที่ต้องการ Bypass",
        private="ส่งผลลัพธ์แบบส่วนตัว (เห็นแค่คุณ)"
    )
    @app_commands.checks.cooldown(1, DEFAULT_COOLDOWN, key=lambda i: i.user.id)
    async def bypass_slash(self, interaction: discord.Interaction, url: str, private: bool = True):
        url = url.strip()

        if not (url.startswith("http://") or url.startswith("https://")):
            await interaction.response.send_message(
                "❌ **URL ไม่ถูกต้อง!** ต้องขึ้นต้นด้วย `http://` หรือ `https://`",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=private, thinking=True)
        provider = DomainDetector.detect(url)
        loading_embed = EmbedFactory.create_loading(url, provider)
        await interaction.edit_original_response(embed=loading_embed)

        start_time = time.time()
        try:
            result = await asyncio.wait_for(bypass_engine.bypass_url(url), timeout=11.0)
        except asyncio.TimeoutError:
            result = {
                "success": False,
                "error": "⏱️ การ Bypass ใช้เวลานานเกินกำหนด (Timeout 11s) ลิงก์อาจติด Cloudflare Turnstile ขั้นสูง",
                "provider": provider,
                "time_taken": 11.0
            }
        elapsed = time.time() - start_time

        guild_id = interaction.guild.id if interaction.guild else None

        if result.get("success"):
            direct_url = result["direct_url"]
            endpoint_used = result.get("endpoint_used", "unknown")

            stats_manager.record_bypass(provider["key"], interaction.user.id, guild_id)

            chain_note = result.get("chain_note", "")
            is_key = result.get("is_key", False)

            embed = EmbedFactory.create_success(
                original_url=url,
                direct_url=direct_url,
                provider=provider,
                elapsed_time=elapsed,
                sent_dm=False,
                chain_note=chain_note,
                is_key=is_key,
                endpoint_used=endpoint_used
            )
            view = BypassButtonsView(direct_url=direct_url, user_id=interaction.user.id)
            await interaction.edit_original_response(embed=embed, view=view)

            # Log to result channel if configured
            if guild_id:
                result_ch_id = guild_config.get_result_channel(guild_id)
                if result_ch_id:
                    try:
                        log_ch = interaction.guild.get_channel(result_ch_id) if interaction.guild else None
                        if not log_ch and self.bot:
                            try:
                                log_ch = await self.bot.fetch_channel(result_ch_id)
                            except Exception:
                                log_ch = None
                        if log_ch:
                            log_embed = EmbedFactory.create_log(
                                user=interaction.user,
                                provider=provider,
                                original_url=url,
                                elapsed=elapsed,
                                success=True,
                                endpoint=endpoint_used
                            )
                            await log_ch.send(embed=log_embed)
                        else:
                            print(f"[BypassCog] Log channel {result_ch_id} could not be resolved.")
                    except Exception as e:
                        print(f"[BypassCog] Log send error: {e}")
        else:
            error_embed = EmbedFactory.create_error(url, provider, result.get("error", "Unknown error"))
            await interaction.edit_original_response(embed=error_embed)

            if guild_id:
                result_ch_id = guild_config.get_result_channel(guild_id)
                if result_ch_id:
                    try:
                        log_ch = interaction.guild.get_channel(result_ch_id) if interaction.guild else None
                        if not log_ch and self.bot:
                            try:
                                log_ch = await self.bot.fetch_channel(result_ch_id)
                            except Exception:
                                log_ch = None
                        if log_ch:
                            await log_ch.send(embed=EmbedFactory.create_log(
                                user=interaction.user,
                                provider=provider,
                                original_url=url,
                                elapsed=elapsed,
                                success=False
                            ))
                    except Exception as e:
                        print(f"[BypassCog] Error log send error: {e}")

    @bypass_slash.error
    async def bypass_slash_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        original_error = getattr(error, 'original', error)

        if isinstance(error, app_commands.CommandOnCooldown):
            embed = EmbedFactory.create_cooldown(error.retry_after)
        else:
            print(f"[BypassCog Error]: {original_error}")
            embed = discord.Embed(
                title="❌ เกิดข้อผิดพลาด",
                description=f"```{str(original_error)}```",
                color=0xFF3860
            )

        try:
            if interaction.response.is_done():
                await interaction.edit_original_response(content=None, embed=embed, view=None)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception:
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except Exception:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(BypassCog(bot))
