var apiUrl = "http://127.0.0.1:8080"

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

  console.log(respJson);

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
    
    if (value["on_time"] == 2)
    {
      liveString = "EARLY&nbsp;&nbsp;"
    }
    else if (value["on_time"] == 1)
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

$(window).on('load', function() {
  var reqUrl = apiUrl + "/api/v1/record";
  xmlHttpRequestAsync("GET", reqUrl, populateRecord);
  reqUrl = apiUrl + "/api/v1/history"
  xmlHttpRequestAsync("GET", reqUrl, populateHistory);  
});