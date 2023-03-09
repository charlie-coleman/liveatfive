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

  var onTime = parseInt(respJson["on-time"]);
  var early = parseInt(respJson["early"]);
  var total = parseInt(respJson["total"]);
  var late = total - onTime - early;

  var recordDiv = `{0} on-time, {1} early, {2} late.`.format(onTime, early, late);
  $("#record").html(recordDiv);
}

function populateHistory(text)
{
  var respJson = JSON.parse(text);

  $("#history-table").html(`<tr class="table-header">
  <th>Date</th>
  <th>Time</th>
  <th>Offset</th>
  <th>Status</th>
</tr>`);

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
      liveString = "EARLY"
    }
    else if (value["on-time"] == 1)
    {
      liveString = "ON-TIME"
    }
    else
    {
      liveString = "LATE"
    }

    $("#history-table").append(`<tr>
  <th class="live-date">{0}</th>
  <th class="live-time">{1}</th>
  <th class="live-offset">{2}</th>
  <th class="live-status">{3}</th>
</tr>`.format(key, value["time"], value["offset"].toLocaleString(undefined, { maximumFractionDigits: 1, minimumFractionDigits: 1 }), liveString));

    idx++;
  }
}

function populateAverageTime(text)
{
  var respJson = JSON.parse(text);

  $("#avg-time").html(respJson["average"]);
}

function getWeekdaySelection() 
{
  return $("#weekday-select").find(":selected").val();
}

function updatePage()
{
  var reqUrl = apiUrl + "/api/v1/record?weekday=" + getWeekdaySelection();
  xmlHttpRequestAsync("GET", reqUrl, populateRecord);
  reqUrl = apiUrl + "/api/v1/history?weekday=" + getWeekdaySelection();
  xmlHttpRequestAsync("GET", reqUrl, populateHistory);
  reqUrl = apiUrl + "/api/v1/when"
  xmlHttpRequestAsync("GET", reqUrl, populateAverageTime);
}

$(window).on('load', function() {
  updatePage();

  $("#weekday-select").change(function() {
    updatePage()
  });
});