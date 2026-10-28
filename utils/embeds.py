import discord
import time
from datetime import datetime
from config import COLOR_PRIMARY, COLOR_SUCCESS, COLOR_ERROR, COLOR_WARNING, COLOR_INFO

class BypassButtonsView(discord.ui.View):
    """Interactive UI Buttons attached to the Bypass result Embed."""

    def __init__(self, direct_url: str, user_id: int):
        super().__init__(timeout=300)
        self.direct_url = direct_url
        self.user_id = user_id

        if len(direct_url) <= 512 and (direct_url.startswith("http://") or direct_url.startswith("https://")):
            self.add_item(discord.ui.Button(
                label="Open Direct Link",
                style=discord.ButtonStyle.link,
                url=direct_url,
                emoji="🔗"
            ))

    @discord.ui.button(label="Send to DM", style=discord.ButtonStyle.secondary, emoji="📩", custom_id="btn_send_dm")
    async def send_dm_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            dm_url = self.direct_url if len(self.direct_url) <= 1900 else self.direct_url[:1900] + "..."
            embed = discord.Embed(
                title="📩 Direct Link",
                description=f"ลิงค์ที่ Unlock แล้ว:\n```{dm_url}```",
                color=COLOR_SUCCESS
            )
            embed.set_footer(text="Self-hosted Bypass Bot • Privately Sent")
            await interaction.user.send(embed=embed)
            await interaction.response.send_message("✅ ส่ง Direct link ไปยัง DM ของคุณแล้ว!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ ไม่สามารถส่ง DM ได้ กรุณาเปิด DM ก่อน", ephemeral=True)

    @discord.ui.button(label="Copy Link", style=discord.ButtonStyle.primary, emoji="📋", custom_id="btn_copy_link")
    async def copy_link_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        copy_url = self.direct_url if len(self.direct_url) <= 1900 else self.direct_url[:1900]
        await interaction.response.send_message(
            content=f"📋 **Copyable Direct Link:**\n```{copy_url}```",
            ephemeral=True
        )


