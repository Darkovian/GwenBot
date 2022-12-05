from enum import Enum
from functools import partial
from json import loads
from multiprocessing import Queue
from os import makedirs
from os.path import join
from pathlib import WindowsPath
from queue import Queue
from re import IGNORECASE, Pattern, compile
from shutil import rmtree
from subprocess import check_output
from threading import Thread
from typing import Callable, List

from discord import Embed
from discord.ui import Button

from dark_music_bot.gwen_command import GwenCommand, GwenCommands
from dark_music_bot.yt_functions import (do_search, get_stream_url,
                                         get_video_details_by_id,
                                         get_yt_resource)
from dark_music_bot.yt_results import YTResults

REACTIONS = {
    '1': u'\u0031\uFE0F\u20E3',
    '2': u'\u0032\uFE0F\u20E3',
    '3': u'\u0033\uFE0F\u20E3',
    '4': u'\u0034\uFE0F\u20E3',
    '5': u'\u0035\uFE0F\u20E3',
    'N': u'\u25B6\uFE0F',
    'P': '◀️'
}


VID_ID_REGEX = compile(r'(?<=\?v=)[a-z0-9_-]+', IGNORECASE)


class ButtonStyle(Enum):
    primary = 1
    secondary = 2

    def __int__(self) -> int:
        return self.value


class ComponentType(Enum):
    action_row = 1
    button = 2
    select = 3
    input_text = 4

    def __int__(self):
        return self.value


def prepare_thumbnail_directory(id) -> WindowsPath:
    thumbnail_path = WindowsPath(f'./thumbnails/{id}').absolute()
    if thumbnail_path.exists():
        rmtree(thumbnail_path.as_posix())
    makedirs(thumbnail_path.as_posix())
    return thumbnail_path


def worker_do_search(cmd: GwenCommand) -> GwenCommand:
    """Handles the `do_search` yt_function and returns the dict to be put into the data_queue"""
    yt = get_yt_resource()
    cmd.result = do_search(yt=yt, keyword=cmd.data['keyword'], max_results=5, page_token=cmd.data['page_token'])
    return cmd


def worker_create_result_message_content(cmd: GwenCommand) -> GwenCommand:
    """Handles creating the content required by the `display_results` function of the `Music` cog"""
    thumbnail_path = prepare_thumbnail_directory(id=cmd.data['author_id'])
    results: YTResults = cmd.data['results']
    play_buttons = []
    queue_buttons = []
    embeds = []
    attachments = []
    result_keys: list = list(results.results.keys())

    for idx in result_keys:
        result_embed = Embed(title=REACTIONS[f'{idx}'] + '. ' + results.results[idx].title, type='rich')
        with open(join(thumbnail_path.as_posix(), f'{idx}.jpg'), mode='x+b') as fp:
            fp.write(results.results[idx].img_data)
        img_file = (join(thumbnail_path.as_posix(), f'{idx}.jpg'), f'{idx}.jpg')
        attachments.append(img_file)
        result_embed.set_thumbnail(url=f'attachment://{idx}.jpg')
        result_embed.add_field(name='Channel', value=results.results[idx].channel)
        result_embed.add_field(name='Length', value=results.results[idx].length)
        embeds.append(result_embed)
        play_btn = Button(style=ButtonStyle.primary, custom_id=f'btn_play_{idx}', url=None, disabled=False, label='Play: ' + results.results[idx].title if len('Play: ' + results.results[idx].title) < 40 else 'Play: ' + results.results[idx].title[0:37] + '...', emoji=REACTIONS[f'{idx}'], row=idx-1)
        play_btn._underlying.type = ComponentType.button
        play_buttons.append(play_btn)
        queue_btn = Button(style=ButtonStyle.secondary, custom_id=f'btn_queue_{idx}', url=None, disabled=False, label='Queue: ' + results.results[idx].title if len('Queue: ' + results.results[idx].title) < 40 else 'Queue: ' + results.results[idx].title[0:36] + '...', emoji=REACTIONS[f'{idx}'], row=idx-1)
        queue_btn._underlying.type = ComponentType.button
        queue_buttons.append(queue_btn)

    cmd.result = {
        'embeds': embeds,
        'files': attachments,
        'play_buttons': play_buttons,
        'queue_buttons': queue_buttons
    }
    return cmd


