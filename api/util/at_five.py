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
from util.twitch import TwitchAPI
from util.twitch import TWITCH_API_TIME_FORMAT

CSV_DELIM = ','
CSV_QUOTE = '|'

class Punctuality(Enum):
  LATE=0
  ONTIME=1
  EARLY=2
  def __lt__(self, other):
    if self.__class__ is other.__class__:
      return self.value < other.value
    return NotImplemented

class DeltaTemplate(Template):
    delimiter = "%"

def strfdelta(tdelta, fmt):
    d = {"D": tdelta.days}
    hours, rem = divmod(tdelta.seconds, 3600)
    _, hours_12hr = divmod(hours, 12)
    minutes, seconds = divmod(rem, 60)
    d["H"] = '{:02d}'.format(hours)
    d["h"] = '{}'.format(hours_12hr)
    d["M"] = '{:02d}'.format(minutes)
    d["S"] = '{:02d}'.format(seconds)
    t = DeltaTemplate(fmt)
    return t.substitute(**d)

def utc_to_local(utc_dt, local_tz):
  return utc_dt.replace(tzinfo=dt.timezone.utc).astimezone(tz=local_tz)

def is_five(start_time):
  if start_time < dt.time(16,45,0):
    return Punctuality.EARLY
  elif start_time >= dt.time(16,45,0) and start_time <= dt.time(17,15,0): 
    return Punctuality.ONTIME
  else:
    return Punctuality.LATE

def this_year(vod_date):
  return vod_date >= dt.date(2023, 1, 1) and vod_date <= dt.date(2023, 12, 31)

def get_at_five_results(twitch_api, results_file, local_tz):
  os.makedirs(os.path.dirname(results_file), exist_ok=True)
  Path(results_file).touch()

  at_five_results = dict()

  with open(results_file, 'r', newline='', encoding='utf-8') as resultscsv:
    results_reader = csv.reader(resultscsv, delimiter=CSV_DELIM, quotechar=CSV_QUOTE)
    for row in results_reader:
      at_five_results[row[0]] = (Punctuality(int(row[1])), dt.datetime.strptime(row[2], "%H:%M:%S").time())

  vods = twitch_api.get_all_videos()
  for vod in vods:
    vod_dt = utc_to_local(dt.datetime.strptime(vod["created_at"], TWITCH_API_TIME_FORMAT), local_tz)
    if this_year(vod_dt.date()):
      date_str = str(vod_dt.date())
      vod_time = vod_dt.time()
      if date_str in at_five_results:
        curr_val = at_five_results[date_str][0]
        new_val = is_five(vod_time)
        at_five_results[date_str] = (curr_val if new_val < curr_val else new_val, vod_time)
      else:
        at_five_results[date_str] = (is_five(vod_time), vod_time)

  return at_five_results

def save_at_five_results(results, results_file):
  with open(results_file, 'w', newline='', encoding='utf-8') as resultscsv:
    results_writer = csv.writer(resultscsv, delimiter=CSV_DELIM, quotechar=CSV_QUOTE, quoting=csv.QUOTE_MINIMAL)
    for k, v in results.items():
      results_writer.writerow([k, v[0].value, v[1]])

def calc_record(results):
  ontime = 0
  early = 0
  total = 0
  for d, r in results.items():
    total += 1
    if r[0] == Punctuality.ONTIME:
      ontime += 1
    elif r[0] == Punctuality.EARLY:
      early += 1
  return (ontime, early, total)

def get_current_streak(results):
  status = Punctuality.EARLY
  streak = 0

  stream_dates = list(results.keys())
  stream_dates.sort(reverse = True)
  
  status = results[stream_dates[0]][0]
  for stream in stream_dates:
    if status == results[stream][0]:
      streak += 1
    else:
      break

  return (status, streak)