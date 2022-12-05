from __future__ import annotations

from random import random, seed
from asyncio import sleep
from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from dark_music_bot.gwenbot import GwenBot


class Shipping(commands.Cog):
    def __init__(self, bot: GwenBot):
        self.bot: GwenBot = bot

    @commands.command(help='Calculates how compatible the first two users mentioned in the message are')
    async def ship(self, ctx: commands.Context):
        """Calculates how compatible the first two users mentioned in the message are"""
        if len(ctx.message.mentions) == 0:
            self.bot.loop.create_task(self.bot.type_for(ctx.channel, duration=0.5))
            self.bot.loop.create_task(ctx.channel.send(content='Shipping requires at least one person to be mentioned, meow!', reference=ctx.message))
        elif len(ctx.message.mentions) == 1:
            self.bot.loop.create_task(self.bot.type_for(ctx.channel, duration=2))
            date_component = ctx.message.created_at.year + ctx.message.created_at.month + ctx.message.created_at.day
            await ctx.send(content='Meowculating the compatibility of: ' + ctx.message.mentions[0].mention + ' with themselves... 😽')
            seed(sum([
                date_component,
                int(ctx.message.mentions[0].discriminator),
                int(ctx.message.mentions[0].discriminator),
                ctx.message.mentions[0].id,
                ctx.message.mentions[0].id
            ]))
            user_compatibility = f'{random() * 100:.2f}%'
            await sleep(2)
            self.bot.loop.create_task(
                ctx.send(
                    content='I\'ve got it ' + ctx.author.mention + ' , meow! ' + ctx.message.mentions[0].mention + ' is ' + user_compatibility + ' compatible with themself! 😸',
                    reference=ctx.message
                )
            )
        else:
            self.bot.loop.create_task(self.bot.type_for(ctx.channel, duration=2))
            date_component = ctx.message.created_at.year + ctx.message.created_at.month + ctx.message.created_at.day
            await ctx.send(content='Meowculating the compatibility of: ' + ctx.message.mentions[0].mention + ' and ' + ctx.message.mentions[1].mention + '... 😽')
            seed(sum([
                date_component,
                int(ctx.message.mentions[0].discriminator),
                int(ctx.message.mentions[1].discriminator),
                ctx.message.mentions[0].id,
                ctx.message.mentions[1].id
            ]))
            user_compatibility = random() * 100
            if ctx.message.mentions[0].discriminator in ['2021', '1463'] and ctx.message.mentions[1].discriminator in ['2021', '1463']:
                user_compatibility += 80
            user_compatibility_str = f'{user_compatibility:.2f}%'
            await sleep(2)
            self.bot.loop.create_task(
                ctx.send(
                    content='I\'ve got it ' + ctx.author.mention + ' , meow! ' + ctx.message.mentions[0].mention + ' and ' + ctx.message.mentions[1].mention + ' are ' + user_compatibility_str + ' compatible! 😸',
                    reference=ctx.message
                )
            )
