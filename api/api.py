import flask
from flask_cors import CORS, cross_origin
import uuid
from pathlib import Path
import os
import pytz
import json
import argparse
import threading
import datetime as dt
from util.twitch import TwitchAPI
from util.twitch import TWITCH_API_TIME_FORMAT
from util.at_five import *


class API_DataStore():
  TWITCH_API = None
  LOCAL_TZ = None
  DATA_TIMEOUT = 6000

  RESULTS_FILEPATH = "./results.csv"
  RESULTS = dict()
  RESULTS_AGE = None

data = API_DataStore()

app = flask.Flask(__name__)
cors = CORS(app)
app.config["CORS_HEADERS"] = 'Content-Type'

def update_results():
  data.RESULTS = get_at_five_results(data.TWITCH_API, data.RESULTS_FILEPATH, data.LOCAL_TZ)
  save_at_five_results(data.RESULTS, data.RESULTS_FILEPATH)

  data.RESULTS_AGE = dt.datetime.now()

def calc_record():
  ontime = 0
  late = 0
  total = 0
  for d, r in data.RESULTS.items():
    total += 1
    if r[0]:
      ontime += 1
    else:
      late += 1
  return (ontime, late, total)

@app.route('/', methods=['GET'])
@cross_origin()
def home():
  return f"""<h1>LusciousLollipop's LiveAtFive API.</h1>"""

@app.route('/api/v1/record', methods=['GET'])
@cross_origin()
def get_record():
  if (data.RESULTS_AGE is None) or ((dt.datetime.now() - data.RESULTS_AGE).total_seconds() > data.DATA_TIMEOUT):
    update_results()
  ot, l, t = calc_record()
  resp = {
    'on-time': ot,
    'late': l,
    'total': t
  }
  return flask.jsonify(resp)

@app.route('/api/v1/history', methods=['GET'])
@cross_origin()
def get_history():
  if (data.RESULTS_AGE is None) or ((dt.datetime.now() - data.RESULTS_AGE).total_seconds() > data.DATA_TIMEOUT):
    update_results()

  streams = dict()
  for k, v in data.RESULTS.items():
    streams[k] = dict()
    streams[k]["on_time"] = v[0]
    streams[k]["time"] = v[1].isoformat()

  resp = { 'streams': streams }

  return flask.jsonify(resp)

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--host', '-i', default="127.0.0.1", help="API Host IP")
  parser.add_argument('--port', '-p', type=int, default=8080, help="API Port")
  parser.add_argument('--channel', '-c', default="itswill", help="Twitch channel name")
  parser.add_argument('--secrets', '-s', default="./secrets.json", help="JSON file with credentials")
  parser.add_argument('--timezone', '-t', default="America/Los_Angeles", help="Local timezone")
  parser.add_argument('--results', '-r', default="./results/results.csv", help="File to keep results in.")
  
  args = parser.parse_args()

  data.LOCAL_TZ = pytz.timezone(args.timezone)
  data.RESULTS_FILEPATH = args.results

  with open(args.secrets) as cred_file:
    cred_data = json.load(cred_file)
    data.TWITCH_API = TwitchAPI(cred_data["TWITCH"])

  channel_found = data.TWITCH_API.get_broadcaster_id(args.channel, set_default=True)
  if not channel_found:
    print(f"Failed to find {args.channel} in Twitch directory.")

  update_results()

  app.run(host=args.host, port=args.port, debug=False)