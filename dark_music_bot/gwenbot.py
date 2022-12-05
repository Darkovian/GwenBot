from asyncio import sleep
from json import load
from logging import info
from multiprocessing import Queue
from pathlib import WindowsPath
from queue import Empty
from typing import Any, Dict
from uuid import UUID

from discord import Activity, ActivityType, Guild, Intents, TextChannel
from discord.ext import commands
from yaml import safe_dump, safe_load

from dark_music_bot.admin_cog import Administration
from dark_music_bot.gwen_command import GwenCommand, GwenCommands
from dark_music_bot.music_cog import Music
from dark_music_bot.music_control_data import MusicControlData
from dark_music_bot.shipping_cog import Shipping
from dark_music_bot.yt_functions import check_oauth

SECRETS = None
with open('discord_secrets.json', 'r', encoding='utf-8') as file_handler:
    SECRETS = load(fp=file_handler)

DEFAULT_SETTINGS = {
    'default_presence': {'type': 'listening', 'name': 'to music! 🎶'}
}

SETTINGS_PATH = WindowsPath('./settings.yaml').absolute()


class GwenBot(commands.Bot):
    def __init__(self, comm_queue: Queue, data_queue: Queue, ffmeg_path: WindowsPath, *args, **kwargs) -> None:
        super().__init__(**kwargs)
        self.comm_queue = comm_queue
        self.data_queue = data_queue
        self.collected_data_jobs: Dict[str, GwenCommand] = {}
        self.settings = DEFAULT_SETTINGS
        self.ffmeg_path = ffmeg_path
        self.load_settings()
        self.add_cog(Administration(self))
        self.add_cog(Shipping(self))
        self.add_cog(Music(self))
        check_oauth()

    def load_settings(self) -> None:
        if SETTINGS_PATH.exists():
            with SETTINGS_PATH.open('r', encoding='utf-8') as fp:
                settings: dict = safe_load(fp)
            for k, v in settings.items():
                self.settings.update({k: v})
        else:
            with SETTINGS_PATH.open('wb') as fp:
                safe_dump(DEFAULT_SETTINGS, fp, encoding='utf-8')

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        self.loop.create_task(self.change_presence(activity=Activity(type=ActivityType[self.settings['default_presence']['type']], name=self.settings['default_presence']['name'])))
        music_cog: Music = self.get_cog('Music')
        music_cog.track_queue = {k.id: [] for k in self.guilds}
        music_cog.leave_voice_timer = {k.id: None for k in self.guilds}
        music_cog.control_data = {k.id: MusicControlData for k in self.guilds}
        info(f'\n\nGUILDS: {" | ".join([str(g.id) for g in self.guilds])}\n\n')

    @commands.Cog.listener()
    async def on_guild_join(self, guild: Guild):
        music_cog: Music = self.get_cog('Music')
        music_cog.track_queue[guild.id] = []
        music_cog.leave_voice_timer[guild.id] = None
        music_cog.control_data[guild.id] = MusicControlData

    async def type_for(self, channel: TextChannel, duration: float) -> None:
        async def do_typing(channel: TextChannel = channel, duration: float = duration):
            async with channel.typing():
                await sleep(duration)
        self.loop.create_task(do_typing(channel=channel, duration=duration))

    async def get_data_from_queue_with_id(self, cmd_id: UUID):
        while self.data_queue.qsize() > 0:
            try:
                _item: GwenCommand = self.data_queue.get(block=False, timeout=None)
                self.collected_data_jobs[_item.id] = _item.result
            except Empty:
                break

        if cmd_id in self.collected_data_jobs.keys():
            _return_item = self.collected_data_jobs.pop(cmd_id)
            return _return_item

        # if our result wasn't included in this batch try again in 1 second
        await sleep(1)
        return await self.get_data_from_queue_with_id(cmd_id=cmd_id)

    async def put_command_in_comm_queue(self, command: GwenCommand) -> UUID:
        self.comm_queue.put(command)
        return command.id

    async def handle_queue_command(self, command: GwenCommand) -> Any:
        cmd_id = await self.put_command_in_comm_queue(command=command)
        result = await self.get_data_from_queue_with_id(cmd_id)
        return result


intents = Intents.default()
intents.integrations = True
intents.messages = True
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.guild_messages = True
