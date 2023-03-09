var DateTime = luxon.DateTime;

var apiUrl = "http://127.0.0.1:8080"
var goalTime = DateTime.fromObject({ hour: 17, minute: 0, second: 0 }, { zone: "America/Los_Angeles"});
var padTime = DateTime.fromObject({ hour: 17, minute: 15, second: 0 }, { zone: "America/Los_Angeles"});

var isLive = false;
var wasLive = false;

// First, checks if it isn't implemented yet.
if (!String.prototype.format) {
  String.prototype.format = function() {
    var args = arguments;
    return this.replace(/{(\d+)}/g, function(match, number) { 
      return typeof args[number] != 'undefined'
        ? args[number]
        : match
      ;
    });
  };
}

function xmlHttpRequestAsync(method, theUrl, callback)
{
  var xmlHttp = new XMLHttpRequest();
  xmlHttp.onreadystatechange = function() {
    if (xmlHttp.readyState == 4 && xmlHttp.status == 200)
    {
      callback(xmlHttp.responseText);
    }
  }
  xmlHttp.open(method, theUrl, true);
  xmlHttp.send(null);
}

function populateRecord(text)
{
  var respJson = JSON.parse(text);

  var statusString = "late";
  if (respJson['streak-status'] == 1)
  {
    statusString = "on time";
  }
  else if (respJson['streak-status'] == 2)
  {
    statusString = "early";
  }

  var recordDiv = `itswill has been on time for {0} out of the {1} streams since January 1st, 2023.
  <br>
  itswill has been early for {2} out of the {1} streams since January 1st, 2023
  <br>
  itswill has been {3} {4} times in a row.`.format(respJson["on-time"], respJson["total"], respJson["early"], statusString, respJson['streak']);
  $("#record").append(recordDiv);
}

function populateHistory(text)
{
  var respJson = JSON.parse(text);

  var dict = respJson['streams']
  idx = 0;
  for (var key in dict)
  {
    var value = null;
    if (dict.hasOwnProperty(key))
    {
      value = dict[key];
    }

    var liveString = ""
    
    if (value["on-time"] == 2)
    {
      liveString = "EARLY&nbsp;&nbsp;"
    }
    else if (value["on-time"] == 1)
    {
      liveString = "ON TIME"
    }
    else
    {
      liveString = "LATE&nbsp;&nbsp;&nbsp;"
    }

    $("#history").append(`<div class="history-entry" id="entry-{0}">{1}: {2} (went live at {3})</div>`.format(idx, key, liveString, value["time"]));

    idx++;
  }
}

function populateIsLive(text)
{
  var respJson = JSON.parse(text);
  isLive = (respJson['live'] == 1);
  wasLive = (respJson['waslive'] == 1);
  setIsLiveText();
}

function getTimeString(diffObj)
{
  var hourStr = diffObj['hours'].toString();
  var minStr  = diffObj['minutes'].toString().padStart(2, '0');
  var secStr  = diffObj['seconds'].toString().padStart(2, '0');
  
  var timeStr = "";
  if (diffObj['hours'] > 0)
  {
    timeStr = "{0}h {1}m {2}s".format(hourStr, minStr, secStr);
  }
  else if (diffObj['minutes'] > 0)
  {
    timeStr = "{0}m {1}s".format(minStr, secStr);
  }
  else
  {
    timeStr = "{0}s".format(secStr);
  }

  return timeStr;
}

function setIsLiveText()
{
  $("#islive").empty();
  var now = DateTime.local().setZone("America/Los_Angeles");

  if (isLive)
  {
    $("#islive").append(`He's live right now. Go watch.`);
  }
  else if (wasLive)
  {
    $("#islive").append(`Stream is over.`);
  }
  else if (now.toFormat('c') == 1)
  {
    $("#islive").append(`It's Monday. Chances of a stream are low.`);
  }
  else
  {
    if (goalTime > now)
    {
      var til5 = goalTime.diff(now, ['hours', 'minutes', 'seconds', 'milliseconds']).toObject();
      var timeStr = getTimeString(til5);
      $("#islive").append(`He <i>should</i> be live in {0}.`.format(timeStr));
    }
    else if (padTime > now)
    {
      var til515 = padTime.diff(now, ['hours', 'minutes', 'seconds', 'milliseconds']).toObject();
      var timeStr = getTimeString(til515);
      $("#islive").append(`Respect the 15 minute buffer. We still have {0} left before he's late.`.format(timeStr));
    }
    else
    {
      var since5 = now.diff(padTime, ['hours', 'minutes', 'seconds', 'milliseconds']).toObject();
      var timeStr = getTimeString(since5);
      $("#islive").append(`He <i>should've</i> been live {0} ago...`.format(timeStr));
    }
  }
}

function checkIsLive()
{
  var reqUrl = apiUrl + "/api/v1/live"
  xmlHttpRequestAsync("GET", reqUrl, populateIsLive);  
}

$(window).on('load', function() {
  var reqUrl = apiUrl + "/api/v1/record";
  xmlHttpRequestAsync("GET", reqUrl, populateRecord);
  reqUrl = apiUrl + "/api/v1/history"
  xmlHttpRequestAsync("GET", reqUrl, populateHistory);
  checkIsLive();

  var intervalId = setInterval(function() { checkIsLive(); }, 60000);
  var otherInterval = setInterval(function() { setIsLiveText(); }, 1);
});