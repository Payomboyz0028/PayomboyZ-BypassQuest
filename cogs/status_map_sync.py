"""
PAYOMBØYZ Live Map Status & Script Hub Synchronizer Cog (Elite Cyber HUD Edition)
Automatically syncs active supported Roblox games/maps from:
https://payomboyzcreative.online/api/v1/games
Directly into Discord status channel: # status-แมพที่รองรับ (1549820106287349832)
"""
import io
import os
import time
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from typing import Optional, List, Dict, Any

from utils.config_manager import guild_config

API_GAMES_URL = "https://payomboyzcreative.online/api/v1/games"
DEFAULT_STATUS_CHANNEL_ID = 1549820106287349832  # # status-แมพที่รองรับ
DEFAULT_GUILD_ID = 1549398019970179152

SHOWCASE_IMAGE_CANDIDATES = [
    r"d:\Deobfuscate\Lerning\PAYOMBØYZ VIP vs VVIP Gaming Showcase.png",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "PAYOMBØYZ VIP vs VVIP Gaming Showcase.png")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Lerning", "PAYOMBØYZ VIP vs VVIP Gaming Showcase.png")),
]

def _get_showcase_image_path() -> Optional[str]:
    for p in SHOWCASE_IMAGE_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


# ─────────────────────────────────────────────────────────────
# Dropdown Select Menu for Deep Info
# ─────────────────────────────────────────────────────────────
class StatusMapSelect(discord.ui.Select):
    def __init__(self, vip_count: int = 19, vvip_count: int = 12):
        options = [
            discord.SelectOption(
                label=f"🤴 ข้อมูลสิทธิ์ VIP Package ({vip_count} แมพ)",
                value="opt_vip",
                description="สิทธิ์ระดับมาตรฐาน ฟาร์มเวล ไต่อันดับ ปลดล็อคไอเทม",
                emoji="👑"
            ),
            discord.SelectOption(
                label=f"🧙 ข้อมูลสิทธิ์ VVIP Elite ({vvip_count} แมพใหม่ + 19 VIP)",
                value="opt_vvip",
                description="สิทธิ์ขั้นสูงสุด เข้าได้ครบทุกแมพ 100% พร้อมฟังก์ชันลับ",
                emoji="🔥"
            ),
            discord.SelectOption(
                label="🛠️ ข้อมูลเครื่องมือทั้งหมด (11 ระบบ)",
                value="opt_tools",
                description="AI Dumper, Obfuscator, Bypass, Auto Quest, Cloner ฯลฯ",
                emoji="⚙️"
            ),
            discord.SelectOption(
                label="🔄 วิธีกดรีเซ็ต HWID และเงื่อนไข",
                value="opt_hwid",
                description="ตรวจสอบโควตาการรีเซ็ตเครื่อง และวิธีย้ายอุปกรณ์",
                emoji="🔄"
            ),
        ]
        super().__init__(
            placeholder="⚡ เลือกเพื่อดูคำสั่ง & ข้อมูลเจาะลึกของแต่ละแพ็กเกจ...",
            min_values=1,
            max_values=1,
            custom_id="status_map:select_info",
            options=options,
            row=0
        )

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]

        if selected == "opt_vip":
            embed = discord.Embed(
                title="🤴 VIP Package • สิทธิประโยชน์ & ข้อมูลการใช้งาน",
                description=(
                    "> 💡 **ระดับ:** `VIP Access` (เล่นได้ 19 แมพหลัก)\n"
                    "> 🎮 **เกมที่รองรับ:** Blox Fruits, Fisch, Blade Ball, Capybara, AOT, Ride a Pet, Dungeon Lootr, ฯลฯ\n\n"
                    "**🔑 ขั้นตอนการเริ่มใช้งาน:**\n"
                    "1. ซื้อหรือรับคีย์ VIP จากทีมงาน\n"
                    "2. นำคีย์ไปกดรับสคริปต์ที่ <#1549827759457570906>\n"
                    "3. รันโค้ด Loader บน Executor ที่รองรับ (Delta, Codex, Arceus, Wave, Solara)\n"
                    "4. ระบบจะตรวจสอบ HWID และโหลด UI อัตโนมัติในเกม"
                ),
                color=0x3B82F6
            )
            embed.set_footer(text="PAYOMBØYZ VIP Architecture • 60 FPS Optimized")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif selected == "opt_vvip":
            embed = discord.Embed(
                title="🧙 VVIP Elite Package • ข้อมูลสิทธิ์ขั้นสูงสุด",
                description=(
                    "> 🔥 **ระดับ:** `VVIP Elite Pass` (เล่นได้ครบ 31 แมพ ทั้งหมด 100%)\n"
                    "> 🎮 **เกม Exclusive:** Build An Ant Empire, My Anime Mine, Roll Anime to Fight, Mine a Mountain, MM2, Slayers 2, ฯลฯ\n\n"
                    "**⚡ ฟีเจอร์พิเศษสำหรับ VVIP:**\n"
                    "• สิทธิ์เข้าถึงแมพใหม่ล่าสุดก่อนใคร (Day-One Access)\n"
                    "• ฟังก์ชัน Fast-Mode ข้ามแอนิเมชัน ลดอาการกระตุก\n"
                    "• มีโควตารีเซ็ต HWID สูงสุดต่อวัน\n"
                    "• ปลดล็อคระบบสคริปต์แยกย่อยตาม Sub-Places ครบทุกโซนดันเจี้ยน"
                ),
                color=0xA855F7
            )
            embed.set_footer(text="PAYOMBØYZ VVIP Elite Tier • Zero Refusal")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif selected == "opt_tools":
            embed = discord.Embed(
                title="🛠️ PAYOMBØYZ Tools & AI Ecosystem (11 ระบบ)",
                description=(
                    "ศูนย์รวมเครื่องมืออัตโนมัติประจำคอมมูนิตี้:\n\n"
                    "• 🤖 **AI Script HUB** ➔ <#1550534429024456844> (ดัมพ์แมพ Roblox ทั้ง Place)\n"
                    "• 🧠 **Deepseek AI Bot** ➔ <#1550220801297490061> (AI เขียน/แก้สคริปต์ 24 ชม.)\n"
                    "• 🪐 **PAYOMBØYZ Bypass** ➔ <#1555389925615079484> (ข้ามโฆษณาลิงก์คีย์)\n"
                    "• 🛡️ **Code Obfuscate** ➔ <#1559919442995978240> (เข้ารหัส VM ป้องกันสคริปต์)\n"
                    "• 🔍 **Code Deobfuscate** ➔ <#1557945565491236954> (แกะและกู้คืนโครงสร้างโค้ด)\n"
                    "• 🌐 **Dynamic Web Log** ➔ <#1552710426469601281> (เว็บบันทึกประวัติ)\n"
                    "• 🔮 **Auto Quest Discord** ➔ <#1561037352778858516> (ทำเควสต์ดิสคอร์ดออโต้)\n"
                    "• 📜 **Web Script Search** ➔ <#1555406284482683025> (ค้นหาสคริปต์ทั่วโลก)\n"
                    "• 🥶 **Website Cloner** ➔ <#1559720186955956317> (โคลนเว็บ 1:1)\n"
                    "• 🤓 **Discord Cloner** ➔ <#1561024969549291590> (โคลนเซิร์ฟดิสคอร์ด)\n"
                    "• 🎭 **Jailbreak AI** ➔ <#1561971491740975245> (ปลดล็อคข้อจำกัด AI)"
                ),
                color=0x00F0FF
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif selected == "opt_hwid":
            embed = discord.Embed(
                title="🔄 กฎและข้อกำหนดการรีเซ็ต HWID (Hardware ID)",
                description=(
                    "> 📌 **ห้องดำเนินการ:** <#1550444661703975002>\n\n"
                    "**ข้อควรรู้:**\n"
                    "• สคริปต์ผูกกับอุปกรณ์เครื่องแรกที่รันคีย์\n"
                    "• เมื่อเปลี่ยนมือถือ/คอม ให้ไปที่ห้อง <#1550444661703975002> แล้วเลือกโปรเจกต์ ใส่คีย์เพื่อยืนยัน\n"
                    "• โควตารีเซ็ตจะถูกจำกัดต่อวันเพื่อป้องกันการแชร์คีย์กับผู้อื่น\n"
                    "• หากติด Cooldown ระบบจะแจ้งเวลาที่สามารถรีเซ็ตได้ให้อัตโนมัติ"
                ),
                color=0x10B981
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


# ─────────────────────────────────────────────────────────────
# Persistent View for Map Status Panel
# ─────────────────────────────────────────────────────────────
class StatusMapPersistentView(discord.ui.View):
    """Survives bot restarts. Provides one-click shortcuts & manual refresh."""

    def __init__(self, vip_count: int = 19, vvip_count: int = 12):
        super().__init__(timeout=None)
        # Dropdown row 0
        self.add_item(StatusMapSelect(vip_count=vip_count, vvip_count=vvip_count))

        # Action Buttons row 1 (Max 5 buttons per row)
        self.add_item(discord.ui.Button(
            label="ซื้อสคริปต์ (Shop)",
            style=discord.ButtonStyle.link,
            url="https://discord.com/channels/1549398019970179152/1549819642208460970",
            emoji="🛒",
            row=1
        ))
        self.add_item(discord.ui.Button(
            label="ใส่คีย์ / Redeem",
            style=discord.ButtonStyle.link,
            url="https://discord.com/channels/1549398019970179152/1549827759457570906",
            emoji="🔑",
            row=1
        ))
        self.add_item(discord.ui.Button(
            label="AI Dump Map",
            style=discord.ButtonStyle.link,
            url="https://discord.com/channels/1549398019970179152/1550534429024456844",
            emoji="🤖",
            row=1
        ))
        self.add_item(discord.ui.Button(
            label="รีเซ็ต HWID",
            style=discord.ButtonStyle.link,
            url="https://discord.com/channels/1549398019970179152/1550444661703975002",
            emoji="🔄",
            row=1
        ))

    @discord.ui.button(
        label="รีเฟรชสถานะสด",
        style=discord.ButtonStyle.secondary,
        custom_id="status_map:refresh",
        emoji="⚡",
        row=2
    )
    async def btn_refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        cog: Optional[StatusMapSyncCog] = interaction.client.get_cog("StatusMapSyncCog")
        if not cog:
            await interaction.followup.send("⚠️ ไม่พบระบบ StatusMapSyncCog", ephemeral=True)
            return

        guild_id = interaction.guild_id or DEFAULT_GUILD_ID
        success, msg = await cog.sync_status_channel(guild_id)
        if success:
            await interaction.followup.send(f"✅ **รีเฟรชสถานะสดสำเร็จ:** {msg}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ **เกิดข้อผิดพลาด:** {msg}", ephemeral=True)


# ─────────────────────────────────────────────────────────────
# Status Map Sync Cog
# ─────────────────────────────────────────────────────────────
class StatusMapSyncCog(commands.Cog):
    """Syncs live Roblox maps and tools into # status-แมพที่รองรับ."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cached_games_hash = ""

    async def cog_load(self):
        if not self.auto_sync_loop.is_running():
            self.auto_sync_loop.start()

    def cog_unload(self):
        self.auto_sync_loop.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        # Trigger an initial sync 10 seconds after bot is fully ready
        await discord.utils.sleep_until(discord.utils.utcnow() + discord.utils.datetime.timedelta(seconds=10))
        try:
            await self.sync_status_channel(DEFAULT_GUILD_ID)
        except Exception as e:
            print(f"[StatusMapSync] Initial boot sync error: {e}")

    # 5-minute background auto-sync task
    @tasks.loop(minutes=5)
    async def auto_sync_loop(self):
        try:
            await self.sync_status_channel(DEFAULT_GUILD_ID)
        except Exception as e:
            print(f"[StatusMapSync] Auto-sync loop warning: {e}")

    @auto_sync_loop.before_loop
    async def before_auto_sync(self):
        try:
            await self.bot.wait_until_ready()
        except Exception:
            pass

    async def fetch_live_games(self) -> List[Dict[str, Any]]:
        """Fetch real-time games array from payomboyzcreative.online."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(API_GAMES_URL, timeout=aiohttp.ClientTimeout(total=8)) as res:
                    if res.status == 200:
                        data = await res.json()
                        games = data.get("games", [])
                        if isinstance(games, list) and len(games) > 0:
                            return games
        except Exception as e:
            print(f"[StatusMapSync] Live API fetch error: {e}. Falling back to default catalog.")

        # Fallback to local files if website is momentarily unreachable
        try:
            catalog_file = r"C:\Users\PayomboyZ\Desktop\Key-Customer\payomboyz-whitelist-repo\src\data\games_catalog.js"
            if os.path.exists(catalog_file):
                import re
                with open(catalog_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                names = re.findall(r"name:\s*['\"]([^'\"]+)['\"]", content)
                pkgs = re.findall(r"package:\s*['\"]([^'\"]+)['\"]", content)
                parsed = []
                for idx in range(min(len(names), len(pkgs))):
                    parsed.append({"name": names[idx], "package": pkgs[idx], "status": "online"})
                if parsed:
                    return parsed
        except Exception:
            pass

        return []

    def build_status_embed(self, games: List[Dict[str, Any]]) -> discord.Embed:
        """Constructs the ultra-wide, right-aligned status HUD Embed without 'online' text."""
        EMOJI_ONLINE = "<a:ww:1563742554703401084>"
        EMOJI_OFFLINE = "<a:emoji_48:1563742561581924392>"

        def clean_game_name(raw: str) -> str:
            name = raw.strip()
            for em in ['🎃', '⛏️', '🗡️', '🔥', '✨', '🎂', '🐺', '🍁', '🌱', '🐜', '🎯']:
                name = name.replace(em, '').strip()
            if name.startswith('[') and ']' in name:
                tag = name[name.find('[')+1:name.find(']')].strip()
                rest = name[name.find(']')+1:].strip()
                if rest:
                    name = f"{rest} [{tag}]"
            if name.startswith('(学乱)'):
                name = "Gakuran [学乱]"
            name = name.replace("HALLOWEEN   Dungeon Quest Reborn", "Dungeon Quest Reborn [EVENT]")
            name = name.replace("HALLOWEEN  Dungeon Quest Reborn", "Dungeon Quest Reborn [EVENT]")
            return name.strip()

        def build_game_row(icon: str, raw_name: str, is_online: bool = True, width: int = 26) -> str:
            cleaned = clean_game_name(raw_name)
            if len(cleaned) > width:
                cleaned = cleaned[:width-2] + '..'
            padded = f"{cleaned:<{width}}"
            status_icon = EMOJI_ONLINE if is_online else EMOJI_OFFLINE
            return f"{icon} `{padded}` {status_icon}"

        def build_tool_row(icon: str, tool_name: str, is_online: bool = True, width: int = 26) -> str:
            if len(tool_name) > width:
                tool_name = tool_name[:width-2] + '..'
            padded = f"{tool_name:<{width}}"
            status_icon = EMOJI_ONLINE if is_online else EMOJI_OFFLINE
            return f"{icon} `{padded}` {status_icon}"

        vip_lines = []
        vvip_lines = []

        for g in games:
            raw_name = g.get("name", "Unknown Game")
            is_on = g.get("status", "online") in ["online", "active"]
            if g.get("package") == "VIP":
                vip_lines.append(build_game_row('▸', raw_name, is_on, 26))
            elif g.get("package") == "VVIP":
                vvip_lines.append(build_game_row('⭐', raw_name, is_on, 26))

        # Industrial Tools aligned
        tools_data = [
            ("🪐", "PAYOMBØYZ Bypass", True),
            ("🛡️", "Sentinel Obfuscator v3", True),
            ("🔍", "Bytecode Deobfuscator", True),
            ("🔮", "Auto Quest Discord Bot", True),
            ("🤖", "AI Script HUB & Spy", True),
            ("🧠", "Deepseek AI Assistant", True),
            ("🌐", "Dynamic Multi WebLog", True),
            ("📜", "Web Script Search Engine", True),
            ("🥶", "Website Cloner Studio", True),
            ("🤓", "Discord Server Cloner", True),
            ("🎭", "Uncensored Jailbreak AI", True)
        ]
        tool_rows = [build_tool_row(ic, nm, on, 26) for ic, nm, on in tools_data]

        desc = (
            "```ansi\n"
            "\u001b[1;33m[PBG SENTINEL v3.7]\u001b[0m  \u001b[1;32m● ALL CLOUD ENGINES ONLINE\u001b[0m\n"
            f"\u001b[1;30mDATABASE: payomboyzcreative.online | ACTIVE TARGETS: {len(games)} MAPS\u001b[0m\n"
            "```\n"
            "╔═════════════════════════════════════════════════════════╗\n"
            "  🛒 **สั่งซื้อสคริปต์ (Shop)** ➔ <#1549819642208460970>\n"
            "  🔑 **รับสคริปต์ (Redeem)** ➔ <#1549827759457570906>\n"
            "  🤖 **AI Spy & Dump MAP** ➔ <#1550534429024456844>\n"
            "  🔄 **รีเซ็ตสิทธิ์ HWID (24 ชม.)** ➔ <#1550444661703975002>\n"
            "╚═════════════════════════════════════════════════════════╝"
        )

        embed = discord.Embed(
            title="<a:emojigg_jhu:1551032228631281736>  สถานะ Script  •  PAYOMBØYZ HUB  <:payomboyz:1551064225974325318>",
            description=desc,
            color=0xF1C40F  # Warm Gold
        )

        # VIP Package
        if len(vip_lines) > 10:
            p1 = "\n".join(vip_lines[:10])
            p2 = "\n".join(vip_lines[10:])
            embed.add_field(
                name=f"<a:kacchancheer:1551026067400294520>  **VIP PACKAGE (ส่วนที่ 1)**  —  *`10 แมพ`*",
                value=p1,
                inline=False
            )
            embed.add_field(
                name=f"<a:kacchancheer:1551026067400294520>  **VIP PACKAGE (ส่วนที่ 2)**  —  *`{len(vip_lines)-10} แมพ`*",
                value=p2,
                inline=False
            )
        else:
            v_val = "\n".join(vip_lines) if vip_lines else f"- กำลังโหลดข้อมูล...  {EMOJI_ONLINE}"
            embed.add_field(
                name=f"<a:kacchancheer:1551026067400294520>  **VIP Package**  *({len(vip_lines)} แมพ)*",
                value=v_val,
                inline=False
            )

        # VVIP Package
        vv_val = "\n".join(vvip_lines) if vvip_lines else f"- กำลังโหลดข้อมูล...  {EMOJI_ONLINE}"
        embed.add_field(
            name=f"<a:dekucheer:1551025578470281248>  **VVIP ELITE PACKAGE**  —  *`{len(vvip_lines)} แมพ Exclusive + VIP ทั้งหมด`*",
            value=vv_val,
            inline=False
        )

        # PAYOMBØYZ Industrial Tools
        embed.add_field(
            name="<:pbg_aiscript:1551062845339471933>  **PAYOMBØYZ INDUSTRIAL TOOLS (11 ระบบ)**",
            value="\n".join(tool_rows),
            inline=False
        )

        # Reset HWID
        hwid_val = (
            "> 🔄 **ช่องทางปลดล็อค HWID:** <#1550444661703975002>\n"
            "*(ระบบปลดล็อคเครื่องอัตโนมัติ 24 ชม. ตรวจสอบโควตาและรีเซ็ตทันที)*"
        )
        embed.add_field(
            name="<a:Happy:1551070884490518579>  **HARDWARE & LICENSE LIFECYCLE**  <a:hasake3:1551070932213440614>",
            value=hwid_val,
            inline=False
        )

        embed.set_image(url="attachment://showcase.png")
        now_str = time.strftime("%d/%m/%Y %H:%M:%S")
        embed.set_footer(text=f"PAYOMBØYZ Industrial Matrix • https://payomboyzcreative.online • อัปเดตล่าสุด: {now_str}")
        return embed

    async def sync_status_channel(self, guild_id: int) -> tuple[bool, str]:
        """Performs live sync to the target status channel."""
        cfg = guild_config.get(guild_id)
        status_ch_id = cfg.get("status_channel_id") or DEFAULT_STATUS_CHANNEL_ID
        status_msg_id = cfg.get("status_message_id")

        channel = self.bot.get_channel(status_ch_id)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(status_ch_id)
            except Exception as e:
                return False, f"ไม่พบห้อง Status (ID: {status_ch_id}): {e}"

        # Fetch live games
        games = await self.fetch_live_games()
        vip_cnt = len([g for g in games if g.get("package") == "VIP"])
        vvip_cnt = len([g for g in games if g.get("package") == "VVIP"])

        embed = self.build_status_embed(games)
        view = StatusMapPersistentView(vip_count=vip_cnt, vvip_count=vvip_cnt)

        # Check showcase image
        img_path = _get_showcase_image_path()

        # Case 1: Existing message ID saved — attempt to edit
        if status_msg_id:
            try:
                msg = await channel.fetch_message(int(status_msg_id))
                if msg:
                    if img_path and os.path.exists(img_path):
                        with open(img_path, "rb") as f:
                            file = discord.File(f, filename="showcase.png")
                            await msg.edit(embed=embed, view=view, attachments=[file])
                    else:
                        await msg.edit(embed=embed, view=view)
                    return True, f"อัปเดต Cyber HUD สำเร็จ (Msg ID: {status_msg_id}, แมพ: {len(games)} แมพ)"
            except discord.NotFound:
                status_msg_id = None
            except Exception as e:
                print(f"[StatusMapSync] Edit error, re-creating message: {e}")
                status_msg_id = None

        # Case 2: Post fresh message and persist ID
        try:
            if img_path and os.path.exists(img_path):
                with open(img_path, "rb") as f:
                    file = discord.File(f, filename="showcase.png")
                    new_msg = await channel.send(file=file, embed=embed, view=view)
            else:
                new_msg = await channel.send(embed=embed, view=view)

            # Persist message ID in guild_configs
            cfg["status_channel_id"] = status_ch_id
            cfg["status_message_id"] = new_msg.id
            guild_config.configs[str(guild_id)] = cfg
            guild_config._save()

            return True, f"ส่งข้อความใหม่สำเร็จ (Msg ID: {new_msg.id}, แมพ: {len(games)} แมพ)"
        except Exception as e:
            return False, f"ไม่สามารถส่งข้อความเข้าห้อง: {e}"

    # ─────────────────────────────────────────────────────────────
    # Slash Command: /status_panel
    # ─────────────────────────────────────────────────────────────
    status_group = app_commands.Group(
        name="status_panel",
        description="จัดการแผงแสดงสถานะแมพที่รองรับ (Live Auto-Sync จากเว็บไซต์)",
        default_permissions=discord.Permissions(administrator=True)
    )

    @status_group.command(name="sync", description="🔄 ซิงค์ข้อมูลแมพจากเว็บไซต์เข้าห้อง Status ทันที")
    async def cmd_sync(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild_id or DEFAULT_GUILD_ID
        success, msg = await self.sync_status_channel(guild_id)
        if success:
            await interaction.followup.send(f"✅ **ซิงค์สถานะแมพสำเร็จ!**\n{msg}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ **เกิดข้อผิดพลาดในการซิงค์:**\n`{msg}`", ephemeral=True)

    @status_group.command(name="post", description="📌 ติดตั้งแผงแสดงสถานะแมพใหม่ในห้องนี้")
    @app_commands.describe(channel="ห้องที่ต้องการให้แสดงสถานะแมพ (ถ้าไม่ระบุ = ห้องปัจจุบัน)")
    async def cmd_post(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        await interaction.response.defer(ephemeral=True)
        target_ch = channel or interaction.channel
        guild_id = interaction.guild_id or DEFAULT_GUILD_ID

        cfg = guild_config.get(guild_id)
        cfg["status_channel_id"] = target_ch.id
        cfg["status_message_id"] = None  # Force fresh post
        guild_config.configs[str(guild_id)] = cfg
        guild_config._save()

        success, msg = await self.sync_status_channel(guild_id)
        if success:
            await interaction.followup.send(f"✅ **ติดตั้งแผงสถานะใน {target_ch.mention} เรียบร้อย!**\n{msg}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ **เกิดข้อผิดพลาด:**\n`{msg}`", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(StatusMapSyncCog(bot))
    print("  [OK] Loaded: cogs.status_map_sync (Elite Cyber HUD)")
