import http.client, urllib
from keys import token, user
import geocoder

g = geocoder.ip('me')


def push_notification():
    conn = http.client.HTTPSConnection("api.pushover.net:443")
    conn.request("POST", "/1/messages.json",
      urllib.parse.urlencode({
        "token": token,
        "user": user,
        "message": "26.65542285967638, 87.30194645490855, Itahari International College",
        "priority": 1,
        "sound": "Alarm"
      }), { "Content-type": "application/x-www-form-urlencoded" })
    conn.getresponse()

# push_notification()

def reminder_notification(text):
    conn = http.client.HTTPSConnection("api.pushover.net:443")
    conn.request("POST", "/1/messages.json",
      urllib.parse.urlencode({
        "token": token,
        "user": user,
        "message": f"{text}",
              }), { "Content-type": "application/x-www-form-urlencoded" })
    conn.getresponse()
