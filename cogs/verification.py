"""
PAYOMBØYZ Verification Cog — 100% FlowAuth Clone & Self-Hosted Replacement.
Handles:
  • /setpanel verify [role] [channel]
  • Ephemeral Captcha Challenge with Pillow-generated noise image
  • Modal submission & instant role assignment
  • "Already verified" detection
  • Persistent button views across bot restarts
"""
import os
import io
import time
import asyncio
import traceback
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from utils.config_manager import guild_config
from utils.verify_manager import verify_manager
from utils.embeds import EmbedFactory
from utils.verify_card_generator import generate_verification_card_sync

COLOR_VERIFY_RED = 0xFF0000  # Exact FlowAuth red accent
DEFAULT_VERIFIED_ROLE_ID = 1549536757484101814  # PAYOMBØYZ HUB: ⊹-:-.˚ ยืนยันตัวตนแล้ว・


# ─────────────────────────────────────────────────────────────
# Modal — Captcha Answer Input
# ─────────────────────────────────────────────────────────────
class VerifyAnswerModal(discord.ui.Modal, title="PAYOMBØYZ Verification"):
    answer_input = discord.ui.TextInput(
        label="ยืนยันคำตอบ *",
        placeholder="พิมพ์ตัวอักษรที่เห็นในภาพ...",
        style=discord.TextStyle.short,
        required=True,
        min_length=3,
        max_length=10
    )

    def __init__(self, target_role_id: int):
        super().__init__(timeout=180)
        self.target_role_id = target_role_id

    async def on_submit(self, interaction: discord.Interaction):
        user_answer = self.answer_input.value.strip()
        is_valid, msg, role_id = verify_manager.verify_answer(interaction.user.id, user_answer)

        role_to_give_id = role_id or self.target_role_id

        if not is_valid:
            await interaction.response.send_message(
                f"{msg}\nคุณพิมพ์: `{user_answer}`",
                ephemeral=True
            )
            return

        # Correct answer! Give verified role
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("❌ คำสั่งนี้สามารถใช้งานได้ในเซิร์ฟเวอร์เท่านั้น", ephemeral=True)
            return

        role = guild.get_role(role_to_give_id)
        if not role:
            # Fallback search by ID or name
            for r in guild.roles:
                if r.id == role_to_give_id or "ยืนยัน" in r.name:
                    role = r
                    break

        if not role:
            await interaction.response.send_message(
                f"⚠️ ยืนยันคำตอบถูกต้อง แต่ไม่พบบทบาท (Role ID: `{role_to_give_id}`) ในเซิร์ฟเวอร์ โปรดติดต่อแอดมิน",
                ephemeral=True
            )
            return

        member = interaction.user
        if not isinstance(member, discord.Member):
            try:
                member = await guild.fetch_member(interaction.user.id)
            except Exception:
                pass

        try:
            await member.add_roles(role, reason="PAYOMBØYZ Captcha Verification Passed")
            await interaction.response.send_message(
                f"Verification complete. คุณได้รับ {role.mention}",
                ephemeral=True
            )
            
            # Send audit log to verification log channel
            log_ch_id = guild_config.get_verify_log_channel(guild.id)
            if log_ch_id:
                log_ch = guild.get_channel(log_ch_id)
                if not log_ch and interaction.client:
                    try:
                        log_ch = await interaction.client.fetch_channel(log_ch_id)
                    except Exception:
                        log_ch = None

                if log_ch:
                    try:
                        # 1. Fetch avatar bytes with robust multi-layer fallback
                        avatar_bytes = None
                        try:
                            avatar_bytes = await member.display_avatar.with_format("png").with_size(256).read()
                        except Exception:
                            try:
                                avatar_bytes = await member.display_avatar.read()
                            except Exception:
                                try:
                                    import aiohttp
                                    async with aiohttp.ClientSession() as av_sess:
                                        async with av_sess.get(member.display_avatar.url) as av_r:
                                            if av_r.status == 200:
                                                avatar_bytes = await av_r.read()
                                except Exception:
                                    avatar_bytes = None

                        # Fetch exact live member count
                        m_count = getattr(guild, "member_count", 0)
                        if not m_count or m_count < 100:
                            try:
                                f_g = await interaction.client.fetch_guild(guild.id, with_counts=True)
                                m_count = f_g.approximate_member_count or f_g.member_count or m_count
                            except Exception:
                                pass

                        # 2. Render badass cyber verification card
                        card_buf = await asyncio.to_thread(
                            generate_verification_card_sync,
                            user_name=member.display_name,
                            user_handle=member.name,
                            user_id=str(member.id),
                            role_name=role.name,
                            guild_name=guild.name,
                            member_count=m_count,
                            avatar_bytes=avatar_bytes
                        )

                        # 3. Create HighSpec & Luxury Discord Welcome Layout (100% clone of Message ID 1563744661833654305)
                        welcome_content = f"🕊️ ยินดีต้อนรับคุณ {member.mention} เข้าสู่เซิร์ฟเวอร์ **{guild.name}** ! 🕊️"
                        
                        log_embed = discord.Embed(
                            title=f"» • WELCOME {member.display_name} • «",
                            color=0xF1C40F
                        )
                        log_embed.set_author(
                            name=f"{member.name} [{member.id}]",
                            icon_url=member.display_avatar.url
                        )

                        # Top-right GIF thumbnail (Itachi ANBU Cat Mask / Anime GIF)
                        thumb_candidates = [
                            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "welcome_thumb.gif")),
                            os.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "welcome_thumb.gif")),
                            r"d:\Deobfuscate\Lerning\welcome_thumb.gif",
                            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "welcome_thumb.gif")),
                        ]
                        thumb_path = next((p for p in thumb_candidates if os.path.exists(p)), None)

                        card_file = discord.File(fp=card_buf, filename="verify_panel.png")
                        files_to_send = [card_file]

                        if thumb_path and os.path.exists(thumb_path):
                            log_embed.set_thumbnail(url="attachment://welcome_thumb.gif")
                            files_to_send.append(discord.File(thumb_path, filename="welcome_thumb.gif"))
                        else:
                            log_embed.set_thumbnail(url="https://cdn.discordapp.com/avatars/743411121301618721/a_ac83ebefff9091406a5338b32dee5543.gif?size=1024")

                        now_ts = int(time.time())
                        log_embed.description = (
                            f"════════════════════════════════════════════\n"
                            f"• ยินดีต้อนรับ ➔ {member.mention}\n"
                            f"  ({member.name})\n"
                            f"• ยศที่ได้รับ ➔ {role.mention}\n"
                            f"• สมาชิกคนที่ ➔ `#{m_count:,}`\n"
                            f"• เวลาที่ยืนยัน ➔ <t:{now_ts}:F>\n"
                            f"  ( <t:{now_ts}:R> )\n"
                            f"════════════════════════════════════════════\n\n"
                            f"> 👑 **PAYOMBØYZ SENTINEL VERIFICATION PASSED**\n"
                            f"> เข้าสู่ศูนย์รวม Script Hub, Auto Quest & เครื่องมือระดับพรีเมียม"
                        )
                        log_embed.set_image(url="attachment://verify_panel.png")
                        guild_icon_url = guild.icon.url if guild.icon else None
                        log_embed.set_footer(text=f"PAYOMBOYZ X WELCOME • {guild.name}", icon_url=guild_icon_url)

                        await log_ch.send(content=welcome_content, files=files_to_send, embed=log_embed)
                    except Exception as gen_err:
                        print(f"[VerificationCog] Panel card generation error: {gen_err}")
                        traceback.print_exc()
                        log_embed = discord.Embed(
                            title="🛡️ การยืนยันตัวตนสำเร็จ",
                            description=f"👤 **ผู้ใช้:** {member.mention} (`{member.id}`)\n🏷️ **ได้รับยศ:** {role.mention}\n⏰ **เวลา:** <t:{int(time.time())}:R>",
                            color=0x00FF7F
                        )
                        log_embed.set_thumbnail(url=member.display_avatar.url)
                        await log_ch.send(embed=log_embed)

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ **บอทไม่มีสิทธิ์ให้ยศแก่คุณ!**\nโปรดตรวจสอบว่ายศของบอทอยู่สูงกว่ายศที่ต้องการมอบใน Server Settings > Roles",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ เกิดข้อผิดพลาดในการมอบยศ: `{e}`",
                ephemeral=True
            )


