"""
Public Script Search — ตอบในช่องสาธารณะ ไม่ต้องกด /command
ดึงจาก RScript API สไตล์ 'Script-Search' Channel
ดีไซน์หรูหราแบบ Discord Components V2 Container Panel ขนาดใหญ่
"""
import discord
from discord import app_commands
from discord.ext import commands
import os, json
from config import COLOR_PRIMARY, COLOR_SUCCESS, COLOR_ERROR, COLOR_INFO

try:
    from utils.script_api import script_api
except ImportError:
    script_api = None

try:
    from utils.config_manager import guild_config
except ImportError:
    guild_config = None

SCRIPT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "scripts.json")

TYPE_EMOJI = {"farm":"🌾","admin":"👑","aimbot":"🎯","mod":"🔧","esp":"👁️","tool":"🛠️","raid":"⚔️","hunt":"🏹","stat":"📊","shop":"🛒","quest":"📜","dungeon":"🏚️","script":"📜"}

DEFAULT_SCRIPT_BANNER_URL = "https://cdn.discordapp.com/attachments/1565150107513520179/1565169276741226659/banner.gif"

def load_db():
    try:
        with open(SCRIPT_DB_PATH,"r",encoding="utf-8") as f: return json.load(f)
    except: return {}

def get_all():
    db=load_db(); res=[]
    for cat,scripts in db.items():
        for s in scripts: res.append({**s,"source":cat})
    return res

def format_script_code(item: dict) -> str:
    """แปลงข้อความสคริปต์ให้อยู่ในรูป Lua loadstring ที่ถูกต้อง ไม่ครอบซ้ำซ้อน"""
    raw = (item.get("raw_url") or item.get("url") or "").strip()
    if not raw:
        return ""
    if "loadstring" in raw or "\n" in raw:
        return raw
    if raw.startswith("http://") or raw.startswith("https://"):
        return f'loadstring(game:HttpGet("{raw}"))()'
    return raw


