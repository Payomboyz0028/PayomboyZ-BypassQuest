"""
================================================================================
  PAYOMBOYZ AUTO QUEST COG
  Integrates Discord Quests v10 Protocol & API Server into KeyBypassBot
  Source Engine: d:\\Deobfuscate\\DiscordAutoquest2
================================================================================
"""

import os
import sys
import asyncio
import secrets
from typing import Optional, Dict, Any, List

import discord
from discord.ext import commands
from discord import app_commands, ui

# Point sys.path strictly to DiscordAutoquest2 (local or absolute)
_local_aq2 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "DiscordAutoquest2")
AUTOQUEST_DIR = _local_aq2 if os.path.exists(_local_aq2) else r"d:\Deobfuscate\DiscordAutoquest2"
if AUTOQUEST_DIR not in sys.path:
    sys.path.insert(0, AUTOQUEST_DIR)

from payomboyz_autoquest import (
    state,
    worker_pool,
    DiscordQuestV10Handler,
    VisualEmbedEngine,
    UserQuestJob,
    AutoQuestSubmissionModal,
    PanelEditModal,
    QuestPremiumModal,
    PersistentQuestPanelView,
    build_panel_embed,
    send_quest_v2_panel,
    start_api_server,
    API_PORT,
    API_HOST
)

# ==============================================================================
# CORE WORKER ROUTINES (Clean coroutine functions called by commands)
# ==============================================================================
async def do_panel(interaction: discord.Interaction, target_channel: Optional[discord.TextChannel] = None):
    if not interaction.guild:
        if not interaction.response.is_done():
            return await interaction.response.send_message("❌ ใช้งานได้เฉพาะในเซิร์ฟเวอร์", ephemeral=True)
        return
    if not interaction.response.is_done():
        try:
            await interaction.response.defer(ephemeral=True)
        except Exception:
            pass
    ch = target_channel or interaction.channel
    bot_token = interaction.client.http.token
    ok, res = await send_quest_v2_panel(ch.id, bot_token, interaction.guild_id)
    if not ok:
        embed, files = build_panel_embed(interaction.guild_id)
        view = PersistentQuestPanelView(interaction.guild_id)
        await ch.send(embed=embed, files=files, view=view)
    try:
        await interaction.followup.send(f"✅ ส่งแผงควบคุมทำเควส (Components V2 Native Container) สำเร็จ (ห้อง {ch.mention})", ephemeral=True)
    except Exception:
        pass

async def do_editpanel(interaction: discord.Interaction):
    if not interaction.guild:
        return await interaction.response.send_message("❌ ใช้งานได้เฉพาะในเซิร์ฟเวอร์", ephemeral=True)
    cfg = state.get_panel(interaction.guild_id)
    modal = PanelEditModal(cfg)
    await interaction.response.send_modal(modal)

async def do_setchannels(interaction: discord.Interaction, result_channel: discord.TextChannel, status_channel: Optional[discord.TextChannel] = None):
    gid = interaction.guild_id
    current_cfg = state.get_guild(gid) if state else {}
    st_ch = status_channel or (interaction.guild.get_channel(current_cfg.get("status_channel_id", 0)) if interaction.guild else None)
    st_ch_id = st_ch.id if st_ch else (current_cfg.get("status_channel_id") or 1560942929063972944)

    state.set_guild_channels(gid, st_ch_id, result_channel.id)

    # Sync also to alternate json paths
    try:
        import json
        alt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "payomboyz_quest_data.json")
        if os.path.exists(alt_path):
            with open(alt_path, "r", encoding="utf-8") as f:
                d = json.load(f)
            if "guilds" not in d: d["guilds"] = {}
            d["guilds"][str(gid)] = {"status_channel_id": st_ch_id, "result_channel_id": result_channel.id}
            with open(alt_path, "w", encoding="utf-8") as f:
                json.dump(d, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    msg = (
        f"✅ **ตั้งค่าห้อง Auto Quest สำเร็จเรียบร้อยแล้ว!**\n"
        f"• 📬 **ห้องผลลัพธ์เควส (Completion Logs):** {result_channel.mention}\n"
        f"• 📡 **ห้องสถานะสด (Live Progress):** <#{st_ch_id}>\n\n"
        f"*(บอทจะส่งผลลัพธ์การทำเควสและรหัสรางวัลทั้งหมดไปยังห้อง {result_channel.mention} เท่านั้น หน้า Panel จะไม่รกอีกต่อไป)*"
    )
    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)

