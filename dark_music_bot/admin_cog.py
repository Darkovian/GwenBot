from __future__ import annotations

from logging import error
from typing import TYPE_CHECKING

from discord import ApplicationContext, Embed
from discord.ext import commands


if TYPE_CHECKING:
    from dark_music_bot.gwenbot import GwenBot


class Administration(commands.Cog):
    def __init__(self, bot: GwenBot):
        self.bot: GwenBot = bot

    def check_is_owner(ctx: commands.Context):
        return ctx.message.author.id == 545320998988415016

    @commands.command(help='Allows Gwen to take a break and get some sleep 💤')
    @commands.check(check_is_owner)
    async def sleepytime(self, ctx: commands.Context):
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                if channel.name.lower() == 'bot-spam':
                    async with channel.typing():
                        await channel.send(content='I\'m gonna go nap for awhile, but I\'ll be back later to play more! 💤')
        self.bot.data_queue.put({'cmd': 'stop'})
        await self.bot.close()

    @commands.slash_command(description='Information about how to interact with GwenBot')
    async def gwen_help(self, ctx: ApplicationContext):
        async with ctx.channel.typing():
            msg = 'To see a list of commands with descriptions, try `/gwen help` or `/g:help`! 😼\n'
            embed = Embed()
            embed.title = '🐈 GwenBot Help 🐈'
            embed.description = msg
            embed.add_field(name='Command Prefix', value='/gwen *command* OR /g: *command*\n - Ex: /gwen hello OR /g:hello\n\n')
            for cogName in self.bot.cogs:
                cog = self.bot.get_cog(cogName)
                cog_msg = ''
                for cmd in cog.walk_commands():
                    if cmd.name != 'gwen_help':
                        cog_msg += f'  - {cmd.name}\n'
                embed.add_field(name=cogName, value=cog_msg, inline=False)
            
        self.bot.loop.create_task(ctx.respond(content=None, embed=embed))

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, exception: commands.errors.CommandError, /) -> None:
        error(msg=str(exception))
        self.bot.loop.create_task(ctx.message.reply(content='I don\'t have to listen to you! *scurries away* 🐈'))
