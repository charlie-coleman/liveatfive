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

def utc_to_local(utc_dt, local_tz):
  return utc_dt.replace(tzinfo=dt.timezone.utc).astimezone(tz=local_tz)

def is_five(start_time):
  if start_time < dt.time(16,45):
    return Punctuality.EARLY
  elif start_time >= dt.time(16,45) and start_time <= dt.time(17,15): 
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
      at_five_results[row[0]] = (Punctuality(int(row[1])), row[2])

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