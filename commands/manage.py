"""
manage.py
Slash Commands that are meant to be used by whoever is hosting the bot.
"""

import asyncio
import os

import aiohttp
import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup
from discord.commands import Option

from db.pet import Character
from utils.error_message import apologize

admin_guild_id = int(os.environ.get("admin_guild_id", "0"))


def setup(bot):
    """
    Code to run on cog import.
    """
    bot.add_cog(Manage(bot))


class Manage(commands.Cog):
    """
    Slash Commands that are meant to be used by whoever is hosting the bot.
    They are only available from one (presumably private) server.
    """

    def __init__(self, bot: discord.Bot):
        self.bot = bot

    admin = SlashCommandGroup(
        "admin",
        "Commands for the bot's owner.",
        checks=[commands.is_owner().predicate],
        guild_ids=[admin_guild_id],
    )
    
    def reload_cogs(self):
        for cog in [x[:-3] for x in os.listdir("commands") if x.endswith(".py")]:
            try:
                self.bot.unload_extension(f"commands.{cog}")
            except (discord.ExtensionNotLoaded, discord.ExtensionNotFound):
                pass

        # pylint: disable=protected-access
        self.bot._pending_application_commands = []

        for cog in [x[:-3] for x in os.listdir("commands") if x.endswith(".py")]:
            self.bot.load_extension(f"commands.{cog}")

    @admin.command(description="Reload the bot's extensions")
    async def reload(self, ctx: discord.ApplicationContext):
        """
        Reloads extensions.
        """
        self.reload_cogs()
        await ctx.respond("✅ Done", ephemeral=True)

    @admin.command(descriptioon="Sync commands to a guild")
    async def sync(self, ctx: discord.ApplicationContext):
        """
        Syncs all commands with Discord.
        """
        await self.bot.sync_commands()
        await ctx.respond("✅ Done", ephemeral=True)
    
    @admin.command(descriptioon="Sync commands to a guild")
    async def refreshall(self, ctx: discord.ApplicationContext):
        """
        Reload and then sync.
        """
        self.reload_cogs()
        await self.bot.sync_commands()
        await ctx.respond("✅ Done", ephemeral=True)

    @admin.command(descriptioon="Add a pet command")
    async def addpet(
        self,
        ctx: discord.ApplicationContext,
        gifname: Option(str, "GIF filename"),
        name: Option(str, "Character name"),
        is_oc: Option(bool, "Whether this is an OC"),
        owner: Option(str, "Owner of this OC (if applicable)", required=False),
        url: Option(str, "Image URL to download and automatically commit", required=False),
    ):
        if is_oc and not owner:
            await ctx.respond("❌ An owner must be supplied if adding an OC", ephemeral=True)
        if url:
            outfile = f'assets/pet/{"oc" if is_oc else "character"}/{gifname}.gif'
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        f = open(outfile, mode='wb')
                        f.write(await resp.read())
                        f.close()
            assert os.system(f'git reset') == 0
            assert os.system(f'git add "{outfile}"') == 0
            assert os.system(f'git commit "{outfile}" -m "Upload .gif, automatic commit"') == 0
            assert os.system(f'git push origin main') == 0
        Character.create(gif=gifname, name=name, is_oc=is_oc, owner=owner)
        # pylint: disable=protected-access
        self.bot._pending_application_commands = []
        self.bot.unload_extension("commands.pet")
        self.bot.load_extension("commands.pet")
        await self.bot.sync_commands()
        await ctx.respond("✅ Done", ephemeral=True)
    
    @admin.command(description="Update from GitHub")
    async def pull(self, ctx: discord.ApplicationContext):
        """
        Update from GitHub.
        """
        assert os.system(f'git pull origin main') == 0
        await ctx.respond("✅ Done", ephemeral=True)
    
    @commands.Cog.listener()
    async def on_application_command_error(
        self, ctx: discord.ApplicationContext, error: discord.DiscordException
    ):
        """
        Handler for errors (to tell a user they can't use the bot).
        """
        if isinstance(error, commands.NotOwner):
            ctx.options = {"handled": True}
            await apologize(ctx, "You can't use that command.")