# ─────────────────────────────────────────────────────────────
# Ephemeral View — Captcha Challenge (Answer Button)
# ─────────────────────────────────────────────────────────────
class CaptchaChallengeView(discord.ui.View):
    def __init__(self, user_id: int, role_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.role_id = role_id

    @discord.ui.button(
        label="ยืนยันคำตอบ",
        style=discord.ButtonStyle.primary,
        custom_id="payom_verify:submit_btn"
    )
    async def btn_answer(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ ข้อความนี้เป็นของคุณคนอื่น โปรดกดปุ่มยืนยันตัวตนของคุณเอง", ephemeral=True)
            return

        session = verify_manager.get_challenge(self.user_id)
        if not session:
            await interaction.response.send_message(
                "⚠️ เซสชันการยืนยันตัวตนหมดอายุแล้ว โปรดกดปุ่ม **\"ยืนยันตัวตน\"** ด้านบนใหม่อีกครั้ง",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(VerifyAnswerModal(target_role_id=self.role_id))


# ─────────────────────────────────────────────────────────────
# Persistent View — Main Verification Panel Button
# ─────────────────────────────────────────────────────────────
class VerifyPanelView(discord.ui.View):
    """Persistent View for Verification Panel — survives bot restarts."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="ยืนยันตัวตน",
        style=discord.ButtonStyle.success,
        custom_id="payom_verify:start"
    )
    async def btn_verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("❌ สามารถใช้งานได้เฉพาะในเซิร์ฟเวอร์", ephemeral=True)
            return

        # Resolve verified role
        role_id = guild_config.get_verify_role(guild.id) or DEFAULT_VERIFIED_ROLE_ID
        role = guild.get_role(role_id)
        if not role:
            for r in guild.roles:
                if r.id == DEFAULT_VERIFIED_ROLE_ID or "ยืนยัน" in r.name:
                    role = r
                    role_id = r.id
                    break

        member = interaction.user
        if not isinstance(member, discord.Member):
            try:
                member = await guild.fetch_member(interaction.user.id)
            except Exception:
                pass

        # Check if already verified
        if role and role in getattr(member, "roles", []):
            await interaction.response.send_message(
                f"You are already verified with {role.mention}",
                ephemeral=True
            )
            return

        # Generate fresh Captcha challenge
        code, png_bytes = verify_manager.create_challenge(
            user_id=interaction.user.id,
            guild_id=guild.id,
            role_id=role_id
        )

        embed = discord.Embed(
            title="Captcha Challenge",
            description="Type the characters shown in the image. This challenge expires in 5 minutes.",
            color=COLOR_VERIFY_RED
        )
        embed.set_image(url="attachment://captcha.png")

        captcha_file = discord.File(io.BytesIO(png_bytes), filename="captcha.png")
        view = CaptchaChallengeView(user_id=interaction.user.id, role_id=role_id)

        await interaction.response.send_message(
            embed=embed,
            file=captcha_file,
            view=view,
            ephemeral=True
        )


# ─────────────────────────────────────────────────────────────
# Verification Cog & /setpanel Slash Commands
# ─────────────────────────────────────────────────────────────
class VerificationCog(commands.Cog):
    """Verification System — Complete FlowAuth Replacement."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Slash command group: /setpanel
    setpanel_group = app_commands.Group(
        name="setpanel",
        description="ติดตั้งและจัดการแผงควบคุมระบบ (Verification, Bypass, etc.)",
        default_permissions=discord.Permissions(administrator=True)
    )

    @setpanel_group.command(name="verify", description="🛡️ ติดตั้งแผงยืนยันตัวตน (Captcha Verification Panel แบบ FlowAuth)")
    @app_commands.describe(
        role="ยศที่จะมอบให้ผู้ใช้เมื่อยืนยันตัวตนผ่าน (ถ้าไม่ระบุ = ตรวจหาอัตโนมัติ)",
        channel="ช่องที่จะส่งแผงยืนยันตัวตน (ถ้าไม่ระบุ = ช่องปัจจุบัน)"
    )
    async def cmd_setpanel_verify(
        self,
        interaction: discord.Interaction,
        role: Optional[discord.Role] = None,
        channel: Optional[discord.TextChannel] = None
    ):
        target_channel = channel or interaction.channel
        guild = interaction.guild

        if not guild:
            await interaction.response.send_message("❌ คำสั่งนี้ใช้ได้เฉพาะในเซิร์ฟเวอร์", ephemeral=True)
            return

        # Resolve role
        target_role = role
        if not target_role:
            target_role = guild.get_role(DEFAULT_VERIFIED_ROLE_ID)
            if not target_role:
                for r in guild.roles:
                    if "ยืนยัน" in r.name:
                        target_role = r
                        break

        if not target_role:
            await interaction.response.send_message(
                "❌ **ไม่พบยศยืนยันตัวตน!** กรุณาระบุพารามิเตอร์ `role` เช่น `/setpanel verify role:@ยืนยันตัวตนแล้ว`",
                ephemeral=True
            )
            return

        # Check permissions
        bot_member = guild.me
        if not bot_member.guild_permissions.manage_roles and not bot_member.guild_permissions.administrator:
            await interaction.response.send_message(
                "⚠️ **คำเตือน:** บอทไม่มีสิทธิ์ `Manage Roles` หรือ `Administrator` ในเซิร์ฟเวอร์นี้ กรุณาให้ยศที่มีสิทธิ์แก่บอทก่อน",
                ephemeral=True
            )
            return

        if bot_member.top_role.position <= target_role.position and not bot_member.guild_permissions.administrator:
            await interaction.response.send_message(
                f"⚠️ **คำเตือน:** ยศของบอท ({bot_member.top_role.name}) อยู่ต่ำกว่าหรือเท่ากับยศ {target_role.mention}\n"
                "กรุณาลากยศของบอทให้อยู่สูงกว่าใน Server Settings > Roles",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        # Build exact clone embed matching FlowAuth
        panel_embed = discord.Embed(
            title="PAYOMBØYZ Verification",
            description=(
                "โปรดกดปุ่ม \"ยืนยันตัวตน\" ด้านล่าง และนำเลข Captcha ไปใส่ในช่อง เพื่อยืนยันตัวตน ว่าคนนะไม่ใช่หุ่นยนต์ ที่จะทนตากแดดทั้งวัน\n\n"
                f"Verified role: {target_role.mention} ˖"
            ),
            color=COLOR_VERIFY_RED
        )

        view = VerifyPanelView()

        try:
            msg = await target_channel.send(embed=panel_embed, view=view)
            
            # Save configuration
            guild_config.set_verify_role(guild.id, target_role.id)
            guild_config.set_verify_channel(guild.id, target_channel.id)
            guild_config.set_verify_panel_message(guild.id, msg.id)

            await interaction.followup.send(
                f"✅ **ติดตั้ง Verification Panel เรียบร้อยแล้ว!**\n"
                f"• **ช่อง:** {target_channel.mention}\n"
                f"• **ยศที่จะได้รับ:** {target_role.mention} (`{target_role.id}`)\n"
                f"• **Message ID:** `{msg.id}`\n\n"
                "ระบบพร้อมทำงาน 100% แทนที่ FlowAuth ได้ทันที!",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.followup.send(
                f"❌ **บอทไม่มีสิทธิ์ส่งข้อความในช่อง {target_channel.mention}**\nโปรดตรวจสอบสิทธิ์ Send Messages และ Embed Links ของบอทในช่องดังกล่าว",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ เกิดข้อผิดพลาดในการติดตั้ง Panel: `{e}`",
                ephemeral=True
            )

    @setpanel_group.command(name="bypass", description="🔓 ติดตั้งแผง Bypass Link (Bypass Ad-Link Panel)")
    @app_commands.describe(
        result_channel="ช่องที่จะแสดงผล Log การ Bypass (ถ้าไม่ระบุ = ช่องเดียวกัน)",
        channel="ช่องที่จะส่งแผง Bypass (ถ้าไม่ระบุ = ช่องปัจจุบัน)"
    )
    async def cmd_setpanel_bypass(
        self,
        interaction: discord.Interaction,
        result_channel: Optional[discord.TextChannel] = None,
        channel: Optional[discord.TextChannel] = None
    ):
        target_channel = channel or interaction.channel
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("❌ คำสั่งนี้ใช้ได้เฉพาะในเซิร์ฟเวอร์", ephemeral=True)
            return

        from cogs.panel import PanelView
        from config import COLOR_PRIMARY

        log_ch = result_channel or target_channel
        guild_config.set_result_channel(guild.id, log_ch.id)
        guild_config.set_bypass_channel(guild.id, target_channel.id)

        panel_embed = discord.Embed(
            title="🔓 Bypass Ad-Link Panel",
            description=(
                "กด **Bypass Link** เพื่อเปิดหน้าต่างใส่ลิงค์\n"
                "ระบบจะประมวลผลและส่งลิงค์ตรงกลับมาให้คุณ **แบบส่วนตัว** (เห็นแค่คุณคนเดียว)\n\n"
                "**รองรับ:**\n"
                "> ⚡ Linkvertise  •  💎 LootLabs  •  💼 Work.ink\n"
                "> 🔓 Rekonise  •  🔒 Lockr  •  🚀 Boost.ink\n"
                "> 🪐 Platoboost (Delta)  •  ▶️ Sub2Unlock  •  📁 MediaFire\n\n"
                f"📝 ผลลัพธ์การ Bypass จะถูก Log ใน {log_ch.mention}"
            ),
            color=COLOR_PRIMARY
        )
        panel_embed.set_footer(text="Self-hosted Bypass Engine • No external API dependency")

        try:
            msg = await target_channel.send(embed=panel_embed, view=PanelView())
            guild_config.set_panel_message(guild.id, msg.id)
            await interaction.response.send_message(
                f"✅ **ติดตั้ง Bypass Panel ในช่อง {target_channel.mention} เรียบร้อยแล้ว!**\nLog Channel: {log_ch.mention}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ เกิดข้อผิดพลาด: `{e}`", ephemeral=True)

    @app_commands.command(name="verify", description="🛡️ ยืนยันตัวตนสมาชิก (รับยศผู้ใช้ยืนยันแล้ว)")
    async def cmd_direct_verify(self, interaction: discord.Interaction):
        """Direct command allowing users to trigger verification without panel."""
        view = VerifyPanelView()
        # Trigger the same logic as pressing the panel button
        await view.btn_verify.callback(interaction)

    @app_commands.command(name="welcome_test", description="👑 ทดสอบส่งการ์ดต้อนรับ HighSpec เข้าห้อง Welcome (เฉพาะแอดมิน)")
    @app_commands.describe(member="สมาชิกที่ต้องการทดสอบการ์ดต้อนรับ (ไม่ระบุ = ตัวเอง)")
    @app_commands.default_permissions(administrator=True)
    async def cmd_welcome_test(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        target_member = member or interaction.user
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("❌ คำสั่งนี้ใช้ได้เฉพาะในเซิร์ฟเวอร์", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        role_id = guild_config.get_verify_role(guild.id) or DEFAULT_VERIFIED_ROLE_ID
        role = guild.get_role(role_id)
        if not role:
            for r in guild.roles:
                if "ยืนยัน" in r.name:
                    role = r
                    break
        if not role:
            role = guild.default_role

        log_ch_id = guild_config.get_verify_log_channel(guild.id) or 1555390535215358073
        log_ch = guild.get_channel(log_ch_id)
        if not log_ch and self.bot:
            try:
                log_ch = await self.bot.fetch_channel(log_ch_id)
            except Exception:
                log_ch = None

        if not log_ch:
            await interaction.followup.send(f"❌ ไม่พบห้อง Welcome (ID: {log_ch_id})", ephemeral=True)
            return

        try:
            avatar_bytes = None
            try:
                avatar_bytes = await target_member.display_avatar.with_format("png").with_size(256).read()
            except Exception:
                try:
                    avatar_bytes = await target_member.display_avatar.read()
                except Exception:
                    avatar_bytes = None

            card_buf = await asyncio.to_thread(
                generate_verification_card_sync,
                user_name=target_member.display_name,
                user_handle=target_member.name,
                user_id=str(target_member.id),
                role_name=role.name,
                guild_name=guild.name,
                member_count=getattr(guild, "member_count", 0),
                avatar_bytes=avatar_bytes
            )

            welcome_content = f"<a:pbg_wing_l:1562553182859563150> ยินดีต้อนรับคุณ {target_member.mention} เข้าสู่เซิร์ฟเวอร์ **{guild.name}** ! <a:pbg_wing_r:1562553185325940748>"
            
            log_embed = discord.Embed(
                title=f"» • 𝐖𝐄𝐋𝐂𝐎𝐌𝐄 {target_member.display_name.upper()} • «",
                color=0xF1C40F
            )
            log_embed.set_author(
                name=f"{target_member.name} [{target_member.id}]",
                icon_url=target_member.display_avatar.url
            )
            log_embed.set_thumbnail(url=target_member.display_avatar.url)

            now_ts = int(time.time())
            m_count = getattr(guild, "member_count", 0)
            log_embed.description = (
                f"╔════════════════════════════════════════════╗\n"
                f"  • ยินดีต้อนรับ ➔ {target_member.mention} (`{target_member.name}`)\n"
                f"  • ยศที่ได้รับ ➔ {role.mention}\n"
                f"  • สมาชิกคนที่ ➔ `#{m_count:,}`\n"
                f"  • เวลาที่ยืนยัน ➔ <t:{now_ts}:F> (<t:{now_ts}:R>)\n"
                f"╚════════════════════════════════════════════╝\n\n"
                f"> 👑 **PAYOMBØYZ SENTINEL VERIFICATION PASSED**\n"
                f"> เข้าสู่ศูนย์รวม Script Hub, Auto Quest & เครื่องมือระดับพรีเมียม"
            )
            log_embed.set_image(url="attachment://welcome_banner.png")
            guild_icon_url = guild.icon.url if guild.icon else None
            log_embed.set_footer(text=f"PAYOMBOYZ X WELCOME • {guild.name}", icon_url=guild_icon_url)

            card_file = discord.File(fp=card_buf, filename="welcome_banner.png")
            await log_ch.send(content=welcome_content, file=card_file, embed=log_embed)
            await interaction.followup.send(f"✅ **ส่งการ์ดต้อนรับ HighSpec เข้าห้อง {log_ch.mention} เรียบร้อยแล้ว!**", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ เกิดข้อผิดพลาด: `{e}`", ephemeral=True)


async def setup(bot: commands.Bot):
    # Register persistent views so buttons stay active after reboot
    bot.add_view(VerifyPanelView())
    try:
        from utils.token_finder_panel import FindTokenPanelView
        bot.add_view(FindTokenPanelView())
    except Exception as e:
        print(f"[-] Failed to register FindTokenPanelView in BotBypass: {e}")
    await bot.add_cog(VerificationCog(bot))