async def do_toggle(interaction: discord.Interaction, is_open: bool):
    state.update_panel(interaction.guild_id, is_open=is_open)
    st = "🟢 **เปิดระบบแล้ว**" if is_open else "🔴 **ปิดระบบชั่วคราวแล้ว**"
    await interaction.response.send_message(f"✅ บันทึกสถานะ: {st}\n(ส่ง `/panel` ใหม่เพื่อให้ปุ่มอัปเดตสถานะ)", ephemeral=True)

async def do_setpro(interaction: discord.Interaction, role: discord.Role):
    state.set_pro_role(interaction.guild_id, role.id)
    await interaction.response.send_message(f"✅ ตั้งค่ายศ Pro Quest เป็น: {role.mention}", ephemeral=True)

async def do_keygen(interaction: discord.Interaction, amount: int = 1, days: int = 30):
    amount = max(1, min(amount, 50))
    new_keys = []
    for _ in range(amount):
        new_key = f"PAYOMBOYZ-VIP-{secrets.token_hex(3).upper()}-{secrets.token_hex(3).upper()}"
        state.redeem_keys.add(new_key)
        new_keys.append(new_key)
    state.save()
    if len(new_keys) == 1:
        msg = (
            f"🔑 **สร้างคีย์ VIP Pro Quest สำเร็จ!**\n"
            f"`{new_keys[0]}`\n"
            f"⏱️ ระยะเวลา: **{days} วัน**\n"
            f"ผู้ใช้สามารถนำไปใช้ด้วยคำสั่ง `/redeem` หรือกดปุ่ม 💎 **VIP PREMIUM**"
        )
    else:
        keys_list = "\n".join(f"{i+1}. `{k}`" for i, k in enumerate(new_keys))
        msg = (
            f"🔑 **สร้างคีย์ VIP Pro Quest สำเร็จ {len(new_keys)} คีย์!**\n"
            f"⏱️ ระยะเวลา: **{days} วัน** ต่อคีย์\n\n"
            f"{keys_list}\n\n"
            f"ผู้ใช้สามารถนำไปใช้ด้วยคำสั่ง `/redeem` หรือกดปุ่ม 💎 **VIP PREMIUM**"
        )
    await interaction.response.send_message(msg, ephemeral=True)

async def do_redeem(interaction: discord.Interaction, key: str):
    success = state.redeem_key(interaction.user.id, key)
    if success:
        await interaction.response.send_message("🎉 **แลกรับสิทธิ์ Pro Quest สำเร็จแล้ว!** ใช้งานได้ไม่จำกัดโควตา 30 วัน", ephemeral=True)
    else:
        await interaction.response.send_message("❌ **คีย์ไม่ถูกต้อง หรือถูกใช้งานไปแล้ว!**", ephemeral=True)

async def do_reset(interaction: discord.Interaction):
    state.reset_all_quotas()
    await interaction.response.send_message("✅ **รีเซ็ตโควต้าฟรีของสมาชิกทุกคนเรียบร้อยแล้ว!** ทุกคนสามารถทำเควสใหม่ได้ทันที", ephemeral=True)

async def do_setrole_quest(interaction: discord.Interaction, user: discord.Member, days: int = 30, role: Optional[discord.Role] = None):
    if not interaction.guild:
        return await interaction.response.send_message("❌ ใช้งานได้เฉพาะในเซิร์ฟเวอร์", ephemeral=True)
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


# ==============================================================================
# COMMAND GROUP: /quest (All Admin & User Operations in One Clean Namespace)
# ==============================================================================
quest_group = app_commands.Group(name="quest", description="💎 ระบบจัดการ PayomboyZ Auto Quest (Discord Quests v10)")

