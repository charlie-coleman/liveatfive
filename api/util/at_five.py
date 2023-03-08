import argparse
import json
import os
import re
import requests
import unicodedata
import subprocess
import math
import csv
from pathlib import Path
import datetime as dt
import pytz
from string import Template
from enum import Enum
from luscioustwitch import *

CSV_DELIM = ','
CSV_QUOTE = '|'

class DeltaTemplate(Template):
    delimiter = "%"

def strfdelta(tdelta : dt.timedelta, fmt):
    d = {"D": tdelta.days}
    hours, rem = divmod(tdelta.seconds, 3600)
    _, hours_12hr = divmod(hours, 12)
    minutes, seconds = divmod(rem, 60)
    d["H"] = '{:02d}'.format(hours)
    d["HH"] = '{}'.format(hours_12hr)
    d["h"] = '{}'.format(hours)
    d["M"] = '{:02d}'.format(minutes)
    d["m"] = '{}'.format(minutes)
    d["S"] = '{:02d}'.format(seconds)
    d["s"] = '{}'.format(seconds)
    t = DeltaTemplate(fmt)
    return t.substitute(**d)
  
def smartfmtdelta(tdelta : dt.timedelta):
  hours, rem = divmod(tdelta.seconds, 3600)
  minutes, _ = divmod(rem, 60)
  
  if hours > 0:
    return strfdelta(tdelta, "%{h}h %{M}m %{S}s")
  elif minutes > 0:
    return strfdelta(tdelta, "%{m}m %{S}s")
  else:
    return strfdelta(tdelta, "%{s}s")

def utc_to_local(utc_dt : dt.datetime, local_tz):
  return utc_dt.replace(tzinfo=dt.timezone.utc).astimezone(tz=local_tz)

def timeadd(time1 : dt.time, time2 : dt.time):
  return (dt.datetime.combine(dt.date.today(), time1) + dt.datetime.combine(dt.date.today(), time2))

def timediff(time1 : dt.time, time2: dt.time):
  return (dt.datetime.combine(dt.date.today(), time1) - dt.datetime.combine(dt.date.today(), time2))

class Punctuality(int, Enum):
  LATE   = 0
  ONTIME = 1
  EARLY  = 2
  def __lt__(self, other):
    if self.__class__ is other.__class__:
      return self.value < other.value
    return NotImplemented
  