def worker_get_stream_url(cmd: GwenCommand) -> GwenCommand:
    """Handles getting the dtream url of a given youtube video by video id"""
    cmd.result = get_stream_url(video_id=cmd.data['video_id'])
    return cmd


def worker_get_video_id_from_url(cmd: GwenCommand, id_regex: Pattern = VID_ID_REGEX) -> GwenCommand:
    """Handles getting the video id from a given url"""
    ids = id_regex.findall(cmd.data['url'])
    cmd.result = ids[0] if ids else None
    return cmd


def worker_get_video_data(cmd: GwenCommand) -> GwenCommand:
    """Handles getting information about a video by video id"""
    yt = get_yt_resource()
    cmd.result = get_video_details_by_id(yt=yt, id=cmd.data['video_id'])
    return cmd


def worker_probe_video(cmd: GwenCommand) -> GwenCommand:
    exe: str = cmd.data['ffmpeg_path']
    exe = exe.replace('ffmpeg.exe', 'ffprobe.exe')
    args = [
            exe,
            '-v',
            'quiet',
            '-print_format',
            'json',
            '-show_streams',
            '-select_streams',
            'a:0',
            cmd.data['url'],
        ]
    output = check_output(args, timeout=20)
    codec = 'libopus'
    bitrate = 128

    if output:
        data = loads(output)
        streamdata = data['streams'][0]

        codec = streamdata.get('codec_name')
        bitrate = int(streamdata.get('bit_rate', 0))
        bitrate = max(round(bitrate / 1000), 512)

    cmd.result = {
        'codec': 'copy' if codec in ['opus', 'libopus'] else codec,
        'bitrate': bitrate
    }
    return cmd


def worker_ship(cmd: GwenCommand) -> GwenCommand:
    pass


def worker_do_and_submit(func: Callable[[], GwenCommand], data_queue: Queue) -> None:
    """A convenience function for running a callable (`func`) and putting the result into `data_queue`"""
    result = func()
    if result is not None:
        data_queue.put(result, block=True)


def worker_daemon_fn(input_queue: Queue, data_queue: Queue) -> None:
    """Takes jobs from `input_queue` and places the results into `data_queue`"""
    while True:
        _item = input_queue.get()
        if callable(_item):
            worker_do_and_submit(func=_item, data_queue=data_queue)
        input_queue.task_done()


def worker_proc(comm_queue: Queue, data_queue: Queue):
    """Handles starting and running the worker process, and manages the communication and work queues"""
    WORK_INPUT_QUEUE = Queue()
    MAX_DAEMON_THREADS = 8
    DAEMON_THREADS: List[Thread] = []
    COMMAND_MAPPING = {
        0: worker_do_search,
        1: worker_create_result_message_content,
        2: worker_get_stream_url,
        3: worker_get_video_id_from_url,
        4: worker_get_video_data,
        5: worker_ship,
        6: worker_probe_video
    }

    # Spawn MAX_DAEMON_THREADS number of worker threads to run the functions we'll be putting in queue
    for i in range(1, MAX_DAEMON_THREADS + 1):
        worker_daemon = Thread(target=worker_daemon_fn, name=f'GwenBot-Worker-Daemon-{i}', args=(WORK_INPUT_QUEUE, data_queue), daemon=True)
        worker_daemon.start()
        DAEMON_THREADS.append(worker_daemon)

    # If the stop command is rcvd or Ctrl-C is pressed the bot is shut down
    # Otherwise, run forever
    try:
        while True:
            current_cmd: GwenCommand = comm_queue.get()

            if current_cmd.cmd == GwenCommands.Stop:
                raise KeyboardInterrupt()

            # If the command is not `stop`, check COMMAND_MAPPING for a matching function
            # If a function is found, create a partial with cmd=current_cmd and add it to the work queue
            worker_func: Callable = COMMAND_MAPPING.get(current_cmd.cmd.value)
            if worker_func is not None:
                worker_func_partial = partial(worker_func, cmd=current_cmd)
                WORK_INPUT_QUEUE.put(worker_func_partial)

    except KeyboardInterrupt:
        exit()
