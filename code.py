import os, time, ssl, json
import board
import wifi, socketpool
import adafruit_requests
import displayio
from adafruit_display_text import bitmap_label
import terminalio

import time, rtc, socketpool, wifi
import adafruit_ntp

import rtc
import adafruit_ntp

# after wifi is up:
pool = socketpool.SocketPool(wifi.radio)
ntp = adafruit_ntp.NTP(pool, server="pool.ntp.org", tz_offset=-4)  # adjust offset for your tz
rtc.RTC().datetime = ntp.datetime

print("time synced:", time.localtime())

import displayio
import terminalio
from adafruit_display_text import bitmap_label
import board, time

# colors
RED   = 0xFF0000
YEL   = 0xFFFF00
GRN   = 0x00FF00
WHITE = 0xFFFFFF

display = board.DISPLAY
group = displayio.Group()
try:
    display.root_group = group   # cp9+
except AttributeError:
    display.show(group)          # cp8-

def _clr(mins):
    if mins <= 4:  return RED
    if mins <= 10: return YEL
    return GRN

def _add_label(x, y, text, color, scale=3, anchor="mid"):
    lbl = bitmap_label.Label(terminalio.FONT, text=text, color=color, scale=scale)
    # crude anchoring
    if anchor == "mid":
        lbl.anchor_point = (0.5, 0.5)
    elif anchor == "left":
        lbl.anchor_point = (0.0, 0.5)
    elif anchor == "right":
        lbl.anchor_point = (1.0, 0.5)
    lbl.anchored_position = (x, y)
    group.append(lbl)
    return lbl

def _fmt_time_hhmm(t):
    h = t.tm_hour
    m = t.tm_min
    return "{}:{:02d}".format(h, m)

def render_times_line(y, stop_id, head_substr):
    # fetch 3 etas (mins)
    etas = fetch(stop_id, head_substr)  # returns list of (mins, head, dir)
    mins = [e[0] for e in etas][:3]
    while len(mins) < 3:
        mins.append(None)  # pad

    # compute three evenly spaced x positions
    w = display.width
    x1 = w * 1 // 6
    x2 = w * 3 // 6
    x3 = w * 5 // 6
    xs = (x1, x2, x3)

    for i, mm in enumerate(mins):
        if mm is None:
            txt, col = "--", WHITE
        else:
            txt = "DUE" if mm <= 0 else "{}".format(mm)
            col = _clr(mm)
        _add_label(xs[i], y, txt, col, scale=3, anchor="mid")

API = "https://api-v3.mbta.com/predictions"
ROUTE = os.getenv("MBTA_ROUTE") or "109"
STOP_A = os.getenv("STOP_BEACON_WASH")     # to harvard
STOP_B = os.getenv("STOP_WASH_CALDWELL")   # to linden
HEADERS = {}
key = os.getenv("MBTA_API_KEY")
if key:
    HEADERS["x-api-key"] = key

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

display = board.DISPLAY  # tft feather esp32-s3 builtin
group = displayio.Group()
display.root_group = group

def line(y, text):
    lbl = bitmap_label.Label(terminalio.FONT, text=text)
    lbl.x = 2
    lbl.y = y
    group.append(lbl)

# replace your fetch() with this
def fetch(stop_id, want_headsign):
    url = ("{}?filter[route]={}&filter[stop]={}&sort=departure_time"
           "&include=trip&page[limit]=12").format(API, ROUTE, stop_id)
    r = requests.get(url, headers=HEADERS, timeout=5)
    data = r.json(); r.close()

    # build trip id -> headsign
    heads = {}
    for inc in data.get("included", []):
        if inc.get("type") == "trip":
            heads[inc["id"]] = (inc["attributes"].get("headsign") or "").lower()

    out, now = [], time.time()
    for p in data.get("data", []):
        attr = p["attributes"]
        dep = attr.get("departure_time") or attr.get("arrival_time")
        if not dep:
            continue
        Y,M,D,h,m,s = [int(x) for x in (dep[:19]
                        .replace("T"," ").replace("-"," ").replace(":"," ").split())]
        epoch = time.mktime((Y,M,D,h,m,s,-1,-1,-1))
        mins = round((epoch - now)/60)
        if mins < -1:
            continue

        trip = p["relationships"].get("trip", {}).get("data", {})
        head = heads.get(trip.get("id",""), "")
        if want_headsign not in head:
            continue  # <- keep only the direction you actually want

        out.append((mins, head, attr.get("direction_id")))
    out.sort(key=lambda x: x[0])
    return out[:3]

display = board.DISPLAY
group = displayio.Group()
try:
    display.root_group = group
except AttributeError:
    display.show(group)

def _clr(mins):
    if mins <= 4:  return RED
    if mins <= 10: return YEL
    return GRN

def _add_label(x, y, text, color=WHITE, scale=3, anchor="mid"):
    lbl = bitmap_label.Label(terminalio.FONT, text=text, color=color, scale=scale)
    if anchor == "mid":
        lbl.anchor_point = (0.5, 0.5)
    elif anchor == "left":
        lbl.anchor_point = (0.0, 0.5)
    elif anchor == "right":
        lbl.anchor_point = (1.0, 0.5)
    lbl.anchored_position = (x, y)
    group.append(lbl)
    return lbl

def render_times_line(y, stop_id, head_substr, line1, line2):
    # vertical center reference
    label_center = y - 4   # shift up 4px
    _add_label(5, label_center - 8, line1, WHITE, scale=2, anchor="left")
    _add_label(15, label_center + 8, line2, WHITE, scale=2, anchor="left")

    etas = fetch(stop_id, head_substr)
    mins = [e[0] for e in etas][:3]
    while len(mins) < 3:
        mins.append(None)

    # shift times up 4px and space them wider
    y = y - 12
    xs = (display.width - 100, display.width - 55, display.width - 10)
    for i, mm in enumerate(mins):
        if mm is None:
            txt, col = "--", WHITE
        else:
            txt = "{}".format(mm)
            col = _clr(mm)
        _add_label(xs[i], y, txt, col, scale=3, anchor="right")

def render_screen():
    global group
    group = displayio.Group()
    try:
        display.root_group = group
    except AttributeError:
        display.show(group)

    # row 1: harvard
    render_times_line(40, STOP_A, "harvard", "109 to", "Harvard")

    # row 2: linden
    render_times_line(100, STOP_B, "linden", "109 to", "Linden")

    # clock stays put
    now = time.localtime()
    clock = "{}:{:02d}".format(now.tm_hour, now.tm_min)
    _add_label(display.width - 5, display.height - 15, clock,
               WHITE, scale=2, anchor="right")


render_screen()

# refresh every 20s, reconnect if needed
while True:
    try:
        if not wifi.radio.ipv4_address:
            wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"),
                               os.getenv("CIRCUITPY_WIFI_PASSWORD"))
        render_screen()
    except Exception as e:
        print("err:", e)
        time.sleep(3)
        continue
    time.sleep(20)
