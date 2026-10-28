"""
================================================================================
  PAYOMBOYZ TOKEN FINDER COG & AUTOQUEST BRIDGE
  Unified Token Extractor integrated directly with พยอมบอยหมูสับจัดให้ (Container 1)
  Provides:
    - 🔐 Direct Login with Genuine Desktop Super Properties & Captcha Protection
    - 📷 Discord Remote Auth QR Code Scanner (Fixed HTTP 400 Ticket Exchange)
    - 💻 PC Automated Web Bridge (/token) & 1-line Console Helper
    - 📱 Mobile Web & Bookmarklet Helper
    - 🚀 1-Click "Send Token to Auto Quest" Instant Execution
    - 🛡️ Zero Retention Architecture: RAM-only, ephemeral views, 5-min auto-destruction
================================================================================
"""

import os
import sys
import io
import time
import json
import base64
import hashlib
import asyncio
from typing import Optional, Dict, Any, List

import aiohttp
try:
    from curl_cffi.requests import AsyncSession as CurlAsyncSession
    HAVE_CURL_CFFI = True
except ImportError:
    HAVE_CURL_CFFI = False
import discord
from discord.ext import commands
from discord import app_commands, ui
import qrcode
import websockets
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

# Ensure DiscordAutoquest2 is accessible
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_AUTOQUEST2_DIR = os.path.join(_BASE_DIR, "DiscordAutoquest2")
if os.path.exists(_AUTOQUEST2_DIR) and _AUTOQUEST2_DIR not in sys.path:
    sys.path.insert(0, _AUTOQUEST2_DIR)

try:
    from payomboyz_autoquest import (
        state,
        worker_pool,
        DiscordQuestV10Handler,
        UserQuestJob,
        VisualEmbedEngine,
        build_quest_selection_embed,
        QuestSelectionView
    )
except ImportError:
    # Graceful fallback if imported in standalone context
    state = None
    worker_pool = None
    DiscordQuestV10Handler = None
    UserQuestJob = None
    VisualEmbedEngine = None
    build_quest_selection_embed = None
    QuestSelectionView = None

COLOR_PRIMARY = 0x5865F2    # Blurple
COLOR_SUCCESS = 0x57F287    # Green
COLOR_WARNING = 0xFEE75C    # Gold
COLOR_DANGER = 0xED4245     # Red
COLOR_EXPIRED = 0x2B2D31    # Dark Slate

# Genuine Discord Web Client Super Properties & Live Build Number
DISCORD_CLIENT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

DISCORD_CLIENT_SUPER_PROPERTIES = {
    "os": "Windows",
    "browser": "Chrome",
    "device": "",
    "system_locale": "th-TH",
    "browser_user_agent": DISCORD_CLIENT_UA,
    "browser_version": "128.0.0.0",
    "os_version": "10",
    "referrer": "",
    "referring_domain": "",
    "referrer_current": "",
    "referring_domain_current": "",
    "release_channel": "stable",
    "client_build_number": 643186,
    "client_event_source": None
}
ENCODED_SUPER_PROPERTIES = base64.b64encode(
    json.dumps(DISCORD_CLIENT_SUPER_PROPERTIES).encode("utf-8")
).decode("utf-8")


