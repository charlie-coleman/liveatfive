import flask
from flask_cors import CORS, cross_origin
import uuid
from pathlib import Path
import pytz
import json
import argparse
import datetime as dt
from luscioustwitch import *
from util.at_five import *

class API_DataStore():
  ATFIVE_API = None

data = API_DataStore()

app = flask.Flask(__name__)
cors = CORS(app)
app.config["CORS_HEADERS"] = 'Content-Type'

@app.route('/', methods=['GET'])
@cross_origin()
def home():
  return f"""<h1>LusciousLollipop's LiveAtFive API.</h1>"""

@app.route('/api/v1/record', methods=['GET'])
@cross_origin()
def get_record():
  o, e, t = data.ATFIVE_API.calc_record()
  status, streak = data.ATFIVE_API.get_current_streak()
  if 'plaintext' in flask.request.args:
    return_str = f"{data.ATFIVE_API.get_when_live()} He has been early {e} times, on time {o} times, and late {t-o-e} times."
    if streak > 1:
      status_str = status.name.lower()
      return_str += f" He has been {status_str} {streak} streams in a row."
    
    return return_str
  else:
    resp = {
      'on-time': o,
      'early': e,
      'total': t,
      'streak': streak,
      'streak-status': status
    }
    return flask.jsonify(resp)

@app.route('/api/v1/history', methods=['GET'])
@cross_origin()
def get_history():
  data.ATFIVE_API.update_data_if_necessary()
  
  streams = dict()
  for k, v in data.ATFIVE_API.STATS.items():
    streams[k] = dict()
    streams[k]["on_time"] = v["on-time"]
    streams[k]["time"] = dt.datetime.strptime(v['datetime'], TWITCH_API_TIME_FORMAT).strftime("%H:%M:%S")

  resp = { 'streams': streams }

  return flask.jsonify(resp)

@app.route('/api/v1/live', methods=['GET'])
@cross_origin()
def get_live():
  data.ATFIVE_API.update_data_if_necessary()
    
  resp = { 'live' : 1 if data.ATFIVE_API.IS_LIVE else 0, 'waslive' : 1 if data.ATFIVE_API.WAS_LIVE else 0 }
  return flask.jsonify(resp)

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--host', '-i', default="127.0.0.1", help="API Host IP")
  parser.add_argument('--port', '-p', type=int, default=8080, help="API Port")
  parser.add_argument('--channel', '-c', default="itswill", help="Twitch channel name")
  parser.add_argument('--secrets', '-s', default="./secrets.json", help="JSON file with credentials")
  parser.add_argument('--timezone', '-t', default="America/Los_Angeles", help="Local timezone")
  parser.add_argument('--datapath', '-d', default="./data", help="File to keep results in.")
  
  args = parser.parse_args()

  with open(args.secrets) as cred_file:
    cred_data = json.load(cred_file)
    data.ATFIVE_API = AtFiveAPI(TwitchAPI(cred_data["TWITCH"]), creator=args.channel, tz=pytz.timezone(args.timezone))

  app.run(host=args.host, port=args.port, debug=True)