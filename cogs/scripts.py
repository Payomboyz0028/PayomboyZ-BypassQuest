"""
Scripts Cog — /rscript, /bloxscript, /script-search, /game
ค้นหาสคริปต์ Roblox ตามชื่อเกม/แมพ พร้อมระบบแนะนำ
"""
import os
import json
import re
import discord
from discord import app_commands
from discord.ext import commands
from config import COLOR_PRIMARY, COLOR_SUCCESS, COLOR_ERROR, COLOR_INFO
from utils.config_manager import guild_config

try:
    from utils.script_api import script_api, search_with_fallback
except ImportError:
    script_api = None
    search_with_fallback = None

try:
    from utils.gemini_search import gemini
except ImportError:
    gemini = None

try:
    from cogs.script_search_listener import ScriptCardView
except ImportError:
    try:
        from .script_search_listener import ScriptCardView
    except ImportError:
        ScriptCardView = None

SCRIPT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "scripts.json")

# Emoji map for script types
TYPE_EMOJI = {
    "farm": "🌾", "admin": "👑", "aimbot": "🎯", "mod": "🔧",
    "esp": "👁️", "tool": "🛠️", "raid": "⚔️", "hunt": "🏹",
    "stat": "📊", "shop": "🛒", "quest": "📜", "dungeon": "🏚️",
    "script": "📜"
}

# Game emoji map
GAME_EMOJI = {
    "blox fruits": "🌊", "blox fruit": "🌊",
    "jailbreak": "🚔", "arsenal": "🔫",
    "phantom forces": "🎯", "bedwars": "⚔️",
    "murder mystery 2": "🔪", "mm2": "🔪",
    "doors": "🚪", "da hood": "💀",
    "pet simulator": "🐾", "tower defense": "🏰",
    "adopt me": "🐶", "fisch": "🐟",
    "king legacy": "🏴‍☠️", "grand piece": "⛵",
    "project slayers": "👹", "blox legend": "🌟",
    "a piece": "⛵", "anime fighters": "💥",
    "anime vanguards": "⚡", "natural disaster": "🌋",
    "tower of hell": "🔥", "universal": "🌐"
}

