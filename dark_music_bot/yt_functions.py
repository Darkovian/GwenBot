from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass, field
from typing import List, Union

import googleapiclient.discovery
import googleapiclient.errors
import pytube
import requests
from pytube import request
from pytube.innertube import InnerTube

from dark_music_bot.yt_results import YTResultItem, YTResults

scopes = ['https://www.googleapis.com/auth/youtube.readonly']

# YouTube on TV client secrets
_client_id = '861556708454-d6dlm3lh05idd8npek18k6be8ba3oc68.apps.googleusercontent.com'
_client_secret = 'SboVhoG9s0rNafixCSGGKXAT'

API_KEY = None

@dataclass(slots=True)
class YTStream:
    codec: Union[str, None] = None
    bitrate: Union[int, None] = None
    mime_type: Union[str, None] = None
    url: Union[str, None] = field(default=None, repr=False)
    audio_sample_rate: Union[int, None] = field(default=None, repr=False)

    @staticmethod
    def from_streaming_data(data: dict) -> YTStream:
        _mc: str = data['mimeType'].split('; codecs=')
        if 'audio' not in _mc[0]:
            raise Exception()
        mime_type = _mc[0].split('/')[1]
        codec = _mc[1].strip('"')
        return YTStream(codec=codec, bitrate=data['bitrate'], mime_type=mime_type, url=data['url'], audio_sample_rate=int(data.get('audioSampleRate')) if data.get('audioSampleRate') is not None else None)


def get_yt_resource() -> googleapiclient.discovery.Resource:
    global API_KEY
    if API_KEY is None:
        with open('api_key.secret', 'r') as fh:
            API_KEY = fh.read()
    api_service_name = 'youtube'
    api_version = 'v3'
    yt = googleapiclient.discovery.build(api_service_name, api_version, developerKey=API_KEY)
    return yt


def check_oauth() -> bool:
    innertube = InnerTube(client='ANDROID', use_oauth=True, allow_cache=True)
    if innertube.access_token:
        innertube.refresh_bearer_token()
    else:
        start_time = int(time.time() - 30)
        data = {
            'client_id': _client_id,
            'scope': 'https://www.googleapis.com/auth/youtube'
        }
        response = request._execute_request(
            'https://oauth2.googleapis.com/device/code',
            'POST',
            headers={
                'Content-Type': 'application/json'
            },
            data=data
        )
        response_data = json.loads(response.read())
        verification_url = response_data['verification_url']
        user_code = response_data['user_code']
        
        os.system(f'start /wait cmd /c "echo Please open {verification_url} and input code {user_code} & set /p=Press ENTER when you have completed this step"')

        data = {
            'client_id': _client_id,
            'client_secret': _client_secret,
            'device_code': response_data['device_code'],
            'grant_type': 'urn:ietf:params:oauth:grant-type:device_code'
        }
        response = request._execute_request(
            'https://oauth2.googleapis.com/token',
            'POST',
            headers={
                'Content-Type': 'application/json'
            },
            data=data
        )
        response_data = json.loads(response.read())

        innertube.access_token = response_data['access_token']
        innertube.refresh_token = response_data['refresh_token']
        innertube.expires = start_time + response_data['expires_in']
        innertube.cache_tokens()


def do_search(yt: googleapiclient.discovery.Resource, keyword: str, max_results: int = 5, page_token: str = None) -> YTResults:
    yt_results = YTResults()

    if page_token:
        response = yt.search().list(q=keyword, part='snippet', type='video', maxResults=max_results, pageToken=page_token).execute()
    else:
        response = yt.search().list(q=keyword, part='snippet', type='video', maxResults=max_results).execute()

    for idx, val in enumerate(response['items'], start=1):
        yt_result = YTResultItem(channel=val['snippet']['channelTitle'], title=val['snippet']['title'], video_id=val['id']['videoId'], img=val['snippet']['thumbnails']['default']['url'])
        yt_results.results[idx] = yt_result

    for idx in yt_results.results.keys():
        vid_data = pytube.YouTube(url='https://youtu.be/' + yt_results.results[idx].video_id, use_oauth=True, allow_oauth_cache=True)
        yt_results.results[idx].length = f'{math.floor(vid_data.length / 60)}:' + f'{vid_data.length % 60:02}'
        img_response = requests.get(yt_results.results[idx].img)
        yt_results.results[idx].img_data = img_response.content

    yt_results.next_page_token = response['nextPageToken'] if 'nextPageToken' in response.keys() else None
    yt_results.prev_page_token = response['prevPageToken'] if 'prevPageToken' in response.keys() else None
    return yt_results


def get_video_details_by_id(yt: googleapiclient.discovery.Resource, id: str) -> dict:
    response = yt.videos().list(part='snippet,contentDetails', id=id).execute()
    video_dict = response['items'][0]
    item_output = {'channel': video_dict['snippet']['channelTitle'], 'title': video_dict['snippet']['title'], 'img': video_dict['snippet']['thumbnails']['default']['url']}
    return item_output


def parse_streaming_data(data: dict) -> List[YTStream]:
    audio_streams = []
    for stream in data['formats']:
        try:
            current_stream = YTStream.from_streaming_data(stream)
            audio_streams.append(current_stream)
        except:
            continue
    for stream in data['adaptiveFormats']:
        try:
            current_stream = YTStream.from_streaming_data(stream)
            audio_streams.append(current_stream)
        except:
            continue
    return audio_streams


def get_stream_url(video_id: str) -> str:
    itube = InnerTube(client='ANDROID')
    resp = itube.player(video_id=video_id)
    streams = parse_streaming_data(resp['streamingData'])
    streams: List[YTStream] = sorted(streams, key=lambda x: x.bitrate, reverse=True)
    return streams[0].url


if __name__ == '__main__':
    print(get_stream_url(video_id='ouN4ok_gwOY'))