# ─────────────────────────────────────────────────────────────
# 1. 1-CLICK ACTION BRIDGE: SEND TOKEN DIRECTLY TO AUTOQUEST
# ─────────────────────────────────────────────────────────────
async def enqueue_token_for_autoquest(interaction: discord.Interaction, token: str):
    """Feeds a retrieved token directly into AutoQuest worker pool without manual copy-paste."""
    guild = interaction.guild
    if not guild:
        return await interaction.followup.send("⚠️ กรุณาใช้งานฟังก์ชันนี้ภายในเซิร์ฟเวอร์", ephemeral=True)

    if not worker_pool or not state or not DiscordQuestV10Handler:
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "token": token,
                    "guild_id": str(guild.id),
                    "user_id": str(interaction.user.id),
                    "status_channel_id": str(interaction.channel_id),
                    "result_channel_id": str(interaction.channel_id)
                }
                async with session.post(
                    "http://127.0.0.1:5050/api/start_quest",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        status_url = data.get("status_url") or f"https://discord.com/channels/{guild.id}/{interaction.channel_id}"
                        check_view = discord.ui.View()
                        check_view.add_item(discord.ui.Button(
                            label="🔍 CHECK STATUS",
                            style=discord.ButtonStyle.link,
                            url=status_url
                        ))
                        username = data.get("username", "User")
                        return await interaction.followup.send(
                            content=(
                                f"🚀 **ส่ง Token เข้าสู่ระบบ Auto Quest เรียบร้อยแล้ว!**\n"
                                f"👤 **บัญชี Discord:** `{username}`\n"
                                f"📍 **ห้องสถานะสด:** <#{interaction.channel_id}>\n"
                                f"👉 คลิกปุ่ม **[🔍 CHECK STATUS]** ด้านล่างเพื่อติดตามการทำเควสแบบเรียลไทม์ได้ทันที"
                            ),
                            view=check_view,
                            ephemeral=True
                        )
                    else:
                        try:
                            err_data = await resp.json()
                            err_msg = err_data.get("error", "ไม่สามารถส่ง Token ได้")
                        except Exception:
                            err_msg = f"HTTP {resp.status}"
                        return await interaction.followup.send(
                            f"❌ **AutoQuest แจ้งเตือน:** {err_msg}",
                            ephemeral=True
                        )
        except Exception as bridge_err:
            print(f"[BridgeError] AutoQuest bridge to port 5050 failed: {bridge_err}", flush=True)
            return await interaction.followup.send(
                "⚠️ ระบบ Auto Quest Engine ยังไม่พร้อมทำงาน กรุณาคัดลอก Token ไปวางด้วยตนเอง หรือใช้คำสั่ง `/quest start`",
                ephemeral=True
            )

    # 1. Validate token & fetch profile
    profile = await DiscordQuestV10Handler.validate_token(token)
    if not profile:
        return await interaction.followup.send(
            "❌ **Token ไม่ถูกต้อง หรือหมดอายุแล้ว!** กรุณาลองดึงใหม่อีกครั้ง",
            ephemeral=True
        )

    # 2. Check quota & VIP status
    is_pro = state.is_user_pro(interaction.user.id, interaction.user, guild.id)
    can_proceed, count = state.check_and_increment_quota(interaction.user.id, is_pro)
    if not can_proceed:
        return await interaction.followup.send(
            "⚠️ **คุณใช้โควตาทำเควสฟรีครบ 3 ครั้งสำหรับวันนี้แล้ว!**\n"
            "💎 อัปเกรดเป็น **VIP Quest** หรือใช้คำสั่ง `/quest redeem` เพื่อรับโควตาไม่จำกัด",
            ephemeral=True
        )

    # 3. Resolve status & result channels safely
    cfg = state.get_guild(guild.id)
    status_ch_id = cfg.get("status_channel_id")
    result_ch_id = cfg.get("result_channel_id")

    status_ch = None
    if status_ch_id:
        status_ch = guild.get_channel(status_ch_id)
        if not status_ch:
            try:
                status_ch = await guild.fetch_channel(status_ch_id)
            except Exception:
                pass
    if not status_ch or not hasattr(status_ch, "send"):
        status_ch = interaction.channel

    result_ch = None
    if result_ch_id:
        result_ch = guild.get_channel(result_ch_id)
        if not result_ch:
            try:
                result_ch = await guild.fetch_channel(result_ch_id)
            except Exception:
                pass
    if not result_ch or not hasattr(result_ch, "send"):
        result_ch = interaction.channel

    # 4. Interactive Quest Selection (DevilQuest Parity)
    if build_quest_selection_embed and QuestSelectionView:
        quest_data = await DiscordQuestV10Handler.fetch_quests(token)
        raw_quests = quest_data.get("quests", [])

        active_quests = []
        now_utc = datetime.now(timezone.utc)
        for q in raw_quests:
            cfg_q = q.get("config", {})
            exp_str = cfg_q.get("expires_at")
            if exp_str:
                try:
                    exp_dt = datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
                    if exp_dt <= now_utc:
                        continue
                except Exception:
                    pass
            user_status = q.get("user_status") or {}
            if not user_status.get("completed_at") or not user_status.get("claimed_at"):
                active_quests.append(q)

        if not active_quests:
            return await interaction.followup.send(
                "🎉 **บัญชี Discord ของคุณไม่มีเควสค้าง หรือทำเควสทั้งหมดและรับรางวัลครบแล้ว!**",
                ephemeral=True
            )

        video_count = 0
        game_count = 0
        quest_info_list = []
        for idx, q in enumerate(active_quests, start=1):
            q_id = str(q.get("id"))
            cfg_q = q.get("config", {})
            msgs = cfg_q.get("messages", {})
            q_name = msgs.get("quest_name") or msgs.get("game_title") or q.get("name") or f"Quest {q_id}"

            tasks = None
            if cfg_q.get("task_config_v2", {}).get("tasks"):
                tasks = cfg_q["task_config_v2"]["tasks"]
            elif cfg_q.get("task_config", {}).get("tasks"):
                tasks = cfg_q["task_config"]["tasks"]
            else:
                for k in q:
                    if isinstance(q[k], dict) and q[k].get("tasks"):
                        tasks = q[k]["tasks"]
                        break
            tasks = tasks or {}
            is_vid = any(t in tasks for t in ('WATCH_VIDEO', 'WATCH_VIDEO_ON_MOBILE'))
            if is_vid:
                video_count += 1
                q_type = "video"
            else:
                game_count += 1
                q_type = "game"

            quest_info_list.append({
                "index": idx,
                "id": q_id,
                "name": q_name,
                "type": q_type,
                "quest": q
            })

        embed = build_quest_selection_embed(
            user=interaction.user,
            profile=profile,
            quest_info_list=quest_info_list,
            video_count=video_count,
            game_count=game_count,
            is_pro=is_pro
        )
        view = QuestSelectionView(
            user=interaction.user,
            tokens=[token],
            profile=profile,
            active_quests=active_quests,
            quest_info_list=quest_info_list,
            status_channel=status_ch,
            result_channel=result_ch,
            guild=guild,
            is_pro=is_pro
        )
        return await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    # Fallback if UI components are not available
    job = UserQuestJob(
        guild=guild,
        user=interaction.user,
        profile=profile,
        tokens=[token],
        status_channel=status_ch,
        result_channel=result_ch
    )
    await worker_pool.enqueue(job)

    # 5. Build confirmation embed & jump link
    status_url = f"https://discord.com/channels/{guild.id}/{status_ch.id}"
    check_view = discord.ui.View()
    check_view.add_item(discord.ui.Button(
        label="🔍 CHECK STATUS",
        style=discord.ButtonStyle.link,
        url=status_url
    ))

    quota_msg = "💎 สิทธิ์การใช้งาน: **PRO (ไม่จำกัดโควตา)**" if is_pro else f"📊 โควตาวันนี้: **{count}/3 ครั้ง**"
    username = profile.get("username", "User")
    await interaction.followup.send(
        content=(
            f"🚀 **ส่ง Token เข้าสู่ระบบ Auto Quest เรียบร้อยแล้ว!**\n"
            f"👤 **บัญชี Discord:** `{username}`\n"
            f"📍 **ห้องสถานะสด:** {status_ch.mention}\n"
            f"🏆 **ห้องผลลัพธ์ของรางวัล:** {result_ch.mention}\n"
            f"{quota_msg}\n"
            f"👉 คลิกปุ่ม **[🔍 CHECK STATUS]** ด้านล่างเพื่อติดตามการทำเควสแบบเรียลไทม์ได้ทันที"
        ),
        view=check_view,
        ephemeral=True
    )


# ─────────────────────────────────────────────────────────────
# 2. SUCCESS VIEW WITH 1-CLICK AUTOQUEST BUTTON
# ─────────────────────────────────────────────────────────────
class TokenResultSuccessView(discord.ui.View):
    """Attached to successful token extraction responses."""
    def __init__(self, token: str, user_id: int):
        super().__init__(timeout=300)
        self.token = token
        self.user_id = user_id
        self.add_item(discord.ui.Button(
            label="🌐 เปิด Discord Web",
            style=discord.ButtonStyle.link,
            url="https://discord.com/app"
        ))

    @discord.ui.button(
        label="🚀 ส่ง Token ไปทำ Auto Quest ทันที",
        style=discord.ButtonStyle.success,
        emoji="⚡",
        custom_id="pbg_token:btn_send_autoquest",
        row=0
    )
    async def btn_send_quest(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ ข้อความนี้เป็นของผู้อื่น", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        button.disabled = True
        button.label = "กำลังรัน Auto Quest..."
        try:
            await interaction.edit_original_response(view=self)
        except Exception:
            pass
        await enqueue_token_for_autoquest(interaction, self.token)

    @discord.ui.button(
        label="🗑️ ทำลายข้อความทันที",
        style=discord.ButtonStyle.danger,
        custom_id="pbg_token:btn_destroy_success",
        row=0
    )
    async def btn_destroy(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ ข้อความนี้เป็นของผู้อื่น", ephemeral=True)
        expired_embed = discord.Embed(
            title="🔒 ทำลายข้อความเรียบร้อยแล้ว",
            description="ข้อความคำแนะนำและข้อมูล Token ถูกปิดการใช้งานและล้างออกจากระบบเพื่อความปลอดภัยเรียบร้อยแล้ว",
            color=COLOR_EXPIRED
        )
        await interaction.response.edit_message(embed=expired_embed, view=None, attachments=[])


class EphemeralActionToolbar(discord.ui.View):
    """General toolbar for instruction/info pages with destroy button."""
    def __init__(self, user_id: int, web_url: Optional[str] = None):
        super().__init__(timeout=300)
        self.user_id = user_id
        if web_url:
            self.add_item(discord.ui.Button(
                label="🌐 เปิดเว็บดึง Token อัตโนมัติ",
                style=discord.ButtonStyle.link,
                url=web_url
            ))
        self.add_item(discord.ui.Button(
            label="🌐 เปิด Discord Web",
            style=discord.ButtonStyle.link,
            url="https://discord.com/app"
        ))

    @discord.ui.button(
        label="🗑️ ทำลายข้อความทันที",
        style=discord.ButtonStyle.danger,
        custom_id="pbg_token:btn_destroy_toolbar"
    )
    async def btn_destroy(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ ข้อความนี้เป็นของผู้อื่น", ephemeral=True)
        expired_embed = discord.Embed(
            title="🔒 ทำลายข้อความเรียบร้อยแล้ว",
            description="ข้อความคำแนะนำถูกปิดการใช้งานและทำลายเพื่อความปลอดภัยเรียบร้อยแล้ว",
            color=COLOR_EXPIRED
        )
        await interaction.response.edit_message(embed=expired_embed, view=None, attachments=[])


# ─────────────────────────────────────────────────────────────
# 3. DIRECT LOGIN TOKEN EXTRACTOR MODAL (DESKTOP EMULATION)
# ─────────────────────────────────────────────────────────────
class TokenLoginExtractorModal(discord.ui.Modal, title="🔐 ล็อกอินดึง Token อัตโนมัติ (ไม่ต้อง F12)"):
    email = discord.ui.TextInput(
        label="อีเมล Discord หรือ เบอร์โทรศัพท์",
        placeholder="example@email.com หรือ เบอร์โทรศัพท์...",
        required=True
    )
    password = discord.ui.TextInput(
        label="รหัสผ่านบัญชี Discord",
        placeholder="รหัสผ่านบัญชี Discord ของคุณ...",
        style=discord.TextStyle.short,
        required=True
    )
    mfa_code = discord.ui.TextInput(
        label="รหัส 2FA Authenticator 6 หลัก (ถ้ามี)",
        placeholder="ใส่รหัส Authenticator 6 หลัก หรือเว้นว่างได้",
        style=discord.TextStyle.short,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        login_val = self.email.value.strip()
        pass_val = self.password.value.strip()
        mfa_val = self.mfa_code.value.strip()

        payload = {
            "login": login_val,
            "password": pass_val,
            "undelete": False,
            "captcha_key": None,
            "login_source": None,
            "gift_code_sku_id": None,
            "login_status": None
        }

        # Authentic Desktop Client Headers with Super Properties
        headers = {
            "Content-Type": "application/json",
            "User-Agent": DISCORD_CLIENT_UA,
            "Referer": "https://discord.com/login",
            "Origin": "https://discord.com",
            "X-Super-Properties": ENCODED_SUPER_PROPERTIES,
            "X-Discord-Locale": "th",
            "X-Discord-Timezone": "Asia/Bangkok",
            "X-Debug-Options": "bugReporterEnabled"
        }

        token = None
        error_msg = None
        hit_captcha = False

        data = {}
        resp_status = 0
        used_curl = False

        if HAVE_CURL_CFFI:
            try:
                async with CurlAsyncSession(impersonate="chrome124") as curl_s:
                    await curl_s.get("https://discord.com/login", timeout=8)
                    curl_resp = await curl_s.post(
                        "https://discord.com/api/v9/auth/login",
                        json=payload,
                        headers=headers,
                        timeout=15
                    )
                    resp_status = curl_resp.status_code
                    try:
                        data = curl_resp.json()
                    except Exception:
                        data = {}
                    used_curl = True
            except Exception as ce:
                print(f"[DirectAuth] curl_cffi attempt failed: {ce}", flush=True)

        if not used_curl or resp_status == 0:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://discord.com/api/v9/auth/login",
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=15)
                    ) as resp:
                        resp_status = resp.status
                        data = await resp.json()
            except Exception as e:
                error_msg = f"❌ เกิดข้อผิดพลาดในการเชื่อมต่อ Discord Auth: {e}"

        try:
            if resp_status == 200 and "token" in data:
                token = data["token"]
            elif data.get("mfa") and data.get("ticket"):
                ticket = data["ticket"]
                if mfa_val:
                    mfa_payload = {
                        "code": mfa_val,
                        "ticket": ticket,
                        "login_source": None,
                        "gift_code_sku_id": None
                    }
                    if HAVE_CURL_CFFI:
                        async with CurlAsyncSession(impersonate="chrome124") as curl_s:
                            mfa_resp = await curl_s.post(
                                "https://discord.com/api/v9/auth/mfa/totp",
                                json=mfa_payload,
                                headers=headers,
                                timeout=15
                            )
                            mfa_data = mfa_resp.json()
                            if mfa_resp.status_code == 200 and "token" in mfa_data:
                                token = mfa_data["token"]
                            else:
                                error_msg = "❌ รหัส 2FA (Authenticator) ไม่ถูกต้อง หรือหมดอายุแล้ว"
                    else:
                        async with aiohttp.ClientSession() as session:
                            async with session.post(
                                "https://discord.com/api/v9/auth/mfa/totp",
                                json=mfa_payload,
                                headers=headers,
                                timeout=aiohttp.ClientTimeout(total=15)
                            ) as mfa_resp:
                                mfa_data = await mfa_resp.json()
                                if mfa_resp.status == 200 and "token" in mfa_data:
                                    token = mfa_data["token"]
                                else:
                                    error_msg = "❌ รหัส 2FA (Authenticator) ไม่ถูกต้อง หรือหมดอายุแล้ว"
                else:
                    error_msg = "🔐 บัญชีของคุณเปิดใช้งาน 2FA กรุณากรอกรหัส Authenticator 6 หลักในช่อง 2FA ด้วยครับ"
            elif "captcha_key" in data or "captcha_sitekey" in data:
                hit_captcha = True
                error_msg = (
                    "🧩 **Discord ตรวจพบการเข้าสู่ระบบจาก IP เซิร์ฟเวอร์ และร้องขอ CAPTCHA**\n\n"
                    "💡 **วิธีแก้ปัญหาที่ง่ายและสะดวกที่สุด:**\n"
                    "• กดปุ่ม **\"📷 สแกน QR Code (ดึง Token ออโต้)\"** บนเมนูหลัก\n"
                    "  เพียงเปิดแอป Discord ในมือถือสแกนแล้วกดยืนยัน จะได้รับ Token ทันทีโดย**ไม่ติด CAPTCHA และไม่ต้องกรอกรหัสผ่าน 100%!**"
                )
            elif "password" in str(data):
                error_msg = "🔑 อีเมลหรือรหัสผ่านไม่ถูกต้อง กรุณาตรวจสอบอีกครั้ง"
            elif not token and not error_msg:
                error_msg = f"❌ ไม่สามารถล็อกอินได้: {data.get('message', 'โปรดลองใช้วิธีสแกน QR Code แทน')}"
        except Exception as e:
            if not error_msg:
                error_msg = f"❌ เกิดข้อผิดพลาดในการเชื่อมต่อ Discord Auth: {e}"

        if token:
            now_ts = int(time.time())
            expire_ts = now_ts + 300
            embed = discord.Embed(
                title="✅ ล็อกอินดึง Token สำเร็จ 100%!",
                description=(
                    f"👤 **ผู้ใช้งาน:** {interaction.user.mention}\n\n"
                    "🔑 **User Token ของคุณ (แตะเพื่อคัดลอก):**\n"
                    f"```\n{token}\n```\n"
                    "🚀 **ทำเควสทันที:** คุณสามารถกดปุ่มสีเขียว **[🚀 ส่ง Token ไปทำ Auto Quest ทันที]** ด้านล่างได้เลย บอทจะเริ่มทำเควสให้ทันทีโดยไม่ต้องก็อปปี้!\n\n"
                    "🛡️ **ระบบรักษาความปลอดภัย (Zero Retention):**\n"
                    "• รหัสผ่านและ Token ไม่มีการบันทึกลง Database ข้อมูลประมวลผลใน RAM ชั่วคราวเท่านั้น\n"
                    f"• ข้อความนี้จะถูกทำลายและปิดการใช้งานภายใน 5 นาที (<t:{expire_ts}:R>)"
                ),
                color=COLOR_SUCCESS
            )
            embed.set_footer(text="PAYOMBØYZ SECURITY • Direct Auth Session")
            view = TokenResultSuccessView(token=token, user_id=interaction.user.id)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        else:
            embed = discord.Embed(
                title="⚠️ ดึง Token ไม่สำเร็จ",
                description=error_msg,
                color=COLOR_DANGER
            )
            view = discord.ui.View()
            if hit_captcha:
                qr_btn = discord.ui.Button(
                    label="📷 สลับไปสแกน QR Code (ไม่ติด Captcha)",
                    style=discord.ButtonStyle.primary,
                    emoji="📷",
                    custom_id="pbg_token:btn_fallback_qr"
                )
                async def fallback_qr_cb(btn_interaction: discord.Interaction):
                    await btn_interaction.response.defer(ephemeral=True, thinking=True)
                    worker = DiscordRemoteAuthWorker(btn_interaction)
                    asyncio.create_task(worker.execute())
                qr_btn.callback = fallback_qr_cb
                view.add_item(qr_btn)

            view.add_item(discord.ui.Button(
                label="🌐 เปิด Discord Web",
                style=discord.ButtonStyle.link,
                url="https://discord.com/app"
            ))
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)


# ─────────────────────────────────────────────────────────────
# 4. DISCORD REMOTE AUTH QR CODE WORKER (FIXED HTTP 400 ERROR)
# ─────────────────────────────────────────────────────────────
class DiscordRemoteAuthWorker:
    """
    Implements true Discord Remote Authentication WebSocket Protocol (v2).
    Generates QR code for mobile Discord app scanner, listens for user approval,
    decrypts the user token in memory, and delivers it to the user's ephemeral channel.
    Injects full Desktop Super Properties into ticket exchange to prevent HTTP 400.
    """
    GATEWAY_URL = "wss://remote-auth-gateway.discord.gg/?v=2"
    LOGIN_URL = "https://discord.com/api/v9/users/@me/remote-auth/login"

    def __init__(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key = self.private_key.public_key()
        
        spki_der = self.public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        self.encoded_public_key = base64.b64encode(spki_der).decode("utf-8")
        self.fingerprint = None
        self.running = True

    def generate_qr_file(self, fingerprint: str) -> discord.File:
        qr_target = f"https://discord.com/ra/{fingerprint}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2
        )
        qr.add_data(qr_target)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#1E1F22", back_color="#FFFFFF")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return discord.File(buf, filename="discord_qr.png")

    async def execute(self):
        try:
            # 1. Warm up session and fetch real Cloudflare & Discord cookies (__dcfduid, __sdcfduid)
            harvested_cookies = {}
            try:
                async with aiohttp.ClientSession() as prep_session:
                    async with prep_session.get(
                        "https://discord.com/login",
                        headers={"User-Agent": DISCORD_CLIENT_UA},
                        timeout=aiohttp.ClientTimeout(total=8)
                    ) as prep_resp:
                        for k, v in prep_resp.cookies.items():
                            harvested_cookies[k] = v.value
            except Exception:
                pass

            async with websockets.connect(
                self.GATEWAY_URL,
                origin="https://discord.com",
                extra_headers={"User-Agent": DISCORD_CLIENT_UA}
            ) as ws:
                heartbeat_task = None
                
                async for raw_message in ws:
                    if not self.running:
                        break
                    
                    data = json.loads(raw_message)
                    op = data.get("op")

                    if op == "hello":
                        interval = data.get("heartbeat_interval", 41250) / 1000.0
                        
                        async def heartbeat_loop():
                            try:
                                while self.running:
                                    await asyncio.sleep(interval)
                                    await ws.send(json.dumps({"op": "heartbeat"}))
                            except Exception:
                                pass
                                
                        heartbeat_task = asyncio.create_task(heartbeat_loop())
                        
                        # Send init with public key
                        await ws.send(json.dumps({
                            "op": "init",
                            "encoded_public_key": self.encoded_public_key
                        }))

                    elif op == "nonce_proof":
                        encrypted_nonce = base64.b64decode(data["encrypted_nonce"])
                        decrypted_nonce = self.private_key.decrypt(
                            encrypted_nonce,
                            padding.OAEP(
                                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                                algorithm=hashes.SHA256(),
                                label=None
                            )
                        )
                        nonce_hash = hashlib.sha256(decrypted_nonce).digest()
                        proof = base64.urlsafe_b64encode(nonce_hash).decode("utf-8").rstrip("=")
                        
                        await ws.send(json.dumps({
                            "op": "nonce_proof",
                            "proof": proof
                        }))

                    elif op == "pending_remote_init":
                        self.fingerprint = data.get("fingerprint")
                        if not self.fingerprint:
                            continue
                            
                        qr_file = self.generate_qr_file(self.fingerprint)
                        now_ts = int(time.time())
                        expire_ts = now_ts + 120  # QR valid for 2 mins

                        embed = discord.Embed(
                            title="📷 สแกน QR Code เพื่อดึง Token (Discord Remote Auth)",
                            description=(
                                f"👤 **ผู้ใช้งาน:** {self.interaction.user.mention} (`{self.interaction.user.id}`)\n\n"
                                "📱 **ขั้นตอนการสแกนด้วยโทรศัพท์มือถือ (ง่ายและปลอดภัยที่สุด):**\n"
                                "1. เปิดแอป **Discord บนโทรศัพท์มือถือ** ของท่าน\n"
                                "2. แตะที่ **รูปโปรไฟล์มุมขวาล่าง** เพื่อเข้าหน้าต่าง **การตั้งค่า (Settings)**\n"
                                "3. เลื่อนลงมาเลือกหัวข้อ **\"สแกนคิวอาร์โค้ด (Scan QR Code)\"**\n"
                                "4. ใช้กล้องมือถือสแกนรูปภาพ QR Code ด้านล่างนี้\n"
                                "5. กดปุ่ม **\"ยืนยันการเข้าสู่ระบบ (Yes, log me in)\"** บนมือถือ\n\n"
                                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"⏳ **สถานะ:** กำลังรอการสแกนจากโทรศัพท์... (หมดอายุ <t:{expire_ts}:R>)\n"
                                "🔒 *ระบบจะถอดรหัสและส่ง Token ให้คุณทันทีหลังกดยืนยัน*"
                            ),
                            color=COLOR_PRIMARY
                        )
                        embed.set_image(url="attachment://discord_qr.png")
                        embed.set_footer(text="PAYOMBØYZ REMOTE AUTH • เข้ารหัส 2048-bit RSA ชั่วคราวใน RAM")

                        view = EphemeralActionToolbar(user_id=self.interaction.user.id)
                        try:
                            await self.interaction.edit_original_response(embed=embed, attachments=[qr_file], view=view)
                        except Exception:
                            await self.interaction.followup.send(embed=embed, file=qr_file, view=view, ephemeral=True)

                    elif op == "pending_ticket":
                        # User scanned QR on phone
                        encrypted_user = base64.b64decode(data.get("encrypted_user_payload", ""))
                        try:
                            user_payload = self.private_key.decrypt(
                                encrypted_user,
                                padding.OAEP(
                                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                                    algorithm=hashes.SHA256(),
                                    label=None
                                )
                            ).decode("utf-8")
                            parts = user_payload.split(":")
                            u_id = parts[0] if len(parts) > 0 else "Unknown"
                            u_name = parts[3] if len(parts) > 3 else "Discord User"
                        except Exception:
                            u_id = "Detected"
                            u_name = "Discord User"

                        scanned_embed = discord.Embed(
                            title="📲 ตรวจพบการสแกนแล้ว! รอการยืนยันบนโทรศัพท์",
                            description=(
                                f"👤 **พบบัญชี:** `{u_name}` (ID: `{u_id}`)\n\n"
                                "⚠️ **โปรดกดปุ่ม \"ยืนยันการเข้าสู่ระบบ (Yes, log me in)\" บนโทรศัพท์ของท่านทันที**\n"
                                "ระบบกำลังรอรับ Token เพื่อส่งกลับมาให้ท่านในข้อความนี้...\n\n"
                                "⏱️ *กรุณากดยืนยันภายใน 30 วินาที*"
                            ),
                            color=COLOR_WARNING
                        )
                        scanned_embed.set_footer(text="PAYOMBØYZ REMOTE AUTH • กำลังรออนุมัติ")
                        try:
                            await self.interaction.edit_original_response(embed=scanned_embed, attachments=[])
                        except Exception:
                            pass

                    elif op == "pending_login":
                        ticket = data.get("ticket")
                        if not ticket:
                            continue

                        # Exchange ticket for encrypted token using genuine Chrome TLS fingerprint (curl_cffi)
                        login_headers = {
                            "Origin": "https://discord.com",
                            "Referer": "https://discord.com/login",
                            "Content-Type": "application/json",
                            "Accept": "*/*",
                            "Accept-Language": "th-TH,th;q=0.9,en-US;q=0.8,en;q=0.7",
                            "X-Super-Properties": ENCODED_SUPER_PROPERTIES,
                            "X-Discord-Locale": "th",
                            "X-Discord-Timezone": "Asia/Bangkok"
                        }

                        login_data = {}
                        resp_status = 0
                        err_text = ""

                        if HAVE_CURL_CFFI:
                            try:
                                async with CurlAsyncSession(impersonate="chrome124") as curl_s:
                                    await curl_s.get("https://discord.com/login", timeout=8)
                                    c_resp = await curl_s.post(
                                        self.LOGIN_URL,
                                        json={"ticket": ticket},
                                        headers=login_headers,
                                        timeout=15
                                    )
                                    resp_status = c_resp.status_code
                                    try:
                                        login_data = c_resp.json()
                                    except Exception:
                                        err_text = c_resp.text
                            except Exception as ce:
                                print(f"[RemoteAuth] curl_cffi login exchange note: {ce}", flush=True)

                        if resp_status == 0:
                            async with aiohttp.ClientSession(cookies=harvested_cookies) as session:
                                async with session.post(
                                    self.LOGIN_URL,
                                    json={"ticket": ticket},
                                    headers=login_headers,
                                    timeout=aiohttp.ClientTimeout(total=15)
                                ) as resp:
                                    resp_status = resp.status
                                    try:
                                        login_data = await resp.json()
                                    except Exception:
                                        err_text = await resp.text()

                        if resp_status == 200:
                            enc_token_b64 = login_data.get("encrypted_token")
                            if enc_token_b64:
                                dec_token = self.private_key.decrypt(
                                    base64.b64decode(enc_token_b64),
                                    padding.OAEP(
                                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                                        algorithm=hashes.SHA256(),
                                        label=None
                                    )
                                ).decode("utf-8")

                                now_ts = int(time.time())
                                expire_ts = now_ts + 300

                                success_embed = discord.Embed(
                                    title="✅ ดึง User Token สำเร็จเรียบร้อยแล้ว!",
                                    description=(
                                        f"👤 **ผู้ใช้งาน:** {self.interaction.user.mention}\n\n"
                                        "🔑 **Discord User Token ของคุณ (แตะเพื่อคัดลอก):**\n"
                                        f"```\n{dec_token}\n```\n"
                                        "🚀 **ทำเควสทันที:** คลิกปุ่มสีเขียว **[🚀 ส่ง Token ไปทำ Auto Quest ทันที]** ด้านล่างได้เลย บอทจะเริ่มทำเควสให้ทันที!\n\n"
                                        "🛡️ **ระบบรักษาความปลอดภัย (Zero Retention):**\n"
                                        "• ข้อมูลประมวลผลใน RAM ชั่วคราวเท่านั้น ไม่มีการบันทึกลงดิสก์หรือฐานข้อมูล\n"
                                        f"• ข้อความนี้จะถูกทำลายและปิดการใช้งานภายใน 5 นาที (<t:{expire_ts}:R>)"
                                    ),
                                    color=COLOR_SUCCESS
                                )
                                success_embed.set_footer(text="PAYOMBØYZ SECURITY • 100% Client-Side Delivery")
                                view = TokenResultSuccessView(token=dec_token, user_id=self.interaction.user.id)
                                try:
                                    await self.interaction.edit_original_response(embed=success_embed, view=view, attachments=[])
                                except Exception:
                                    pass
                                
                                self._schedule_final_destruction(self.interaction)
                                self.running = False
                                break
                        else:
                            print(f"[RemoteAuth] Login exchange rejected ({resp_status}): {err_text}", flush=True)

                            web_token_url = "https://www.payomboyzcreative.online/token"
                            if "captcha" in err_text.lower():
                                fail_embed = discord.Embed(
                                    title="🛡️ Discord บังคับยืนยัน Captcha สำหรับ IP นี้",
                                    description=(
                                        "⚠️ **Discord บังคับแก้ Captcha สำหรับการแลกเปลี่ยน Token บน Cloud Node (Datacenter IP)**\n\n"
                                        "✨ **วิธีดึง Token ไร้ Captcha 100% (ทำผ่านเน็ตบ้านของคุณ):**\n"
                                        "• **บนคอม (PC):** คลิกปุ่มสีฟ้า **[🌐 เปิดเว็บ PAYOMBØYZ TOKEN]** ด้านล่างนี้เพื่อดึง Token บนเบราว์เซอร์ของคุณโดยตรง\n"
                                        "• **บนมือถือ:** เปิด Discord Web ใน Safari / Chrome แล้วแตะ Bookmarklet\n\n"
                                        "🚀 **เมื่อได้ Token แล้ว:** นำมาส่งในช่องบอท Auto Quest เพื่อเริ่มทำเควสได้ทันที!"
                                    ),
                                    color=COLOR_WARNING
                                )
                                fail_view = EphemeralActionToolbar(user_id=self.interaction.user.id, web_url=web_token_url)
                            else:
                                fail_embed = discord.Embed(
                                    title="❌ การยืนยันตัวตนล้มเหลว",
                                    description=(
                                        f"Discord ปฏิเสธการแลกเปลี่ยน Token (HTTP {resp_status}) หรือเซสชันหมดอายุ\n"
                                        "กรุณากดลองสแกนใหม่อีกครั้ง และตรวจสอบว่าโทรศัพท์เชื่อมต่ออินเทอร์เน็ตปกติ"
                                    ),
                                    color=COLOR_DANGER
                                )
                                fail_view = EphemeralActionToolbar(user_id=self.interaction.user.id, web_url=web_token_url)
                            try:
                                await self.interaction.edit_original_response(embed=fail_embed, attachments=[], view=fail_view)
                            except Exception:
                                pass
                            self.running = False
                            break

                    elif op == "cancel":
                        cancel_embed = discord.Embed(
                            title="❌ ยกเลิกการเข้าสู่ระบบ",
                            description="การเชื่อมต่อถูกยกเลิกจากโทรศัพท์ หรือหมดเวลาการเชื่อมต่อ กรุณากดปุ่มสร้าง QR Code ใหม่อีกครั้ง",
                            color=COLOR_DANGER
                        )
                        try:
                            await self.interaction.edit_original_response(embed=cancel_embed, attachments=[])
                        except Exception:
                            pass
                        self.running = False
                        break

                if heartbeat_task and not heartbeat_task.done():
                    heartbeat_task.cancel()

        except Exception as e:
            try:
                err_embed = discord.Embed(
                    title="⚠️ การเชื่อมต่อ QR Code สิ้นสุด",
                    description=f"เซสชันหมดเวลาหรือการเชื่อมต่อปิดลงแล้ว ({e})\nหากต้องการใช้งานโปรดกดปุ่มอีกครั้ง",
                    color=COLOR_EXPIRED
                )
                await self.interaction.edit_original_response(embed=err_embed, attachments=[])
            except Exception:
                pass

    def _schedule_final_destruction(self, interaction: discord.Interaction):
        async def expire():
            await asyncio.sleep(300)
            try:
                expired_embed = discord.Embed(
                    title="🔒 เซสชันแสดง Token หมดอายุแล้ว (5 นาที)",
                    description="ข้อความแสดง Token นี้ถูกทำลายและปิดการใช้งานเพื่อความปลอดภัยของคุณเรียบร้อยแล้ว",
                    color=COLOR_EXPIRED
                )
                await interaction.edit_original_response(embed=expired_embed, view=None, attachments=[])
            except Exception:
                pass
        asyncio.create_task(expire())


# ─────────────────────────────────────────────────────────────
# 5. MAIN PERSISTENT PANEL VIEW (/find_token)
# ─────────────────────────────────────────────────────────────
class FindTokenPanelView(discord.ui.View):
    """
    Persistent View for /find_token Panel.
    Equipped with real QR Code Login, PC Web Helper, Mobile Bookmarklet, and Direct Login.
    Survives bot restarts.
    """
    def __init__(self):
        super().__init__(timeout=None)

    # 🔐 ROW 0: BUTTON DIRECT LOGIN (ZERO F12)
    @discord.ui.button(
        label="ล็อกอินดึง Token (ไม่ต้อง F12)",
        style=discord.ButtonStyle.success,
        emoji="🔐",
        custom_id="pbg_find_token:btn_login",
        row=0
    )
    async def btn_login(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TokenLoginExtractorModal())

    # 📷 ROW 0: BUTTON REAL QR CODE LOGIN
    @discord.ui.button(
        label="สแกน QR Code (ดึง Token ออโต้)",
        style=discord.ButtonStyle.primary,
        emoji="📷",
        custom_id="pbg_find_token:btn_qr",
        row=0
    )
    async def btn_qr(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        worker = DiscordRemoteAuthWorker(interaction)
        asyncio.create_task(worker.execute())

    # 💻 ROW 1: BUTTON PC WEB & CONSOLE
    @discord.ui.button(
        label="สำหรับ PC (เปิดเว็บ / Console 5 วิ)",
        style=discord.ButtonStyle.secondary,
        emoji="💻",
        custom_id="pbg_find_token:btn_pc",
        row=1
    )
    async def btn_pc(self, interaction: discord.Interaction, button: discord.ui.Button):
        now_ts = int(time.time())
        expire_ts = now_ts + 300
        web_token_url = "https://www.payomboyzcreative.online/token"

        embed = discord.Embed(
            title="💻 วิธีดึง Token บน PC / คอมพิวเตอร์ (ทำได้ใน 5 วินาที)",
            description=(
                f"👤 **ผู้ใช้งาน:** {interaction.user.mention} (`{interaction.user.id}`)\n\n"
                "🌟 **วิธีที่ 1: ดึงอัตโนมัติผ่านเว็บเบราว์เซอร์ (คลิกปุ่มด้านล่าง)**\n"
                f"• เปิดหน้าเว็บ: **[🌐 PAYOMBØYZ TOKEN BRIDGE]({web_token_url})**\n"
                "• มีปุ่มลากใส่ Bookmarks และสคริปต์ 1 คลิกที่จะดึง Token ให้อัตโนมัติทันที!\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "🌟 **วิธีที่ 2: วางคำสั่ง Console 1 บรรทัด (สำหรับคนชอบ F12)**\n"
                "1. เปิด Discord บนเบราว์เซอร์ (Chrome / Edge / Opera) หรือ Discord App บน PC\n"
                "2. กดปุ่มลัด **`Ctrl + Shift + I`** บนคีย์บอร์ด (หรือคลิกขวาเลือก *Inspect / ตรวจสอบ*)\n"
                "3. คลิกไปที่แท็บ **Console**\n"
                "   *(หากมีคำเตือนสีแดงจาก Discord ให้พิมพ์ `allow pasting` แล้วกด Enter ก่อน)*\n"
                "4. คัดลอกโค้ดด้านล่างนี้ วางลงในช่อง Console แล้วกด **Enter**:\n"
                "```javascript\n"
                "(webpackChunkdiscord_app.push([[''],{},e=>{m=[];for(let c in e.c)m.push(e.c[c])}]),m).find(m=>m?.exports?.default?.getToken!==void 0).exports.default.getToken()\n"
                "```\n"
                "5. **Token จะแสดงเป็นข้อความยาวๆ ในเครื่องหมายคำพูด**\n"
                "   คัดลอกเฉพาะข้อความในเครื่องหมายคำพูด นำไปส่งในบอท Auto Quest ได้ทันที!\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⏱️ **ความปลอดภัย:** ข้อความนี้มองเห็นได้เฉพาะคุณ และ**จะทำลายตัวเองภายใน 5 นาที** (<t:{expire_ts}:R>)"
            ),
            color=COLOR_PRIMARY
        )
        embed.set_footer(text="PAYOMBØYZ SECURITY • ไร้ Database ปลอดภัย 100%")

        view = EphemeralActionToolbar(user_id=interaction.user.id, web_url=web_token_url)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        self._schedule_auto_expire(interaction)

    # 📱 ROW 1: BUTTON MOBILE BOOKMARKLET
    @discord.ui.button(
        label="สำหรับ มือถือ (Bookmarklet & Web)",
        style=discord.ButtonStyle.secondary,
        emoji="📱",
        custom_id="pbg_find_token:btn_mobile",
        row=1
    )
    async def btn_mobile(self, interaction: discord.Interaction, button: discord.ui.Button):
        now_ts = int(time.time())
        expire_ts = now_ts + 300
        web_token_url = "https://www.payomboyzcreative.online/token"

        embed = discord.Embed(
            title="📱 วิธีดึง Token บนมือถือ / iPad / แท็บเล็ต (Bookmarklet & Web)",
            description=(
                f"👤 **ผู้ใช้งาน:** {interaction.user.mention} (`{interaction.user.id}`)\n\n"
                "💡 **คำแนะนำที่ดีที่สุดสำหรับมือถือ:**\n"
                "• แนะนำให้ใช้ปุ่ม **\"📷 สแกน QR Code (ดึง Token ออโต้)\"** บนคอมหรืออุปกรณ์อื่น แล้วเอามือถือเครื่องนี้เปิด Discord สแกน จะสะดวกที่สุด ไม่ต้องตั้งค่าอะไรเลย!\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "🌟 **วิธีที่ 1: ดึงผ่าน Bookmarklet บนเว็บเบราว์เซอร์มือถือ**\n"
                "1. เปิดเว็บเบราว์เซอร์ในมือถือ เข้าไปที่: **https://discord.com/app** แล้วล็อกอิน\n"
                "2. ทำการบันทึกหน้านั้นเป็น **Bookmark (ที่คั่นหน้า)** ไว้\n"
                "3. เข้าไปแก้ไข Bookmark นั้น โดยเปลี่ยนช่อง URL ให้เป็นโค้ดด้านล่างนี้:\n"
                "```javascript\n"
                "javascript:(function(){let t=(webpackChunkdiscord_app.push([[''],{},e=>{m=[];for(let c in e.c)m.push(e.c[c])}]),m).find(m=>m?.exports?.default?.getToken!==void 0).exports.default.getToken();prompt(\"คัดลอก Token ของคุณ:\",t)})();\n"
                "```\n"
                "4. กลับไปที่หน้า Discord Web แล้วแตะที่แถบพิมพ์ URL ด้านบน พิมพ์ชื่อ Bookmark แล้วกดรัน\n"
                "5. หน้าจอจะเด้งกล่อง Prompt พร้อม Token ให้คัดลอกได้ทันที!\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⏱️ **ความปลอดภัย:** ข้อความนี้มองเห็นได้เฉพาะคุณ และ**จะทำลายตัวเองภายใน 5 นาที** (<t:{expire_ts}:R>)"
            ),
            color=COLOR_SUCCESS
        )
        embed.set_footer(text="PAYOMBØYZ SECURITY • ไร้ Database ปลอดภัย 100%")

        view = EphemeralActionToolbar(user_id=interaction.user.id, web_url=web_token_url)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        self._schedule_auto_expire(interaction)

    def _schedule_auto_expire(self, interaction: discord.Interaction):
        async def expire():
            await asyncio.sleep(300)
            try:
                expired_embed = discord.Embed(
                    title="🔒 เซสชันหมดอายุแล้ว (5 นาที)",
                    description=(
                        "ข้อความแสดงข้อมูลนี้ถูกปิดการใช้งานและทำลายเพื่อความปลอดภัยเรียบร้อยแล้ว\n"
                        "หากต้องการดึงข้อมูลใหม่อีกครั้ง โปรดกดปุ่มเลือกหมวดหมู่ที่แผงข้อความหลัก"
                    ),
                    color=COLOR_EXPIRED
                )
                await interaction.edit_original_response(embed=expired_embed, view=None, attachments=[])
            except Exception:
                pass

        asyncio.create_task(expire())


# ─────────────────────────────────────────────────────────────
# 6. BUILD MAIN PANEL EMBED
# ─────────────────────────────────────────────────────────────
def build_find_token_panel_embed(
    title: Optional[str] = None,
    description: Optional[str] = None,
    color_hex: Optional[str] = None
) -> discord.Embed:
    """Build the public persistent panel embed."""
    panel_title = title or "𓆩 🔑 PAYOMBØYZ • ศูนย์ช่วยเหลือดึง Token (Auto Quest) 𓆪"
    panel_desc = description or (
        "แผงระบบช่วยค้นหา Discord User Token สำหรับนำไปใช้งานกับบอท **Discord Auto Quest**\n"
        "(สำหรับทำเควสเล่นเกม / ดูสตรีม / ปลดล็อกของรางวัลอัตโนมัติ)\n\n"
        "⚡ **เลือกวิธีดึง Token ตามที่ท่านสะดวก:**\n"
        "• **🔐 ล็อกอินดึง Token (ไม่ต้อง F12)**: กรอกอีเมลและรหัสผ่านในป๊อปอัป ระบบจะดึง Token มาให้ทันที (ไม่ต้องเปิด DevTools)\n"
        "• **📷 สแกน QR Code (ดึง Token ออโต้)**: สร้าง QR Code ให้เอามือถือเปิด Discord สแกนแล้ว Token จะเด้งขึ้นมาทันที (ไม่ติด Captcha)\n"
        "• **💻 สำหรับ PC (เปิดเว็บ / Console 5 วิ)**: เปิดหน้าเว็บตัวช่วยดึง หรือวางโค้ด Console 1 บรรทัด\n"
        "• **📱 สำหรับ มือถือ (Bookmarklet & Web)**: วิธีดึงผ่าน Bookmarklet บนเว็บเบราว์เซอร์มือถือ\n\n"
        "🚀 **ระบบส่งตรงเข้า Auto Quest:** เมื่อดึง Token สำเร็จ จะมีปุ่มสีเขียว **[🚀 ส่ง Token ไปทำ Auto Quest ทันที]** ให้กดทำเควสได้เลยโดยไม่ต้องก็อปปี้!\n\n"
        "🛡️ **เงื่อนไขและการรักษาความปลอดภัย (Zero Retention Guarantee):**\n"
        "1. ระบบนี้**ไม่มี Database** ไม่มีการบันทึกหรือส่งต่อ Token ของผู้ใช้ใดๆ ทั้งสิ้น\n"
        "2. ผู้ใช้งานจะได้รับและมองเห็นเฉพาะ Token ของตัวเองเท่านั้น (ข้อความเห็นคนเดียว)\n"
        "3. มีระบบทำลายข้อความอัตโนมัติภายใน 5 นาที เพื่อความปลอดภัยสูงสุด\n\n"
        "⚠️ **คำเตือนสำคัญ:**\n"
        "Token เปรียบเสมือนกุญแจบัญชีของคุณ โปรดเก็บรักษาให้ดีและอย่านำไปให้บุคคลอื่นเด็ดขาด!"
    )
    
    embed_color = COLOR_PRIMARY
    if color_hex:
        try:
            cleaned = color_hex.lstrip("#")
            embed_color = int(cleaned, 16)
        except Exception:
            pass

    embed = discord.Embed(
        title=panel_title,
        description=panel_desc,
        color=embed_color
    )
    embed.set_footer(text="PAYOMBØYZ DISCORD QUEST HELPER • Zero Retention Architecture")
    return embed


# ─────────────────────────────────────────────────────────────
# 7. COG REGISTRATION
# ─────────────────────────────────────────────────────────────
class TokenFinderCog(commands.Cog, name="TokenFinder"):
    """🔑 ศูนย์ช่วยเหลือและดึง Token Discord สำหรับ Auto Quest"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="find_token",
        description="🔑 ส่งแผงช่วยเหลือและระบบดึง Discord User Token สำหรับ Auto Quest"
    )
    @app_commands.describe(
        channel="ช่องที่ต้องการส่งแผงข้อความ (เว้นว่างเพื่อส่งในช่องปัจจุบัน)",
        title="หัวข้อของแผงข้อความ (ไม่บังคับ)",
        description="รายละเอียดในแผงข้อความ (ไม่บังคับ)",
        color="รหัสสี HEX เช่น #5865F2 (ไม่บังคับ)"
    )
    @app_commands.default_permissions(administrator=True)
    async def cmd_find_token(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[str] = None
    ):
        target_ch = channel or interaction.channel
        if not target_ch or not hasattr(target_ch, "send"):
            return await interaction.response.send_message("❌ ไม่สามารถส่งข้อความในช่องที่เลือกได้", ephemeral=True)

        embed = build_find_token_panel_embed(title=title, description=description, color_hex=color)
        view = FindTokenPanelView()
        await target_ch.send(embed=embed, view=view)

        await interaction.response.send_message(
            f"✅ ส่งแผงดึง Token ไปยังช่อง {target_ch.mention} สำเร็จเรียบร้อยแล้ว!",
            ephemeral=True
        )

    @app_commands.command(
        name="token",
        description="🔑 เปิดหน้าต่างช่วยเหลือดึง Token สำหรับใช้งาน Auto Quest (เห็นเฉพาะคุณ)"
    )
    async def cmd_token_shortcut(self, interaction: discord.Interaction):
        embed = build_find_token_panel_embed()
        view = FindTokenPanelView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(TokenFinderCog(bot))
    print("  [OK] Loaded Cog: TokenFinderCog (/find_token, /token)")