@quest_group.command(name="panel", description="ส่งแผงควบคุมทำเควส PayomboyZ Auto Quest (รองรับระบุห้อง)")
@app_commands.describe(channel="ห้องที่ต้องการให้ส่งแผงควบคุม (เว้นว่างไว้หากต้องการส่งในห้องปัจจุบัน)")
@app_commands.default_permissions(administrator=True)
async def g_cmd_panel(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
    await do_panel(interaction, target_channel=channel)

@quest_group.command(name="edit", description="แก้ไขข้อความ รูปภาพ สี และปุ่มของ Panel แบบ Real-Time")
@app_commands.default_permissions(administrator=True)
async def g_cmd_edit(interaction: discord.Interaction):
    await do_editpanel(interaction)

@quest_group.command(name="channels", description="ตั้งค่าห้องผลลัพธ์เควส และห้องสถานะสด")
@app_commands.describe(
    result_channel="ห้องแจ้งเตือนผลลัพธ์เควสเมื่อทำเสร็จสิ้น (เช่น #quest-complete)",
    status_channel="ห้องแสดงสถานะการทำเควสสด (เช่น #wait-questing - ไม่ระบุจะใช้ห้องเดิม)"
)
@app_commands.default_permissions(administrator=True)
async def g_cmd_channels(interaction: discord.Interaction, result_channel: discord.TextChannel, status_channel: Optional[discord.TextChannel] = None):
    await do_setchannels(interaction, result_channel, status_channel)

@quest_group.command(name="channel", description="ตั้งค่าห้องแจ้งผลลัพธ์เควส (และห้องสถานะสด)")
@app_commands.describe(
    result_channel="ห้องแจ้งเตือนผลลัพธ์เควสเมื่อทำเสร็จสิ้น (เช่น #quest-complete)",
    status_channel="ห้องแสดงสถานะการทำเควสสด (เช่น #wait-questing - ไม่ระบุจะใช้ห้องเดิม)"
)
@app_commands.default_permissions(administrator=True)
async def g_cmd_channel(interaction: discord.Interaction, result_channel: discord.TextChannel, status_channel: Optional[discord.TextChannel] = None):
    await do_setchannels(interaction, result_channel, status_channel)

@quest_group.command(name="toggle", description="เปิด หรือ ปิดระบบทำเควสชั่วคราว (Maintenance Mode)")
@app_commands.describe(is_open="เลือก True เพื่อเปิดระบบ, False เพื่อปิดระบบชั่วคราว")
@app_commands.default_permissions(administrator=True)
async def g_cmd_toggle(interaction: discord.Interaction, is_open: bool):
    await do_toggle(interaction, is_open)

@quest_group.command(name="pro", description="ตั้งค่ายศ Pro Quest ประจำเซิร์ฟเวอร์ (ไม่จำกัดโควตา)")
@app_commands.describe(role="ยศที่ได้รับสิทธิ์ Pro Quest")
@app_commands.default_permissions(administrator=True)
async def g_cmd_pro(interaction: discord.Interaction, role: discord.Role):
    await do_setpro(interaction, role)

@quest_group.command(name="setrole", description="กำหนดสิทธิ์ หรือมอบวันใช้งาน Pro Quest ให้กับสมาชิก")
@app_commands.describe(
    user="สมาชิกที่ต้องการจัดการสิทธิ์",
    days="จำนวนวันที่ต้องการมอบ (ใส่ 0 เพื่อยกเลิกสิทธิ์)",
    role="ยศที่ต้องการมอบให้เพิ่มเติม (ไม่จำเป็นต้องระบุ)"
)
@app_commands.default_permissions(administrator=True)
async def g_cmd_setrole(
    interaction: discord.Interaction,
    user: discord.Member,
    days: int = 30,
    role: Optional[discord.Role] = None
):
    await do_setrole_quest(interaction, user, days, role)

@quest_group.command(name="reset", description="รีเซ็ตโควต้าทำเควสฟรีของสมาชิกทุกคนในเซิร์ฟเวอร์")
@app_commands.default_permissions(administrator=True)
async def g_cmd_reset(interaction: discord.Interaction):
    await do_reset(interaction)

@quest_group.command(name="keygen", description="สร้างคีย์ VIP Pro Quest สำหรับนำไปแจกหรือจำหน่าย (รองรับสร้างหลายคีย์)")
@app_commands.describe(
    amount="จำนวนคีย์ที่ต้องการสร้าง (1 - 50 คีย์)",
    days="จำนวนวันใช้งาน (ค่าเริ่มต้น: 30 วัน)"
)
@app_commands.default_permissions(administrator=True)
async def g_cmd_keygen(interaction: discord.Interaction, amount: int = 1, days: int = 30):
    await do_keygen(interaction, amount=amount, days=days)

@quest_group.command(name="redeem", description="แลกรับสิทธิ์ Pro Quest ด้วยคีย์ VIP")
@app_commands.describe(key="รหัสคีย์ VIP")
async def g_cmd_redeem(interaction: discord.Interaction, key: str):
    await do_redeem(interaction, key)


# ==============================================================================
# COG CLASS (Clean Canonical Shortcuts)
# ==============================================================================
class AutoQuestCog(commands.Cog, name="AutoQuest"):
    """💎 ระบบ PayomboyZ Discord Auto Quest (Discord Quests v10 Protocol)"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # 1. /panel (Quick Top-Level Shortcut for Admins)
    @app_commands.command(name="panel", description="ส่งแผงควบคุมทำเควส PayomboyZ Auto Quest (Editable Panel)")
    @app_commands.describe(channel="ห้องที่ต้องการให้ส่งแผงควบคุม (เว้นว่างไว้หากต้องการส่งในห้องปัจจุบัน)")
    @app_commands.default_permissions(administrator=True)
    async def slash_panel(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        await do_panel(interaction, target_channel=channel)

    # 2. /keygen (Quick Top-Level Shortcut for Admins)
    @app_commands.command(name="keygen", description="สร้างคีย์ VIP Pro Quest (รองรับสร้างทีละหลายคีย์)")
    @app_commands.describe(
        amount="จำนวนคีย์ที่ต้องการสร้าง (1 - 50 คีย์)",
        days="จำนวนวันใช้งาน (ค่าเริ่มต้น: 30 วัน)"
    )
    @app_commands.default_permissions(administrator=True)
    async def slash_keygen(self, interaction: discord.Interaction, amount: int = 1, days: int = 30):
        await do_keygen(interaction, amount=amount, days=days)

    # 3. /redeem (Quick Top-Level Shortcut for Members)
    @app_commands.command(name="redeem", description="แลกรับสิทธิ์ Pro Quest ด้วยคีย์ VIP")
    @app_commands.describe(key="รหัสคีย์ VIP")
    async def slash_redeem(self, interaction: discord.Interaction, key: str):
        await do_redeem(interaction, key)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
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
# COG SETUP
# ==============================================================================
async def setup(bot: commands.Bot):
    # Set bot reference in payomboyz_autoquest module for API handlers
    try:
        import payomboyz_autoquest
        payomboyz_autoquest.bot = bot
    except Exception:
        pass

    # 1. Start Quest Worker Pool
    try:
        if not getattr(worker_pool, "_is_running", False):
            worker_pool.start()
            worker_pool._is_running = True
            print("  [OK] Started PayomboyZ AutoQuest Worker Pool (DiscordAutoquest2)")
    except Exception as e:
        print(f"  [WARN] AutoQuest Worker Pool: {e}")

    # 2. Start Commercial REST API Server on Port 5050
    try:
        asyncio.create_task(start_api_server())
        print(f"  [OK] Launched AutoQuest REST API on port {API_PORT}")
    except Exception as e:
        print(f"  [WARN] AutoQuest API Server: {e}")

    # 3. Add command group /quest
    try:
        existing_names = [cmd.name for cmd in bot.tree.get_commands()]
        if "quest" not in existing_names:
            bot.tree.add_command(quest_group)
    except Exception as e:
        print(f"  [WARN] quest_group register: {e}")

    # 4. Register Persistent Views
    for g in bot.guilds:
        try:
            bot.add_view(PersistentQuestPanelView(g.id))
        except Exception:
            pass

    await bot.add_cog(AutoQuestCog(bot))
    print("  [OK] Loaded AutoQuest Cog from DiscordAutoquest2 into Bot successfully")
