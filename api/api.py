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
  weekday = -1
  if 'weekday' in flask.request.args:
    weekdaystr = flask.request.args['weekday'].lower()
    if weekdaystr in ['m', 'mon', 'monday', '0']:
      weekday = 0
    elif weekdaystr in ['t', 'tues', 'tuesday', '1']:
      weekday = 1
    elif weekdaystr in ['w', 'wed', 'wednesday', '2']:
      weekday = 2
    elif weekdaystr in ['th', 'thurs', 'thursday', '3']:
      weekday = 3
    elif weekdaystr in ['f', 'fri', 'friday', '4']:
      weekday = 4
    elif weekdaystr in ['s', 'sat', 'saturday', '5']:
      weekday = 5
    elif weekdaystr in ['su', 'sun', 'sunday', '6']:
      weekday = 6
    
  o, e, t = data.ATFIVE_API.get_record(day = weekday)
  status, streak = data.ATFIVE_API.get_current_streak(day = weekday)
  if 'plaintext' in flask.request.args:
    return_str = f"{data.ATFIVE_API.get_when_live()} He has been early {e} times, on time {o} times, and late {t-o-e} times."
    if streak > 1:
      status_str = Punctuality(status).name.lower()
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
  
  weekday = -1
  if 'weekday' in flask.request.args:
    weekdaystr = flask.request.args['weekday'].lower()
    if weekdaystr in ['m', 'mon', 'monday', '0']:
      weekday = 0
    elif weekdaystr in ['t', 'tues', 'tuesday', '1']:
      weekday = 1
    elif weekdaystr in ['w', 'wed', 'wednesday', '2']:
      weekday = 2
    elif weekdaystr in ['th', 'thurs', 'thursday', '3']:
      weekday = 3
    elif weekdaystr in ['f', 'fri', 'friday', '4']:
      weekday = 4
    elif weekdaystr in ['s', 'sat', 'saturday', '5']:
      weekday = 5
    elif weekdaystr in ['su', 'sun', 'sunday', '6']:
      weekday = 6
  
  resp = { 'streams': {} }
  if weekday == -1:
    resp['streams'] = data.ATFIVE_API.STATS
  else:
    resp['streams'] = dict(filter(lambda kvp: kvp[1]['weekday'] == weekday, data.ATFIVE_API.STATS.items()))

  return flask.jsonify(resp)

@app.route('/api/v1/live', methods=['GET'])
@cross_origin()
def get_live():
  data.ATFIVE_API.update_data_if_necessary()
    
  resp = { 'live' : 1 if data.ATFIVE_API.IS_LIVE else 0, 'waslive' : 1 if data.ATFIVE_API.WAS_LIVE else 0 }
  return flask.jsonify(resp)

@app.route('/api/v1/when', methods=['GET'])
@cross_origin()
def get_when():
  avg_live_time = data.ATFIVE_API.get_average_live_time()
  return { 'average': avg_live_time.strftime("%H:%M:%S") }

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