class EmbedFactory:
    """Generates styled Discord Embeds."""

    @staticmethod
    def create_loading(url: str, provider: dict) -> discord.Embed:
        embed = discord.Embed(
            title="⚡ กำลัง Bypass...",
            description=(
                f"**กำลังประมวลผลลิงค์...** รอสักครู่\n\n"
                f"**Target:** `{url[:70]}{'...' if len(url)>70 else ''}`"
            ),
            color=COLOR_PRIMARY
        )
        embed.add_field(name="ค่ายที่ตรวจพบ", value=f"{provider['emoji']} **{provider['name']}**", inline=True)
        embed.add_field(name="Status", value="⏳ `กำลัง Bypass...`", inline=True)
        embed.set_footer(text="Self-hosted Bypass Engine")
        return embed

    @staticmethod
    def create_success(
        original_url: str,
        direct_url: str,
        provider: dict,
        elapsed_time: float,
        sent_dm: bool = False,
        chain_note: str = "",
        is_key: bool = False,
        endpoint_used: str = ""
    ) -> discord.Embed:
        if is_key:
            title = "🔑 ได้ Key สำเร็จ!"
            link_label = "🔑 Key ของคุณ"
        else:
            title = "✅ Bypass สำเร็จ!"
            link_label = "🔗 Direct Link"

        embed = discord.Embed(title=title, color=COLOR_SUCCESS)
        embed.add_field(name=f"{provider['emoji']} ค่าย", value=f"**{provider['name']}**", inline=True)
        embed.add_field(name="⏱️ เวลา", value=f"`{elapsed_time:.2f}s`", inline=True)
        if endpoint_used:
            embed.add_field(name="🔌 Solver", value=f"`{endpoint_used}`", inline=True)
        if chain_note:
            embed.add_field(name="⛓️ Chain", value=f"`{chain_note}`", inline=True)
        embed.add_field(name="🛡️ Safety", value="`ตรวจสอบแล้ว` 🟢", inline=True)

        display_url = direct_url if len(direct_url) <= 1000 else direct_url[:990] + "..."
        embed.add_field(name=link_label, value=f"```{display_url}```", inline=False)

        footer = "📩 ส่งไปยัง DM แล้ว!" if sent_dm else "กด 'Send to DM' เพื่อเก็บลิงค์แบบส่วนตัว"
        embed.set_footer(text=footer)
        return embed

    @staticmethod
    def create_error(original_url: str, provider: dict, error_msg: str) -> discord.Embed:
        embed = discord.Embed(
            title="❌ Bypass ไม่สำเร็จ",
            description=f"ไม่สามารถ Bypass ลิงค์นี้ได้\n\n**Error:** `{error_msg}`",
            color=COLOR_ERROR
        )
        embed.add_field(name="ค่าย", value=f"{provider['emoji']} **{provider['name']}**", inline=True)
        embed.add_field(name="URL", value=f"`{original_url[:80]}...`", inline=False)
        embed.set_footer(text="ลองตรวจสอบว่าลิงค์ยังใช้งานได้อยู่")
        return embed

    @staticmethod
    def create_cooldown(retry_after: float) -> discord.Embed:
        embed = discord.Embed(
            title="⏳ Anti-Spam Cooldown",
            description=f"รอ **{retry_after:.1f} วินาที** ก่อนส่งลิงค์ใหม่",
            color=COLOR_WARNING
        )
        embed.set_footer(text="Rate Limit Protection")
        return embed

    @staticmethod
    def create_stats(stats_data: dict, bot_uptime: str = "Active") -> discord.Embed:
        embed = discord.Embed(
            title="📊 Bypass Statistics",
            description="สถิติการใช้งานระบบ Bypass",
            color=COLOR_PRIMARY
        )
        embed.add_field(name="🚀 Bypass ทั้งหมด", value=f"**{stats_data['total_bypassed']:,}** ลิงค์", inline=True)
        embed.add_field(name="📅 วันนี้", value=f"**{stats_data['today_count']:,}** ลิงค์", inline=True)
        embed.add_field(name="👥 ผู้ใช้", value=f"**{stats_data['unique_users']:,}** คน", inline=True)
        embed.add_field(name="⏰ Uptime", value=f"`{bot_uptime}`", inline=True)
        embed.add_field(name="🌐 Status", value="`ONLINE 🟢`", inline=True)

        if stats_data.get("top_providers"):
            lines = [f"• **{n.capitalize()}**: `{c:,}` ลิงค์" for n, c in stats_data["top_providers"]]
            embed.add_field(name="🏆 Top Providers", value="\n".join(lines), inline=False)

        embed.set_footer(text="Self-hosted Bypass Bot")
        return embed

    @staticmethod
    def create_log(
        user: discord.User,
        provider: dict,
        original_url: str,
        elapsed: float,
        success: bool,
        endpoint: str = "unknown"
    ) -> discord.Embed:
        """
        Public log embed sent to the result/log channel.
        Shows: who, what time, which provider, pass/fail.
        Does NOT show the direct URL (that's ephemeral only).
        """
        now = datetime.now()
        time_str = now.strftime("%d/%m/%Y %H:%M:%S")

        color = COLOR_SUCCESS if success else COLOR_ERROR
        status_text = "✅ **PASS**" if success else "❌ **FAIL**"

        embed = discord.Embed(
            title=f"{provider['emoji']} Bypass Log",
            color=color,
            timestamp=now
        )
        embed.add_field(name="👤 ผู้ใช้", value=f"{user.mention} (`{user.name}`)", inline=True)
        embed.add_field(name="🕐 เวลา", value=f"`{time_str}`", inline=True)
        embed.add_field(name="📊 ผลลัพธ์", value=status_text, inline=True)
        embed.add_field(name="🏷️ ค่าย Link", value=f"{provider['emoji']} **{provider['name']}**", inline=True)
        embed.add_field(name="⏱️ เวลาที่ใช้", value=f"`{elapsed:.2f}s`", inline=True)
        if success:
            embed.add_field(name="🔌 Engine", value=f"`{endpoint}`", inline=True)

        display_url = original_url if len(original_url) <= 60 else original_url[:57] + "..."
        embed.add_field(name="🔗 Original Link", value=f"`{display_url}`", inline=False)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="Bypass Log • ลิงค์ตรงส่งให้ผู้ใช้แบบส่วนตัวแล้ว")
        return embed
