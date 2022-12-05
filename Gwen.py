from asyncio import run as run_async
from logging import StreamHandler, Formatter, getLogger, DEBUG
import multiprocessing as mp
import atexit
from pathlib import WindowsPath
import signal
from typing import Union
from dark_music_bot.gwenbot import GwenBot, SECRETS, intents
from dark_music_bot.gwen_command import GwenCommand, GwenCommands
from dark_music_bot.gwen_worker import worker_proc


bot_process:  Union[mp.Process, None] = None
worker_process: Union[mp.Process, None] = None
comm_queue = mp.Queue()
data_queue = mp.Queue()


def graceful_shutdown(*args, **kwargs) -> None:
    comm_queue.put(GwenCommand(cmd=GwenCommands.Stop))
    try:
        bot_process.join(timeout=30)
    except:
        pass
    if bot_process.is_alive():
        bot_process.kill()
    try:
        worker_process.join(timeout=30)
    except:
        pass
    if worker_process.is_alive():
        worker_process.kill()


def gwenbot_proc(comm_queue: mp.Queue, data_queue: mp.Queue):
    handler = StreamHandler()
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
    handler.setFormatter(formatter)
    logger = getLogger()
    logger.setLevel(DEBUG)
    logger.addHandler(handler)

    async def run_gwen():
        debug_guilds = [
            972635478236995654,
            970713800732991488,
            943641153310453810,
            956768188601876480
        ]
        gwen_bot = GwenBot(comm_queue=comm_queue, data_queue=data_queue, ffmeg_path=WindowsPath(r'./ffmpeg/bin/ffmpeg.exe').absolute(), command_prefix=['/gwen ', '/g:'], application_id=SECRETS['app_id'], intents=intents, debug_guilds=debug_guilds)
        await gwen_bot.start(token=SECRETS['token'])
    try:
        run_async(run_gwen())
    except KeyboardInterrupt:
        comm_queue.put(GwenCommand(cmd=GwenCommands.Stop))
        return


if __name__ == '__main__':
    worker_process = mp.Process(target=worker_proc, name='GwenBot-Worker', args=(comm_queue, data_queue))
    bot_process = mp.Process(target=gwenbot_proc, name='GwenBot-Main', args=(comm_queue, data_queue))
    
    atexit.register(graceful_shutdown, bot_process=bot_process, worker_process=worker_process)
    signal.signal(signalnum=signal.SIGINT, handler=graceful_shutdown)

    worker_process.start()
    bot_process.start()
    bot_process.join()
