import requests
import argparse
import os
import unicodedata
import re
import urllib.parse
from datetime import datetime

TWITCH_API_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

class TwitchAPI:
  API_URL = "https://api.twitch.tv/helix"
  DEFAULT_BROADCASTER_ID = ""
  CLIENT_ID = ""
  GQL_ID = ""
  OAUTH = ""

  def __init__(self, credentials):
    self.GQL_ID = credentials["GQLID"]
    self.CLIENT_ID = credentials["CLIENTID"]
    self.OAUTH = credentials["OAUTH"]

  def get_headers(self):
    return { "Authorization": f"Bearer {self.OAUTH}", "Client-Id": self.CLIENT_ID }

  def get_broadcaster_id(self, broadcaster_name, set_default = True):
    url = f"{self.API_URL}/users?login={broadcaster_name}"
    headers = self.get_headers()
    r = requests.get(url, headers=headers)
    resp_json = r.json()
    broadcaster_id = None if ('data' not in resp_json or len(resp_json["data"]) < 1) else resp_json["data"][0]["id"]
    if broadcaster_id is not None and set_default:
      self.DEFAULT_BROADCASTER_ID = broadcaster_id
    return broadcaster_id

  def get_stream_info(self, broadcaster_id = "", live = True):
    bid = broadcaster_id if broadcaster_id != "" else self.DEFAULT_BROADCASTER_ID

    url = f"{self.API_URL}/streams/?user_id={bid}"
    if live:
      url += "&type=live"
    headers = self.get_headers()
    r = requests.get(url, headers=headers)
    resp_json = r.json()
    return resp_json['data']

  def get_broadcaster_live(self, broadcaster_id = ""):
    bid = broadcaster_id if broadcaster_id != "" else self.DEFAULT_BROADCASTER_ID
    stream_info = self.get_stream_info(bid)
    return (len(stream_info) > 0)

  def get_clips(self, limit = 10, broadcaster_id = "", start_time = None, end_time = None, after= ""):
    bid = broadcaster_id if broadcaster_id != "" else self.DEFAULT_BROADCASTER_ID

    url = f"{self.API_URL}/clips?broadcaster_id={bid}&first={limit}"
    if (start_time != None):
        url = url + f"&started_at={start_time.strftime(TWITCH_API_TIME_FORMAT)}"
    if (end_time != None):
        url = url + f"&ended_at={end_time.strftime(TWITCH_API_TIME_FORMAT)}"
    if (after != ""):
        url = url + f"&after={after}"
    
    headers = self.get_headers()
    r = requests.get(url, headers=headers)
    resp_json = r.json()
    return resp_json

  def get_all_clips(self, broadcaster_id = "", start_time = None, end_time = None, after= ""):
    all_clips = []
    while True:
      r = self.get_clips(25, broadcaster_id, start_time, end_time, after)

      if 'data' not in r:
        return all_clips
      else:
        for clip in r['data']:
          all_clips.append(clip)
      
      if 'cursor' not in r['pagination']:
        return all_clips
      else:
        after = r['pagination']['cursor']

  def get_videos(self, limit = 10, broadcaster_id = "", period = "all", vod_type = "archive", after= ""):
    bid = broadcaster_id if broadcaster_id != "" else self.DEFAULT_BROADCASTER_ID

    url = f"{self.API_URL}/videos?user_id={bid}&first={limit}&period={period}&type={vod_type}"
    if (after != ""):
        url = url + f"&after={after}"
    
    headers = self.get_headers()
    r = requests.get(url, headers=headers)
    resp_json = r.json()
    return resp_json

  def get_all_videos(self, broadcaster_id = "", period = "all", vod_type = "archive", after= ""):
    all_clips = []
    while True:
      r = self.get_videos(25, broadcaster_id, period=period, vod_type=vod_type, after=after)

      if 'data' not in r:
        return all_clips
      else:
        for vod in r['data']:
          all_clips.append(vod)
      
      if 'cursor' not in r['pagination']:
        return all_clips
      else:
        after = r['pagination']['cursor']

  def get_clip_info(self, clip_id):
    url = f"{self.API_URL}/clips?id={clip_id}"
    headers = self.get_headers()

    r = requests.get(url, headers=headers)
    resp_json = r.json()
    info = {} if ('data' not in resp_json or len(resp_json['data']) < 1) else resp_json['data'][0]
    return info

  def get_video_info(self, video_id):
    url = f"{self.API_URL}/videos?id={video_id}"
    headers = self.get_headers()

    r = requests.get(url, headers=headers)
    resp_json = r.json()
    info = {} if ('data' not in resp_json or len(resp_json['data']) < 1) else resp_json['data'][0]
    return info

  def populate_with_clip_info(self, clip_info, input_string):
    return input_string.format(id = clip_info["id"],
                               url = clip_info["url"],
                               embed_url = clip_info["embed_url"],
                               broadcaster_id = clip_info["broadcaster_id"],
                               broadcaster_name = clip_info["broadcaster_name"],
                               creator_id = clip_info["creator_id"],
                               creator_name = clip_info["creator_name"],
                               video_id = clip_info["video_id"],
                               game_id = clip_info["game_id"],
                               language = clip_info["language"],
                               title = clip_info["title"],
                               view_count = clip_info["view_count"],
                               created_at = clip_info["created_at"],
                               thumbnail_url = clip_info["thumbnail_url"],
                               duration = clip_info["duration"],
                               vod_offset = clip_info["vod_offset"],
                               clip_date = clip_info["created_at"][0:10])