def load_db():
    if os.path.exists(SCRIPT_DB_PATH):
        try:
            with open(SCRIPT_DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def get_all_scripts():
    """คืนค่ารายการสคริปต์ทั้งหมดแบบ flat list"""
    db = load_db()
    results = []
    for cat, scripts in db.items():
        for s in scripts:
            results.append({**s, "source": cat})
    return results

def get_game_emoji(game: str) -> str:
    """หา emoji สำหรับชื่อเกม"""
    gl = game.lower()
    for key, emoji in GAME_EMOJI.items():
        if key in gl or gl in key:
            return emoji
    return "🎮"

def search_scripts(query: str, use_gemini: bool = True) -> list:
    """ค้นหาสคริปต์แบบ fuzzy — ใช้ Gemini ช่วยขยายคำค้นหา + ครอบคลุมแมพที่คนไม่เล่น"""
    # Gemini ขยายคำค้นหา
    expanded = []
    if use_gemini:
        try:
            import asyncio
            # ต้องใช้ loop ใหม่ถ้ายังไม่ได้สร้าง
            loop = asyncio.get_event_loop()
            # ใช้ synchronous call wrapper
            gemini_result = asyncio.run(gemini.expand_query(query))
            expanded = gemini_result.get("alt_searches", [])
        except Exception:
            expanded = [query, f"{query} farm", f"{query} script"]
    else:
        expanded = [query, f"{query} farm", f"{query} script"]

    all_scripts = get_all_scripts()
    q = query.lower().strip()
    results = []
    seen = set()

    # ค้นหาแบบ match จากคำหลัก + คำขยาย + RScript เป็นหลัก
    for s in all_scripts:
        if s.get("source") == "rscript":
            # RScript ให้คะแนนสูง
            pass

        for term in [q] + expanded:
            term = term.lower()
            name = s.get("name", "").lower()
            game = s.get("game", "").lower()
            desc = s.get("description", "").lower()
            stype = s.get("type", "").lower()

            if (term in name or term in game or term in desc or term in stype):
                key = s.get("name", "_") + s.get("url", "_")
                if key not in seen:
                    seen.add(key)
                    results.append(s)
                break

    # เรียงลำดับ: RScript มาก่อน แล้วตามด้วยเริ่มต้นจากเกมที่ตรง
    def sort_key(s):
        is_rscript = 0 if s.get("source") == "rscript" else 1
        is_obscure = 0 if s.get("game") and s.get("game").lower() in ["tower defense simulator", "anime fighters simulator", "natural disaster survival", "fisch", "anime vanguards", "grand piece online", "project slayers", "a piece", "adopt me!", "tower of hell"] else 1
        return (is_rscript, is_obscure, s.get("name", "").lower())

    results.sort(key=sort_key)
    return results


# ─────────────────────────────────────────────
# Scripts Cog
# ─────────────────────────────────────────────
class ScriptsCog(commands.Cog):
    """ค้นหาสคริปต์ Roblox — /rscript, /bloxscript, /script-search, /games"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """ตรวจสอบว่าเซิร์ฟเวอร์นี้เปิดโหมดสคริปต์หรือไม่"""
        if interaction.guild and not guild_config.is_script_enabled(interaction.guild.id):
            await interaction.response.send_message(
                "❌ **คำสั่งนี้ถูกปิดการใช้งานในเซิร์ฟเวอร์นี้**\n"
                "• ปัจจุบันเซิร์ฟเวอร์ถูกตั้งค่าเป็นโหมด `🔓 Bypass Only`\n"
                "• แอดมินสามารถเปิดใช้งานได้โดยใช้คำสั่ง `/setup mode:full` หรือ `/setup mode:script`",
                ephemeral=True
            )
            return False
        return True

    # ── Autocomplete helper ──
    async def _game_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        """แนะนำชื่อเกมขณะพิมพ์"""
        all_scripts = get_all_scripts()
        games = set()
        for s in all_scripts:
            g = s.get("game", "")
            if g:
                games.add(g)

        c = current.lower()
        matches = sorted([g for g in games if c in g.lower()])[:20]
        emoji_list = ["🎮", "⚔️", "🌊", "🏴‍☠️", "🔫", "🗡️", "🛡️", "🐉", "🌟", "🎯",
                      "💎", "🚀", "🔥", "⚡", "🍀", "🎲", "🎪", "🏰", "🌋", "🐟"]
        return [
            app_commands.Choice(name=f"{emoji_list[i % len(emoji_list)]} {g}", value=g)
            for i, g in enumerate(matches)
        ]

    # ── /rscript ──
    @app_commands.command(name="rscript", description="🔴 ค้นหาสคริปต์ RScript จาก API จริง (rscripts.net)")
    @app_commands.describe(query="ชื่อเกม, แมพ, หรือชื่อสคริปต์ที่ต้องการค้นหา")
    @app_commands.autocomplete(query=_game_autocomplete)
    async def rscript_cmd(self, interaction: discord.Interaction, query: str):
        """ค้นหาสคริปต์ RScript จาก rscripts.net API จริง"""
        await interaction.response.defer(ephemeral=False)

        # เรียก RScript API จริง
        rscript_items = []
        if script_api is not None:
            try:
                rscript_items = await script_api.search_rscripts(query, limit=20)
            except Exception:
                rscript_items = []
        
        # If RScripts API returned nothing (e.g. 502/401/down), fallback to search_with_fallback
        if not rscript_items:
            try:
                from utils.script_api import search_with_fallback
                rscript_items = await search_with_fallback(query)
            except Exception:
                rscript_items = [r for r in search_scripts(query) if r.get("source") == "rscript"]

        # ถ้าไม่เจอใน API และในฐานข้อมูล
        if not rscript_items:
            msg = f"**ไม่พบสคริปต์ RScript สำหรับ `{query}`**\n"
            msg += "\n💡 ลองใช้ `/script-search` เพื่อค้นหาทุกแหล่ง (Local + ScriptBlox + RScript)"
            embed = discord.Embed(
                title="🔴 ไม่พบสคริปต์ RScript",
                description=msg,
                color=COLOR_ERROR
            )
            await interaction.followup.send(embed=embed)
        if ScriptCardView and rscript_items:
            view = ScriptCardView(rscript_items, 0, interaction.user.id)
            await interaction.followup.send(embed=view._build_embed(), view=view)
            return

        # สร้าง embed จากผล API
        embed = discord.Embed(
            title=f"🔴 RScript Results — \"{query}\"",
            description=f"พบ `{len(rscript_items)}` รายการจาก **rscripts.net API**",
            color=COLOR_PRIMARY
        )
        for s in rscript_items[:10]:
            type_emoji = TYPE_EMOJI.get(s.get("type", ""), "📦")
            source_tag = "🔴 RS"
            game = s.get("game", "Unknown")
            desc = s.get("description", "")[:100]
            url = s.get("url", "")
            value = f"{source_tag} | 🎮 **{game}** | `{s.get('executor', 'krnl, synapse, fluxus')}`\n{desc}"
            if url:
                value += f"\n🔗 `{url[:80]}{'...' if len(url) > 80 else ''}`"
            embed.add_field(
                name=f"{type_emoji} {s['name']}",
                value=value,
                inline=False
            )
        if len(rscript_items) > 10:
            embed.set_footer(text=f"แสดง 10 จาก {len(rscript_items)} รายการ • ใช้คำค้นเจาะจงกว่านี้")
        else:
            embed.set_footer(text=f"พบ {len(rscript_items)} รายการ • ใช้ `/script-search` เพื่อค้นหาทุกแหล่ง")
        await interaction.followup.send(embed=embed)

    # ── /bloxscript ──
    @app_commands.command(name="bloxscript", description="🟦 ค้นหาสคริปต์ Blox Script — Blox Fruits, King Legacy, Fisch ฯลฯ")
    @app_commands.describe(query="ชื่อเกมที่ต้องการ (Blox Fruits, Fisch, King Legacy ฯลฯ)")
    @app_commands.autocomplete(query=_game_autocomplete)
    async def bloxscript_cmd(self, interaction: discord.Interaction, query: str):
        """ค้นหาสคริปต์ Blox Script ตามชื่อเกม"""
        await interaction.response.defer(ephemeral=False)
        results = search_scripts(query)
        bscripts = [r for r in results if r.get("source") == "bloxscript"]

        if not bscripts:
            all_cnt = len(results)
            msg = f"ไม่พบสคริปต์ Blox Script สำหรับ `{query}`"
            if all_cnt > 0:
                msg += f"\n\n💡 แต่พบ `{all_cnt}` รายการจาก RScript! ลองใช้ `/rscript query:{query}`"
            embed = discord.Embed(
                title="🟦 ไม่พบสคริปต์ Blox Script",
                description=msg,
                color=COLOR_ERROR
            )
            embed.add_field(name="💡 แนะนำ", value="ลองใช้ `/games` ดูรายชื่อเกมทั้งหมด", inline=False)
            await interaction.followup.send(embed=embed)
        if ScriptCardView and bscripts:
            view = ScriptCardView(bscripts, 0, interaction.user.id)
            await interaction.followup.send(embed=view._build_embed(), view=view)
            return

        embed = self._build_search_embed(bscripts[:10], query, "Blox Script", "🟦")
        if len(bscripts) > 10:
            embed.set_footer(text=f"แสดง 10 จาก {len(bscripts)} รายการ • ใช้คำค้นที่เจาะจงกว่านี้")
        else:
            embed.set_footer(text=f"พบ {len(bscripts)} รายการ • ใช้คำสั่ง /script-search เพื่อค้นหาทุกแหล่ง")
        await interaction.followup.send(embed=embed)

    # ── /game ──
    @app_commands.command(name="game", description="🎮 ค้นหาสคริปต์ตามชื่อเกม (พิมพ์ชื่อเกมเท่านั้น)")
    @app_commands.describe(game_name="ชื่อเกมที่ต้องการดูสคริปต์")
    @app_commands.autocomplete(game_name=_game_autocomplete)
    async def game_cmd(self, interaction: discord.Interaction, game_name: str):
        """ค้นหาสคริปต์ทั้งหมดของเกมที่ระบุ"""
        await interaction.response.defer(ephemeral=False)
        all_scripts = get_all_scripts()

        gn = game_name.lower().strip()
        matched = [s for s in all_scripts if gn in s.get("game", "").lower()]

        if not matched:
            embed = discord.Embed(
                title=f"🎮 ไม่พบเกม \"{game_name}\"",
                description="ไม่พบเกมนี้ในฐานข้อมูล ลองพิมพ์ชื่อใหม่ หรือใช้ `/games` เพื่อดูทั้งหมด",
                color=COLOR_ERROR
            )
            await interaction.followup.send(embed=embed)
            return

        # Group by type
        by_type = {}
        for s in matched:
            t = s.get("type", "other")
            by_type.setdefault(t, []).append(s)

        type_order = ["farm", "aimbot", "esp", "mod", "admin", "quest", "raid", "hunt", "stat", "shop", "dungeon", "tool", "script", "other"]

        embed = discord.Embed(
            title=f"{get_game_emoji(game_name)} สคริปต์สำหรับ {game_name}",
            description=f"พบ `{len(matched)}` สคริปต์",
            color=COLOR_PRIMARY
        )

        for t in type_order:
            if t in by_type:
                names = [s["name"] for s in by_type[t][:3]]
                t_emoji = TYPE_EMOJI.get(t, "📦")
                t_name = t.upper()
                extra = f" และอีก {len(by_type[t]) - 3} รายการ" if len(by_type[t]) > 3 else ""
                embed.add_field(
                    name=f"{t_emoji} {t_name}",
                    value="\n".join(f"• {n}" for n in names) + extra,
                    inline=True
                )

        sources = set(s.get("source", "") for s in matched)
        source_text = " • ".join(f"{'🔴 R' if src == 'rscript' else '🟦 B'}" for src in sources)
        embed.add_field(name="📦 แหล่งที่มา", value=source_text if source_text else "ในตัว", inline=False)
        embed.set_footer(text="ใช้ /rscript หรือ /bloxscript เพื่อดูรายละเอียดแต่ละสคริปต์")

        await interaction.followup.send(embed=embed)

    # ── /games ──
    @app_commands.command(name="games", description="📚 แสดงรายชื่อเกมทั้งหมดที่มีสคริปต์ในระบบ")
    async def games_cmd(self, interaction: discord.Interaction):
        """แสดงรายชื่อเกมทั้งหมดในฐานข้อมูล"""
        all_scripts = get_all_scripts()
        games = {}
        for s in all_scripts:
            g = s.get("game", "Unknown")
            if g == "universal":
                continue
            games.setdefault(g, 0)
            games[g] += 1

        sorted_games = sorted(games.items(), key=lambda x: -x[1])

        embed = discord.Embed(
            title="📚 รายชื่อเกมทั้งหมด",
            description=f"มี `{len(sorted_games)}` เกม รวม `{len(all_scripts)}` สคริปต์",
            color=COLOR_PRIMARY
        )

        emoji_row = []
        for i, (game, count) in enumerate(sorted_games[:30]):
            emoji = get_game_emoji(game)
            emoji_row.append(f"{emoji} **{game}** (`{count}`)")

        # Split into multiple fields if needed
        chunk_size = 10
        for i in range(0, len(emoji_row), chunk_size):
            chunk = emoji_row[i:i + chunk_size]
            embed.add_field(
                name=f"📋 เกม (หน้า {i // chunk_size + 1})" if i > 0 else "📋 เกมทั้งหมด",
                value="\n".join(chunk),
                inline=False
            )

        embed.set_footer(text="พิมพ์ชื่อเกมเพื่อค้นหาสคริปต์ • เช่น /game game_name:Blox Fruits")
        await interaction.response.send_message(embed=embed)

    # ── /script-search ──
    @app_commands.command(name="script-search", description="🔍 ค้นหาสคริปต์จากทุกแหล่ง (Local + ScriptBlox API + Rscripts API)")
    @app_commands.describe(query="ชื่อเกม, แมพ, หรือสคริปต์ที่ต้องการ")
    @app_commands.autocomplete(query=_game_autocomplete)
    async def script_search_cmd(self, interaction: discord.Interaction, query: str):
        """ค้นหาสคริปต์จากทุกแหล่ง — รวม API ภายนอก"""
        await interaction.response.defer(ephemeral=False)

        # ค้นหาจากฐานข้อมูลในตัวก่อน
        local_results = search_scripts(query)
        api_results = []
        api_errors = []

        # ถ้ามี API client ให้ค้นหาจาก API ภายนอกด้วย
        if script_api is not None:
            try:
                # ค้นหาจากทั้ง 2 API พร้อมกัน
                import asyncio
                async def fetch_apis():
                    sb_results, sb_err = [], None
                    rs_results, rs_err = [], None

                    try:
                        sb_results = await script_api.search_scriptblox(query, limit=15)
                    except Exception as e:
                        sb_err = str(e)

                    try:
                        rs_results = await script_api.search_rscripts(query, limit=15)
                    except Exception as e:
                        rs_err = str(e)

                    return [*sb_results, *rs_results], [str(sb_err) if sb_err else "", str(rs_err) if rs_err else ""]

                combined, errs = await fetch_apis()
                api_errors = [e for e in errs if e]
                api_results = combined
            except Exception as e:
                api_errors.append(str(e))

        # รวมผลทั้งหมด
        all_results = local_results
        # เพิ่ม API results ที่ไม่ซ้ำชื่อ
        seen_names = {r.get("name", "").lower() for r in all_results}
        for r in api_results:
            name = r.get("name", "").lower()
            if name not in seen_names:
                seen_names.add(name)
                all_results.append(r)

        # ถ้าไม่มีผลลัพธ์เลย
        if not all_results:
            clean_errors = []
            for e in api_errors:
                if "<" in e or "doctype" in e.lower() or "502" in e:
                    clean_errors.append("RScripts API unreachable (502)")
                elif e:
                    clean_errors.append(e[:60])
            msg = f"**ไม่พบสคริปต์สำหรับ `{query}`**\n"
            msg += "\n💡 ลองใช้คำค้นอื่น เช่น `farm`, `auto`, `blox`, `script`"
            if clean_errors:
                msg += f"\n⚠️ API Status: `{', '.join(clean_errors)}`"
            embed = discord.Embed(
                title="🔍 ไม่พบผลลัพธ์",
                description=msg,
                color=COLOR_ERROR
            )
            await interaction.followup.send(embed=embed)
        if ScriptCardView and all_results:
            view = ScriptCardView(all_results, 0, interaction.user.id)
            await interaction.followup.send(embed=view._build_embed(), view=view)
            return

        # แสดงผล
        embed = self._build_search_embed(all_results[:15], query, "All Sources (Local + APIs)", "🔍")

        # เพิ่มข้อมูลแหล่งที่มา
        sources = set(r.get("source", "local") for r in all_results)
        source_text = []
        for s in sources:
            if s == "rscript":
                source_text.append("🔴 RScript (Local)")
            elif s == "bloxscript":
                source_text.append("🟦 Blox Script (Local)")
            elif s == "scriptblox_api":
                source_text.append("🌐 ScriptBlox API")
            elif s == "rscripts_api":
                source_text.append("📡 Rscripts API")
            elif s == "local":
                source_text.append("📦 Local DB")
            else:
                source_text.append(f"📁 {s}")

        extra_text = f"แสดง 15 จาก {len(all_results)} รายการ"
        if api_errors:
            extra_text += f" • ⚠️ API Error: `{', '.join(api_errors)[:80]}`"
        embed.set_footer(text=f"📊 {extra_text} • แหล่งข้อมูล: {' • '.join(source_text[:5])}")

        await interaction.followup.send(embed=embed)

    # ── Utility ──
    def _build_search_embed(self, scripts: list, query: str, source_name: str, source_emoji: str) -> discord.Embed:
        """สร้าง embed สำหรับแสดงผลการค้นหา"""
        embed = discord.Embed(
            title=f"{source_emoji} ผลค้นหา \"{query}\"",
            description=f"พบ `{len(scripts)}` รายการจาก {source_name}",
            color=COLOR_PRIMARY
        )

        for s in scripts:
            type_emoji = TYPE_EMOJI.get(s.get("type", ""), "📦")
            source_tag = "🔴 R" if s.get("source") == "rscript" else "🟦 B"
            game = s.get("game", "Unknown")
            executor = s.get("executor", s.get("source", "krnl"))
            desc = s.get("description", "")[:120]
            url = s.get("url", "")

            value = (
                f"{source_tag} | 🎮 **{game}** | ⚙️ `{executor}`\n"
                f"{desc}"
            )

            embed.add_field(
                name=f"{type_emoji} {s['name']}",
                value=value,
                inline=False
            )

        return embed


async def setup(bot: commands.Bot):
    await bot.add_cog(ScriptsCog(bot))