class AtFiveAPI():
  TWITCH_API : TwitchAPI = None
  DATA_PATH  : Path      = Path("./data")
  LOCAL_TZ               = pytz.timezone("America/Los_Angeles")
  VIDEO_FILE : Path      = DATA_PATH / "videos.json"
  VIDEOS     : dict      = { "list": [], "count": 0 }
  STATS_FILE : Path      = DATA_PATH / "stats.json"
  STATS      : dict      = {}
  
  USER_ID = ""
  
  GOAL_TIME = dt.time(17, 0, 0)
  BUFFER_MIN = 15
  
  IS_LIVE  = False
  WAS_LIVE = False
  
  DATA_TIMESTAMP = dt.datetime.now()
  DATA_TIMEOUT   = 60
  
  def __init__(self, twitch_api : TwitchAPI, datapath : Path = Path("./data"), tz = pytz.timezone("America/Los_Angeles"), creator = "itswill", start_time : dt.time = dt.time(17, 0, 0), buffer : int = 15):
    self.TWITCH_API = twitch_api
    self.DATA_PATH  = datapath if isinstance(datapath, Path) else Path(datapath)
    self.LOCAL_TZ   = tz
    
    os.makedirs(self.DATA_PATH, exist_ok = True)
    
    self.VIDEO_FILE = self.DATA_PATH / "videos.json"
    self.VIDEO_FILE.touch()
    self.STATS_FILE = self.DATA_PATH / "stats.json"
    self.STATS_FILE.touch()

    self.ONTIME_START = (dt.datetime.combine(dt.date.today(), self.GOAL_TIME) - dt.timedelta(minutes=self.BUFFER_MIN)).time()
    self.ONTIME_END = (dt.datetime.combine(dt.date.today(), self.GOAL_TIME) + dt.timedelta(minutes=self.BUFFER_MIN)).time()
    
    self.USER_ID = self.TWITCH_API.get_user_id(creator)
    if self.USER_ID == "":
      print(f"Failed to find {creator} in Twitch directory.")
      
    self._read_archived_data()
    self._fetch_twitch_data()
    self._save_data()
    
    self._check_is_live()
    self._check_was_live()
    
  def update_results(self):
    print("Updating results.")
    
    self._fetch_twitch_data()
    self._save_data()
    self._check_is_live()
    self._check_was_live()
    
  def update_data_if_necessary(self):
    if (self.DATA_TIMESTAMP is None) or ((dt.datetime.now() - self.DATA_TIMESTAMP).total_seconds() > self.DATA_TIMEOUT):
      self.DATA_TIMESTAMP = dt.datetime.now()
      self.update_results()

  def _is_five(self, start_time : dt.time):
    if start_time < self.ONTIME_START:
      return Punctuality.EARLY
    elif start_time >= self.ONTIME_START and start_time <= self.ONTIME_END: 
      return Punctuality.ONTIME
    else:
      return Punctuality.LATE

  def _this_year(self, vod_date):
    return vod_date >= dt.date(2023, 1, 1) and vod_date <= dt.date(2023, 12, 31)
  
  def _load_json(self, filepath, default = {}):
    with open(filepath, 'r') as jsonfile:
      try:
        return json.load(jsonfile)
      except:
        return default
      
  def _sort_data(self):
    self.STATS = dict(sorted(self.STATS.items(), reverse=True))
    self.VIDEOS["list"] = sorted(self.VIDEOS["list"], key=lambda x: dt.datetime.strptime(x["published_at"], TWITCH_API_TIME_FORMAT), reverse=True)
    self.VIDEOS["count"] = len(self.VIDEOS["list"])
    
  def _read_archived_data(self):
    self.VIDEOS = self._load_json(self.VIDEO_FILE, { "list": [], "count": 0 })
    self.STATS  = self._load_json(self.STATS_FILE)
    self._sort_data()

  def _fetch_twitch_data(self):
    video_params = {
      "user_id": self.USER_ID,
      "period": "all",
      "sort": "time",
      "type": "archive"
    }
    vods = self.TWITCH_API.get_all_videos(video_params)
    
    for vod in vods:
      vod_dt = utc_to_local(dt.datetime.strptime(vod["created_at"], TWITCH_API_TIME_FORMAT), self.LOCAL_TZ)
      if self._this_year(vod_dt.date()):
        if vod not in self.VIDEOS["list"]:
          self.VIDEOS["list"].append(vod)
          
        vod_date = vod_dt.date().isoformat()
        if vod_date not in self.STATS or self.LOCAL_TZ.localize(dt.datetime.strptime(self.STATS[vod_date]["datetime"], TWITCH_API_TIME_FORMAT), is_dst=None) > vod_dt:
          td = timediff(vod_dt.time(), self.GOAL_TIME)
          offset_seconds = td.seconds + (24.0*60.0*60.0*td.days)
          self.STATS[vod_date] = {
            "offset": (offset_seconds / 60.0),
            "on-time": self._is_five(vod_dt.time()).value,
            "datetime": vod_dt.strftime(TWITCH_API_TIME_FORMAT)
          }
        
    self._sort_data()
    
  def _save_data(self):
    with open(self.VIDEO_FILE, 'w') as videofile:
      videofile.write(json.dumps(self.VIDEOS, indent=2))
    with open(self.STATS_FILE, 'w') as statsfile:
      statsfile.write(json.dumps(self.STATS, indent=2))
  
  def _check_is_live(self):
    self.IS_LIVE = self.TWITCH_API.is_broadcaster_live(self.USER_ID)
    
  def _check_was_live(self):
    now = utc_to_local(dt.datetime.now(tz=dt.timezone.utc), self.LOCAL_TZ)
    self.WAS_LIVE = (now.strftime("%Y-%m-%d") in self.STATS)

  def calc_record(self):
    self.update_data_if_necessary()
    
    ontime = 0
    early = 0
    total = 0
    for _, stats in self.STATS.items():
      total += 1
      if stats["on-time"] == Punctuality.ONTIME:
        ontime += 1
      elif stats["on-time"] == Punctuality.EARLY:
        early += 1
    return (ontime, early, total)

  def get_current_streak(self):
    self.update_data_if_necessary()
    
    status = 0
    streak = 0
    
    for __, stats in self.STATS.items():
      if streak == 0:
        status = stats["on-time"]
      if status == stats["on-time"]:
        streak += 1
      else:
        break

    return (status, streak)

  def get_when_live(self):
    self.update_data_if_necessary()
    
    now = utc_to_local(dt.datetime.now(tz=dt.timezone.utc), self.LOCAL_TZ)
    whenLive = ""
    
    if self.IS_LIVE:
      whenLive = "itswill is live now."
    elif self.WAS_LIVE:
      whenLive = "Today's stream has ended."
    elif now.weekday() == 0:
      whenLive = "Probably no stream today BoyHowdyISureDoHateMondays ."
    elif now.time() < self.GOAL_TIME:
      timeStr = smartfmtdelta(timediff(self.GOAL_TIME, now.time()))
      whenLive = f"itswill should be live in {timeStr}."
    elif now.time() <= self.ONTIME_END:
      timeStr = smartfmtdelta(timediff(self.ONTIME_END, now.time()))
      whenLive = f"Respect the 15 minute buffer. He still has {timeStr} left."
    else:
      timeStr = smartfmtdelta(timediff(now.time(), self.ONTIME_END))
      whenLive = f"itswill should've been live {timeStr} ago."
    
    return whenLive
  