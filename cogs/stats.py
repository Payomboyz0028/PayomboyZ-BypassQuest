import discord
from discord import app_commands
from discord.ext import commands
from utils.stats_manager import stats_manager
from utils.embeds import EmbedFactory

class StatsCog(commands.Cog):
    """Cog handling statistics dashboard command."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="stats", description="View KeyBypass network statistics and bypass counts")
    async def stats_slash(self, interaction: discord.Interaction):
        """Displays real-time bypassing statistics."""
        try:
            summary = stats_manager.get_summary()
            embed = EmbedFactory.create_stats(summary)
            
            # Add server-specific count if in a guild
            if interaction.guild:
                guild_id_str = str(interaction.guild.id)
                server_bypasses = stats_manager.stats.get("servers_count", {}).get(guild_id_str, 0)
                embed.add_field(
                    name="🏰 Server Bypasses",
                    value=f"**{server_bypasses:,}** links in `{interaction.guild.name}`",
                    inline=False
                )

            if interaction.response.is_done():
                await interaction.followup.send(embed=embed)
            else:
                await interaction.response.send_message(embed=embed)
        except Exception as e:
            print(f"[StatsCog Error]: {e}")
            msg = f"❌ Failed to load statistics: `{str(e)}`"
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(StatsCog(bot))
