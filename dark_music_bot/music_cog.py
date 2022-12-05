from __future__ import annotations

from asyncio import TimerHandle, gather
from logging import warn
from typing import TYPE_CHECKING, Dict, Union
from discord import TextChannel, NotFound, ButtonStyle, Guild, User, Member, VoiceChannel, VoiceClient, Message, File, FFmpegOpusAudio, Interaction
from discord.ext import commands
from discord.ui import View, Button

from dark_music_bot.gwen_command import GwenCommand, GwenCommands
from dark_music_bot.music_control_data import MusicControlData
from dark_music_bot.yt_results import YTResults

if TYPE_CHECKING:
    from dark_music_bot.gwenbot import GwenBot

# 'last_search_keyword': None,
# 'last_search_results': None,
# 'current_control_msg_id': None,
# 'current_stop_msg_id': None,
# 'current_stop_msg': None


class Music(commands.Cog):
    reactions = {
        '1': u'\u0031\uFE0F\u20E3',
        '2': u'\u0032\uFE0F\u20E3',
        '3': u'\u0033\uFE0F\u20E3',
        '4': u'\u0034\uFE0F\u20E3',
        '5': u'\u0035\uFE0F\u20E3',
        'N': u'\u25B6\uFE0F',
        'P': '◀️'
    }
    FFMPEG_OPT = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn -af equalizer=w=1:t=o:f=55:g=0:r=f64,dynaudnorm=b=1:m=1'
    }

    def __init__(self, bot: GwenBot):
        self.bot: GwenBot = bot
        
        self.control_data: Dict[Union[str, int], MusicControlData] = {}
        self.track_queue: Dict[Union[str, int], list] = {}
        self.leave_voice_timer: Dict[Union[str, int], Union[TimerHandle, None]] = {}

    async def cancel_leave_voice_timer(self, guild_id: int) -> None:
        if self.leave_voice_timer[guild_id] is not None:
            if not self.leave_voice_timer[guild_id].cancelled():
                self.leave_voice_timer[guild_id].cancel()
                self.leave_voice_timer[guild_id] = None

    async def delete_current_stop_button(self, guild_id: int) -> None:
        if self.control_data[guild_id].current_stop_msg is not None:
            try:
                await self.control_data[guild_id].current_stop_msg.delete()
            except NotFound:
                warn(f'[ ! ] ({guild_id}) - No delete button message found, skipping deletion')
            except AttributeError:
                warn(f'[ ! ] ({guild_id}) - Delete method not found on current Stop Button value')
            finally:
                self.control_data[guild_id].current_stop_msg = None

    async def send_new_stop_button(self, guild_id: int, channel: TextChannel):
        await self.delete_current_stop_button(guild_id=guild_id)
        stop_btn_view = View()
        stop_btn_view.add_item(Button(style=ButtonStyle.red, label='Stop Playing', custom_id='btn_stop', emoji=u'\u2620\uFE0F', row=0))
        stop_msg = await channel.send(view=stop_btn_view)
        self.control_data[guild_id].current_stop_msg = stop_msg

    async def find_user_voice_channel(self, guild: Guild, user: Union[User, Member]):
        if isinstance(user, User) and not isinstance(user, Member):
            user = guild.get_member_named(user.name)
        elif isinstance(user, Member):
            user = user
        if user is None or user.voice is None:
            return None
        return user.voice.channel

    async def join_voice(self, channel: VoiceChannel):
        await self.cancel_leave_voice_timer(guild_id=channel.guild.id)
        current_voice: VoiceClient = channel.guild.voice_client
        if current_voice is not None:
            await current_voice.move_to(channel)
            return current_voice
        else:
            return await channel.connect()

    async def leave_voice(self, voice_client: VoiceClient):
        await voice_client.disconnect()

    @commands.command(name='join', aliases=['j'], help='Ask GwenBot to join your current voice channel without playing anything | j')
    async def join_vc(self, ctx: commands.Context):
        voice_channel = await self.find_user_voice_channel(guild=ctx.guild, user=ctx.author)
        if voice_channel is None:
            self.bot.loop.create_task(ctx.send('You aren\'t in a voice channel right meow! 🧶'))
        else:
            voice_client = await self.join_voice(channel=voice_channel)
            self.leave_voice_timer[ctx.guild.id] = self.bot.loop.call_later(5 * 60, self.bot.loop.create_task, self.leave_voice(voice_client=voice_client))

    async def display_results(self, message: Message, results: YTResults, searching_message: Message):
        ctx: commands.Context = await self.bot.get_context(message)
        max_result_key = max(list(results.results.keys()))

        command = GwenCommand(cmd=GwenCommands.CreateSearchResultContent, data={'author_id': ctx.author.id, 'results': results})
        display_data = await self.bot.handle_queue_command(command=command)
        play_buttons = display_data['play_buttons']
        queue_buttons = display_data['queue_buttons']
        embeds = display_data['embeds']
        attachments = [File(fp=i[0], filename=i[1]) for i in display_data['files']]

        # Construct the view and send
        control_view = View()
        for btn in play_buttons:
            control_view.add_item(btn)
        for btn in queue_buttons:
            control_view.add_item(btn)
        control_view.add_item(Button(style=ButtonStyle.success, label='Prev Page', custom_id='btn_prev', url=None, emoji=self.reactions['P'], row=max(max_result_key - 2, 0), disabled=results.prev_page_token is None))
        control_view.add_item(Button(style=ButtonStyle.success, label='Next Page', disabled=False, custom_id='btn_next', url=None, emoji=self.reactions['N'], row=max(max_result_key - 1, 0)))

        result_msg = await searching_message.edit(content=None, embeds=embeds, files=attachments, view=control_view)
        self.control_data[ctx.guild.id].current_control_msg_id = result_msg.id

    @commands.command(aliases=['s'], help='Searches YouTube for videos matching your message. Returns 5 results with the ability to view next (and previous) pages | s')
    async def search(self, ctx: commands.Context, *, keyword):
        """Searches YouTube for videos matching what you ask for"""
        self.control_data[ctx.guild.id].last_search_keyword = keyword

        self.bot.loop.create_task(self.bot.type_for(channel=ctx.channel, duration=3.5))
        searching_msg_task = self.bot.loop.create_task(ctx.send(content='Search in progress...', reference=ctx.message))

        command = GwenCommand(cmd=GwenCommands.Search, data={'keyword': keyword, 'page_token': None})
        results = await self.bot.handle_queue_command(command=command)
        self.control_data[ctx.guild.id].last_search_results = results
        searching_msg = await searching_msg_task
        self.bot.loop.create_task(self.display_results(message=ctx.message, results=results, searching_message=searching_msg))

    async def next(self, ctx: commands.Context):
        if self.control_data[ctx.guild.id].last_search_results is not None:
            self.bot.loop.create_task(self.bot.type_for(channel=ctx.channel, duration=1))

            command = GwenCommand(
                cmd=GwenCommands.Search,
                data={
                    'keyword': self.control_data[ctx.guild.id].last_search_keyword,
                    'page_token': self.control_data[ctx.guild.id].last_search_results.next_page_token
                }
            )
            results = await self.bot.handle_queue_command(command=command)
            self.control_data[ctx.guild.id].last_search_results = results
            self.bot.loop.create_task(self.display_results(message=ctx.message, results=results, searching_message=ctx.message))

    async def prev(self, ctx: commands.Context):
        if self.control_data[ctx.guild.id].last_search_results is not None and self.control_data[ctx.guild.id].last_search_results.prev_page_token is not None:
            self.bot.loop.create_task(self.bot.type_for(channel=ctx.channel, duration=1))

            command = GwenCommand(
                cmd=GwenCommands.Search,
                data={
                    'keyword': self.control_data[ctx.guild.id].last_search_keyword,
                    'page_token': self.control_data[ctx.guild.id].last_search_results.prev_page_token
                }
            )
            results = await self.bot.handle_queue_command(command=command)
            self.control_data[ctx.guild.id].last_search_results = results
            self.bot.loop.create_task(self.display_results(message=ctx.message, results=results, searching_message=ctx.message))

    async def get_stream_url(self, video_id: str):
        command = GwenCommand(cmd=GwenCommands.GetStreamURL, data={'video_id': video_id})
        stream_url = await self.bot.handle_queue_command(command=command)
        return stream_url

    async def play(self, ctx: commands.Context, result_number, user):
        text_channel = ctx.channel
        guild = text_channel.guild
        voice_channel = await self.find_user_voice_channel(guild=guild, user=user)
        if self.control_data[ctx.guild.id].last_search_results is None:
            self.bot.loop.create_task(text_channel.send('Search for something first, meow!'))
            return False
        elif result_number not in [f'{i}' for i in range(1, 6)]:
            self.bot.loop.create_task(text_channel.send(f'Stop being silly right meow! {result_number} isn\'t a valid search result and you know it! 😾'))
            return False
        elif voice_channel is None:
            self.bot.loop.create_task(text_channel.send('You aren\'t in a voice channel right meow! 🧶'))
            return False
        else:
            stream_url = await self.get_stream_url(video_id=self.control_data[ctx.guild.id].last_search_results.results[int(result_number)].video_id)
            probe_data: dict = await self.bot.handle_queue_command(command=GwenCommand(cmd=GwenCommands.Probe, data={'ffmpeg_path': self.bot.ffmeg_path.as_posix(), 'url': stream_url}))
            audio_source = FFmpegOpusAudio(stream_url, executable=self.bot.ffmeg_path.as_posix(), bitrate=probe_data['bitrate'], codec=probe_data['codec'], **self.FFMPEG_OPT)
            voice_client = await self.join_voice(channel=voice_channel)
            await self.cancel_leave_voice_timer(guild_id=ctx.guild.id)
            if voice_client.is_playing():
                voice_client.stop()
            voice_client.play(source=audio_source, after=lambda e: self.bot.loop.create_task(self.done_playing(voice_client=voice_client)))
            self.bot.loop.create_task(self.send_new_stop_button(guild_id=guild.id, channel=text_channel))
            return True

    @commands.command(name='play', aliases=['p'], help='Plays the audio of the YouTube video from the given URL | p')
    async def play_url(self, ctx: commands.Context, url: str):
        """Plays the audio from the specific YouTube URL provided"""
        text_channel = ctx.channel
        guild = text_channel.guild
        voice_channel = await self.find_user_voice_channel(guild=guild, user=ctx.message.author)
        if voice_channel is None:
            self.bot.loop.create_task(text_channel.send('You aren\'t in a voice channel right meow! 🧶'))
            return False
        command = GwenCommand(cmd=GwenCommands.GetVideoIDFromURL, data={'url': url})
        vid_id = await self.bot.handle_queue_command(command=command)
        if vid_id is None:
            return False

        stream_url, _ = await gather(
            self.get_stream_url(video_id=vid_id),
            self.cancel_leave_voice_timer(guild_id=ctx.guild.id)
        )
        
        probe_data: dict = await self.bot.handle_queue_command(command=GwenCommand(cmd=GwenCommands.Probe, data={'ffmpeg_path': self.bot.ffmeg_path.as_posix(), 'url': stream_url}))
        audio_source = FFmpegOpusAudio(stream_url, executable=self.bot.ffmeg_path.as_posix(), bitrate=probe_data['bitrate'], codec=probe_data['codec'], **self.FFMPEG_OPT)
        voice_client: VoiceClient = await self.join_voice(channel=voice_channel)
        voice_client.play(source=audio_source, after=lambda e: self.bot.loop.create_task(self.done_playing(voice_client=voice_client)))
        self.bot.loop.create_task(self.send_new_stop_button(guild_id=guild.id, channel=text_channel))
        return True

    async def add_to_queue(self, ctx: commands.Context, track_url: str, title: str, channel: str):
        self.track_queue[ctx.guild.id].append({'url': track_url, 'title': title, 'channel': channel})
        self.bot.loop.create_task(ctx.send(content=title + ' added to queue! ✔️'))

    async def play_from_queue(self, voice_client: VoiceClient):
        if voice_client is None:
            return False
        if len(self.track_queue[voice_client.guild.id]) > 0:
            await self.cancel_leave_voice_timer(guild_id=voice_client.guild.id)
            track = self.track_queue[voice_client.guild.id].pop(0)
            probe_data: dict = await self.bot.handle_queue_command(command=GwenCommand(cmd=GwenCommands.Probe, data={'ffmpeg_path': self.bot.ffmeg_path.as_posix(), 'url': track['url']}))
            audio_source = FFmpegOpusAudio(track['url'], executable=self.bot.ffmeg_path.as_posix(), bitrate=probe_data['bitrate'], codec=probe_data['codec'], **self.FFMPEG_OPT)
            voice_client.play(source=audio_source, after=lambda e: self.bot.loop.create_task(self.done_playing(voice_client=voice_client)))
            return True
        return False

    async def done_playing(self, voice_client: VoiceClient):
        if len(self.track_queue[voice_client.guild.id]) > 0:
            await self.play_from_queue()
        else:
            self.leave_voice_timer[voice_client.guild.id] = self.bot.loop.call_later(5 * 60, self.bot.loop.create_task, self.leave_voice(voice_client=voice_client))
            await self.delete_current_stop_button(guild_id=voice_client.guild.id)

    @commands.command(help='Stops all currently playing audio while saving the queue')
    async def stop(self, ctx: commands.Context):
        """Stops all currently playing audio while saving the queue"""
        ctx.voice_client.stop()
        await self.delete_current_stop_button(guild_id=ctx.guild.id)

    @commands.command(help='Forces Gwen to stop playing audio and leave the voice channel she is currently in')
    async def leave(self, ctx: commands.Context):
        """Forces Gwen to stop playing audio and leave the voice channel she is currently in"""
        await self.leave_voice(voice_client=ctx.voice_client)
        await self.delete_current_stop_button(guild_id=ctx.guild.id)

    @commands.command(aliases=['sq'], help='Displays all content currently in the queue | sq')
    async def show_queue(self, ctx: commands.Context):
        """Displays all content currently in queue"""
        if len(self.track_queue[ctx.guild.id]) == 0:
            self.bot.loop.create_task(ctx.send('Nothing is in queue right meow! 😼', reference=ctx.message))
        else:
            tracks = []
            for idx, track in enumerate(self.track_queue[ctx.guild.id], 1):
                tracks.append(f'   {idx}'.rjust(3) + '. ' + track['title'] if len(track['title']) < 70 else (track['title'][0:67] + '...'))
            self.bot.loop.create_task(ctx.send(content='Current Queue:\n' + '\n'.join(tracks), reference=ctx.message))

    @commands.command(aliases=['eq'], help='Empties the queue | eq')
    async def empty_queue(self, ctx: commands.Context):
        """Empties the queue"""
        view = View(timeout=60)
        yes_btn = Button(style=ButtonStyle.green, label='Yes ✔️', custom_id='btn_yes_empty_q', url=None)
        no_btn = Button(style=ButtonStyle.red, label='No 🛑', custom_id='btn_no_empty_q', url=None)
        view.add_item(yes_btn)
        view.add_item(no_btn)
        await ctx.send(content='Are you sure you want to remove everything from the queue right meow? 🙀', view=view, ephemeral=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: Interaction):
        ctx: commands.Context = await self.bot.get_context(interaction.message)
        if interaction.data['custom_id'] == 'btn_yes_empty_q':
            await interaction.response.send_message(content=f'🚨 Emptying queue because {interaction.user.display_name} told me to! 🚨')
            self.track_queue[ctx.guild.id].clear()
        elif interaction.data['custom_id'] == 'btn_no_empty_q':
            await interaction.response.defer()
        elif interaction.data['custom_id'] == 'btn_stop' and ctx.message.id == self.control_data[ctx.guild.id].current_stop_msg.id:
            await interaction.response.defer()
            await self.stop(ctx)
        elif ctx.message.id == self.control_data[ctx.guild.id].current_control_msg_id and interaction.data['custom_id'] == 'btn_next':
            await interaction.response.defer()
            await self.next(ctx)
        elif ctx.message.id == self.control_data[ctx.guild.id].current_control_msg_id and interaction.data['custom_id'] == 'btn_prev':
            await interaction.response.defer()
            await self.prev(ctx)
        elif ctx.message.id == self.control_data[ctx.guild.id].current_control_msg_id:
            is_playing = False
            if ctx.voice_client is not None:
                is_playing = ctx.voice_client.is_playing()
            if 'btn_play_' in interaction.data['custom_id'] or ('btn_queue_' in interaction.data['custom_id'] and len(self.track_queue[ctx.guild.id]) == 0 and is_playing is False):
                await interaction.response.defer()
                result_number = interaction.data['custom_id'][-1]
                await self.play(ctx, result_number=result_number, user=interaction.user)
            elif 'btn_queue_' in interaction.data['custom_id']:
                await interaction.response.defer()
                result_number = int(interaction.data['custom_id'][-1])
                url = await self.get_stream_url(video_id=self.control_data[ctx.guild.id].last_search_results.results[result_number].video_id)
                await self.add_to_queue(ctx=ctx, track_url=url, title=self.control_data[ctx.guild.id].last_search_results.results[result_number].title, channel=self.control_data[ctx.guild.id].last_search_results.results[result_number].channel)
        else:
            print('\n')
            print(interaction.data)
            print('\n')
            await interaction.response.defer()

    @commands.command(aliases=['hi'], help='Says hello to you or someone else. | hi')
    async def hello(self, ctx: commands.Context, *, member: Member = None):
        """Says hello"""
        member = member or ctx.author
        await ctx.send(f'Meow meow, {member.display_name}!')