class ScriptCardView(discord.ui.LayoutView):
    """Luxury Discord Components V2 Container Panel for Roblox Script Search."""

    def __init__(self, items: list, page: int = 0, user_id: int = 0):
        super().__init__(timeout=300)
        self.items = items
        self.page = page
        self.user_id = user_id
        self._rebuild()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True  # ทุกคนกดได้

    def _rebuild(self):
        self.clear_items()
        idx = self.page
        if idx >= len(self.items):
            idx = 0
            self.page = 0
        s = self.items[idx]

        script_title = s.get("name", "Roblox Script").strip()
        game = s.get("game", "Unknown Game")
        verified = "✅ ยืนยันแล้ว (Safe)" if s.get("verified") else "⚠️ ยังไม่ยืนยัน"
        key = "🔐 มีระบบคีย์" if s.get("has_key") else "🔓 ฟรีไร้คีย์ 100%"
        views = s.get("views", 0)
        created = s.get("created", "")[:10] if s.get("created") else "N/A"
        updated = s.get("updated", "")[:10] if s.get("updated") else "N/A"
        mobile = "📱 รองรับมือถือ (Universal)" if s.get("is_universal") else "💻 PC / Executor ทั่วไป"
        src = "ScriptBlox" if "scriptblox" in s.get("source", "").lower() else ("RScripts" if "rscripts" in s.get("source", "").lower() else "PayomboyZ Vault")

        # 1. Header with custom animated wings
        header_text = (
            f"## <a:pbg_wing_l:1562553182859563150> **PAYOMBØYZ SCRIPT SEARCH ENGINE** <a:pbg_wing_r:1562553185325940748>\n"
            f"### 📜 **{script_title}**"
        )

        # 2. Body Text with Spec Matrix
        body_text = (
            f"> <:payomboyz:1551064225974325318> **ระบบค้นหาสคริปต์อัตโนมัติ (Roblox Script Engine)**\n"
            f"> 🎮 **เกม / แมพเป้าหมาย:** `{game}` 🔥\n"
            f"> 📦 **แหล่งข้อมูล:** `{src}` • **หน้าที่:** `{self.page+1}/{len(self.items)}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 **ข้อมูลสเปกสคริปต์ (Script Specifications):**\n"
            f"• 🛡️ **สถานะความปลอดภัย:** `{verified}`\n"
            f"• 🔑 **ระบบคีย์:** `{key}`\n"
            f"• 👁️ **ยอดเข้าชม:** `{views:,} ครั้ง`\n"
            f"• 📅 **วันที่สร้าง:** `{created}`\n"
            f"• 🔄 **อัปเดตล่าสุด:** `{updated}`\n"
            f"• 📱 **อุปกรณ์ที่รองรับ:** `{mobile}`"
        )

        # 3. Execution Code Box
        code = format_script_code(s)
        if code:
            display_code = code if len(code) <= 850 else f"{code[:840]}..."
            body_text += (
                f"\n\n📋 **Script Execution (คัดลอกไปวางใน Executor ได้ทันที):**\n"
                f"```lua\n{display_code}\n```"
            )

        # 4. Action Buttons
        prev_btn = discord.ui.Button(label="◀️ ก่อนหน้า", style=discord.ButtonStyle.secondary, custom_id=f"rscript:prev:{idx}")
        copy_btn = discord.ui.Button(label="📋 Copy Script", style=discord.ButtonStyle.success, custom_id=f"rscript:copy:{idx}")
        next_btn = discord.ui.Button(label="ถัดไป ▶️", style=discord.ButtonStyle.secondary, custom_id=f"rscript:next:{idx}")
        deobf_btn = discord.ui.Button(label="🔐 ส่งไป Deobfuscate (กู้ SRC 100%)", style=discord.ButtonStyle.danger, custom_id=f"rscript:deobf:{idx}")

        prev_btn.callback = self.on_prev
        copy_btn.callback = self.on_copy
        next_btn.callback = self.on_next
        deobf_btn.callback = self.on_deobf

        if len(self.items) <= 1:
            prev_btn.disabled = True
            next_btn.disabled = True
        else:
            prev_btn.disabled = (self.page == 0)
            next_btn.disabled = (self.page >= len(self.items) - 1)

        row1 = discord.ui.ActionRow(prev_btn, copy_btn, next_btn)
        row2 = discord.ui.ActionRow(deobf_btn)

        # 5. Image Banner (Script/Game Image or Default Luxury Banner)
        image_url = s.get("image") or s.get("imageUrl") or ""
        if not image_url:
            game_data = s.get("game_data") or s.get("game")
            if isinstance(game_data, dict):
                image_url = game_data.get("thumbnailUrl") or game_data.get("logoUrl") or game_data.get("imageUrl") or ""
        if image_url and image_url.startswith("/"):
            image_url = f"https://scriptblox.com{image_url}"
        
        if not (image_url and (image_url.startswith("http://") or image_url.startswith("https://"))):
            image_url = DEFAULT_SCRIPT_BANNER_URL

        mg = discord.ui.MediaGallery(discord.MediaGalleryItem(image_url))

        # 6. Container Assembly
        container = discord.ui.Container(
            discord.ui.TextDisplay(header_text),
            discord.ui.Separator(),
            discord.ui.TextDisplay(body_text),
            discord.ui.Separator(),
            row1,
            row2,
            discord.ui.Separator(),
            discord.ui.TextDisplay("**POWERED BY PAYOMBØYZ SCRIPT SEARCH ENGINE • ZERO-RETENTION ARCHITECTURE**"),
            discord.ui.Separator(),
            mg,
            accent_color=discord.Color.from_rgb(0, 255, 204)  # Cyan #00FFCC matching Bomber Panel
        )
        self.add_item(container)

    def _build_embed(self) -> discord.Embed:
        """Legacy embed fallback for backward compatibility."""
        idx = self.page
        if idx >= len(self.items): idx = 0
        s = self.items[idx]
        script_title = s.get("name", "Roblox Script").strip()
        game = s.get("game", "Unknown Game")
        verified = "✅ ยืนยันแล้ว (Safe)" if s.get("verified") else "⚠️ ยังไม่ยืนยัน"
        key = "🔐 มีระบบคีย์" if s.get("has_key") else "🔓 ฟรีไร้คีย์ 100%"
        views = s.get("views", 0)
        created = s.get("created", "")[:10] if s.get("created") else "N/A"
        updated = s.get("updated", "")[:10] if s.get("updated") else "N/A"
        mobile = "📱 รองรับมือถือ (Universal)" if s.get("is_universal") else "💻 PC / Executor ทั่วไป"
        src = "ScriptBlox" if "scriptblox" in s.get("source", "").lower() else ("RScripts" if "rscripts" in s.get("source", "").lower() else "PayomboyZ Vault")

        embed = discord.Embed(
            title=f"📜 {script_title}",
            description=(
                f"> <:payomboyz:1551064225974325318> **ระบบค้นหาสคริปต์อัตโนมัติ (PAYOMBØYZ SCRIPT SEARCH ENGINE)**\n"
                f"> 🎮 **เกม / แมพเป้าหมาย:** `{game}` 🔥\n"
                f"> 📦 **แหล่งข้อมูล:** `{src}` • **หน้าที่:** `{self.page+1}/{len(self.items)}`\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=COLOR_PRIMARY
        )
        embed.add_field(name="🛡️ สถานะความปลอดภัย", value=f"`{verified}`", inline=True)
        embed.add_field(name="🔑 ระบบคีย์", value=f"`{key}`", inline=True)
        embed.add_field(name="👁️ ยอดเข้าชม", value=f"`{views:,} ครั้ง`", inline=True)
        embed.add_field(name="📅 วันที่สร้าง", value=f"`{created}`", inline=True)
        embed.add_field(name="🔄 อัปเดตล่าสุด", value=f"`{updated}`", inline=True)
        embed.add_field(name="📱 อุปกรณ์ที่รองรับ", value=f"`{mobile}`", inline=True)
        code = format_script_code(s)
        if code:
            display_code = code if len(code) <= 950 else f"{code[:940]}..."
            embed.add_field(
                name="📋 Script Execution (คัดลอกไปวางใน Executor ได้ทันที):",
                value=f"```lua\n{display_code}\n```",
                inline=False
            )
        embed.set_footer(
            text=f"PAYOMBØYZ SCRIPT VAULT • หน้าที่ {self.page+1} จากทั้งหมด {len(self.items)} รายการ • แหล่งที่มา: {src}"
        )
        return embed

    async def on_prev(self, interaction: discord.Interaction):
        self.page = max(0, self.page - 1)
        self._rebuild()
        await interaction.response.edit_message(content=None, embed=None, view=self)

    async def on_next(self, interaction: discord.Interaction):
        self.page = min(len(self.items) - 1, self.page + 1)
        self._rebuild()
        await interaction.response.edit_message(content=None, embed=None, view=self)

    async def on_copy(self, interaction: discord.Interaction):
        item = self.items[self.page]
        code = format_script_code(item)
        if code:
            if len(code) <= 1900:
                await interaction.response.send_message(
                    f"```lua\n{code}\n```",
                    ephemeral=False
                )
            else:
                await interaction.response.send_message(
                    f"```{code[:1980]}```",
                    ephemeral=False
                )
        else:
            url = item.get("url", "")
            await interaction.response.send_message(
                f"🔗 ดูสคริปต์ได้ที่: {url}" if url else "❌ ไม่พบโค้ดสคริปต์",
                ephemeral=True
            )

    async def on_deobf(self, interaction: discord.Interaction):
        item = self.items[self.page]
        await interaction.response.defer(ephemeral=False)

        script_name = item.get("name", "Script")
        game_name = item.get("game", "Roblox Game")

        status_msg = await interaction.followup.send(
            f"⏳ **[PAYOMBØYZ DEOBFUSCATOR]** กำลังแกะสคริปต์ `{script_name}` ({game_name})\n"
            f"• ตรวจสอบโครงสร้าง Loader Spying & PlaceId Routing...\n"
            f"• กำลังประมวลผลผ่าน Multi-Engine Deobfuscator...",
            ephemeral=False
        )

        try:
            from utils.script_deobf_bridge import DEOBF_BRIDGE
            res = await DEOBF_BRIDGE.execute_full_pipeline(interaction, item)

            if res.get("success"):
                rep_ch_id = res.get("report_channel_id")
                report_msg = res.get("report_msg")
                jump_link = report_msg.jump_url if report_msg else f"https://discord.com/channels/{interaction.guild_id}/{rep_ch_id}"
                
                success_embed = discord.Embed(
                    title="✅ ถอดรหัสและตรวจสอบซอร์สโค้ดสำเร็จ 100%!",
                    description=(
                        f"🎮 **เกม / แมพ:** `{res.get('game_title')}`\n"
                        f"📊 **ขนาดซอร์สโค้ด:** `{res.get('lines'):,} บรรทัด` ({res.get('elapsed'):.2f}s)\n"
                        f"🛡️ **การตรวจสอบแมพ:** `{res['verification']['details']}`\n\n"
                        f"📍 **ห้องรายงานผล:** สคริปต์และไฟล์ `.lua` ถูกส่งไปยังห้อง <#{rep_ch_id}> เรียบร้อยแล้ว!\n\n"
                        f"👉 **[คลิกที่นี่เพื่อไปดูและดาวน์โหลดสคริปต์]({jump_link})**"
                    ),
                    color=COLOR_SUCCESS
                )
                success_embed.set_footer(text="PAYOMBØYZ Centralized Deobfuscator • 100% Deterministic Recovery")
                await status_msg.edit(content=None, embed=success_embed)
            else:
                await status_msg.edit(content=f"❌ การถอดรหัสไม่สำเร็จ: {res.get('error', 'Unknown Error')}")
        except Exception as e:
            await status_msg.edit(content=f"❌ เกิดข้อผิดพลาดในระบบ Deobfuscate Bridge: {e}")


class ScriptSearchCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.script_channel_id = None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # ไม่ตอบบอทเอง / ไม่ตอบใน DM
        if message.author.bot: return
        if message.guild is None: return

        text = message.content.strip()
        if not text: return

        # ตรวจสอบว่าเซิร์ฟเวอร์เปิดโหมดค้นหาสคริปต์หรือไม่
        if guild_config is not None and message.guild:
            if not guild_config.is_script_enabled(message.guild.id):
                return

        # ตรวจสอบช่อง: ตอบเฉพาะช่องสคริปต์ที่ตั้งไว้ (script_channel จาก /setup)
        allowed_channel = None
        if guild_config is not None and message.guild:
            allowed_channel = guild_config.get_script_channel(message.guild.id)
        if allowed_channel is not None and message.channel.id != allowed_channel:
            return
        if allowed_channel is None:
            return  # ยังไม่ตั้งช่อง → ไม่ตอบที่ไหนเลย

        # ถ้าเป็นคำสั่งที่มี / ไม่ต้องตอบ (ให้ slash command จัดการ)
        if text.startswith("/"): return
        if len(text) < 2: return

        # ดึงจาก Multi-Source (ScriptBlox + RScripts + Local) ด้วย search_with_fallback
        rscript_items = []
        try:
            from utils.script_api import search_with_fallback
            rscript_items = await search_with_fallback(text)
        except Exception as e:
            print(f"[ScriptSearchListener] Search error: {e}")

        # ถ้ายังไม่เจอ ลองค้นจากฐานข้อมูลในตัวเพิ่มเติม
        if not rscript_items:
            rscript_items = [
                r for r in get_all()
                if text.lower() in r.get("name", "").lower() or text.lower() in r.get("game", "").lower()
            ]

        # ตอบเมื่อไม่พบผลลัพธ์
        if not rscript_items:
            embed = discord.Embed(
                title=f"🔍 ไม่พบสคริปต์สำหรับ \"{text}\"",
                description=f"💡 ลองค้นหาด้วยชื่อเกมภาษาอังกฤษ หรือฟังก์ชัน เช่น `autofarm`, `trade`\nคำสั่งสำรอง: `/script-search query:{text}`",
                color=COLOR_ERROR
            )
            await message.reply(embed=embed)
            return

        # มีผลลัพธ์ → แสดงการ์ด Discord Components V2 Panel หรูหราขนาดใหญ่
        view = ScriptCardView(rscript_items, 0, message.author.id)
        try:
            await message.reply(view=view)
        except Exception as e:
            print(f"[ScriptSearchListener] Failed to reply with Components V2 LayoutView: {e}")
            await message.reply(embed=view._build_embed(), view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(ScriptSearchCog(bot))
