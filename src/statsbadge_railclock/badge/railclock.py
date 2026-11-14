"""The badge side of statsbadge-railclock: the Rail Clock, as a page.

After Network Rail's Rail Clock (Design Bridge and Partners, 2025), as the FireTVDeparture
departure board draws it in a tile: two red rings, each carrying one chevron of the double
arrow, with the time inside them. The outer chevron goes round clockwise and the inner one
anticlockwise, a turn a minute each. They meet as the double arrow at the top on the
minute, and again at the bottom on the half minute.

The geometry is the board's, in its 200 unit square, scaled to the tile.
"""

import machine
import math
import time

import draw
import look
import pages

DIGITS_FONT, DIGITS_FILE = "railclock", "railclock_digits.af"
# Where `statsbadge install` puts this extension, should __file__ not say.
EXT_HOME = "/system/apps/stats/ext/railclock/"

# The board's stylesheet: the tile in a card's border, the red, the time.
TILE = (11, 15, 20)
EDGE = (24, 34, 48)
RED = (208, 32, 47)
TIME = (236, 236, 236)

# renderRailClock(), in a 200 unit square.
OUTER = 82.0
INNER = 74.5
STROKE = 3.0
GAP = OUTER - INNER
MID = (OUTER + INNER) / 2.0
# The arms leave the ring at 27 degrees, as in Gerry Barney's logo.
ARM = math.radians(27.0)
BACK = GAP / math.tan(ARM)
HALF = STROKE / 2.0 / math.sin(ARM)
SPAN = math.degrees(BACK / MID)
# The time: 34 units, Inter Bold, whose capitals stand 1490 of 2048. The packed font's
# stand 81/128 of the size it is drawn at.
TIME_UNITS = 34.0
CAP_RATIO = (1490.0 / 2048.0) / (81.0 / 128.0)

# The tile is the page band, with a little of the page showing round it as between the
# board's cards, and the face is 88% of it.
INSET = 4
RADIUS = 8
FACE = 0.88

# A PCF85063A drifts a second or two a day.
RESYNC_S = 30
# A gap between draws longer than this is the page coming back on screen, so the frame
# it is handed may be a host's last, from whenever it went quiet.
AWAY_MS = 2000

_pens = None
_built = None
_tried_font = False

_synced = False
_seen_seq = None
_drawn_at = None
_phase_second = None
_phase_at = 0


def _beside(name):
    """Return a file shipped alongside this module, where the installer put both."""
    here = globals().get("__file__") or ""
    return here.rsplit("/", 1)[0] + "/" + name if "/" in here else EXT_HOME + name


def _font():
    global _tried_font
    if not _tried_font:
        _tried_font = True
        draw.add_font(DIGITS_FONT, _beside(DIGITS_FILE), EXT_HOME + DIGITS_FILE)
    return DIGITS_FONT if draw.has_font(DIGITS_FONT) else draw.TEXT


def _colours():
    """Return the pens, made once: a label is cached against its pen."""
    global _pens
    if _pens is None:
        _pens = {"tile": color.rgb(*TILE), "edge": color.rgb(*EDGE),
                 "red": color.rgb(*RED), "time": color.rgb(*TIME)}
    return _pens


def _point(radius, degrees):
    """Return a point `radius` from the centre, `degrees` clockwise from twelve."""
    angle = math.radians(degrees)
    return vec2(radius * math.sin(angle), -radius * math.cos(angle))


def _chevron(scale, ring, tip, direction):
    """Return one chevron about the origin: railClockChevron(), bent onto the rings.

    Built along the direction of travel and across the rings, so the arm crossing the gap
    ends on the other ring's centreline and the opposite arm mirrors it outward.
    """
    local = ((HALF, 0.0), (HALF - BACK, GAP), (-HALF - BACK, GAP), (-HALF, 0.0),
             (-HALF - BACK, -GAP), (HALF - BACK, -GAP))
    return shape.custom([_point((ring + across) * scale,
                                tip + direction * math.degrees(along / MID))
                         for along, across in local])


def _geometry():
    """Return the tile, the face's centre and scale, and the two chevrons, built once."""
    global _built
    if _built is None:
        top = look.BODY_TOP + INSET // 2
        tile = (INSET, top, look.W - INSET * 2, look.BODY_H - INSET)
        centre = (tile[0] + tile[2] / 2.0, tile[1] + tile[3] / 2.0)
        scale = min(tile[2], tile[3]) * FACE / 200.0
        # Offset by half the chevron's span, so the two crossing arms coincide as the
        # logo whenever the chevrons meet.
        outer = _chevron(scale, OUTER, SPAN / 2.0, 1)
        inner = _chevron(scale, INNER, -SPAN / 2.0, -1)
        _built = (tile, centre, scale, outer, inner)
    return _built


def _seconds():
    """Return the second of the minute off the badge's clock, with its fraction."""
    global _phase_second, _phase_at
    whole = time.localtime()[5]
    now = time.ticks_ms()
    if whole != _phase_second:
        _phase_second = whole
        _phase_at = now
    return whole + min(1.0, time.ticks_diff(now, _phase_at) / 1000.0)


def _take(frame):
    """Set the badge's clock from the host's, when this frame is a fresh reading.

    Fresh is a frame seen to arrive while the page is up: the last frame of a host that
    has gone away carries the time it went. A page coming on screen with nothing set yet
    takes what it is handed, as the time it has is no better.
    """
    global _seen_seq, _drawn_at
    now = time.ticks_ms()
    back = _drawn_at is None or time.ticks_diff(now, _drawn_at) > AWAY_MS
    _drawn_at = now
    seq = frame.get("seq")
    if back:
        _seen_seq = seq
        if not _synced:
            _resync(frame.get("railclock") or {})
        return
    if seq != _seen_seq:
        _seen_seq = seq
        _resync(frame.get("railclock") or {})


def _resync(clock):
    """Set the badge's clock from a reading: the first, then only past RESYNC_S."""
    global _synced
    hour, minute, second = clock.get("hour"), clock.get("minute"), clock.get("seconds")
    if hour is None or minute is None or second is None:
        return
    parts = time.localtime()
    drift = (hour * 3600 + minute * 60 + second
             - (parts[3] * 3600 + parts[4] * 60 + parts[5]) + 43200) % 86400 - 43200
    if _synced and -RESYNC_S <= drift <= RESYNC_S:
        return
    machine.RTC().datetime((parts[0], parts[1], parts[2], parts[6],
                            hour, minute, second, 0))
    _synced = True


def render(_page, frame, _history, _theme):
    pens = _colours()
    font = _font()
    tile, centre, scale, outer, inner = _geometry()
    _take(frame)

    # The tile: the board's card, on the page.
    screen.pen = pens["edge"]
    screen.shape(shape.rounded_rectangle(rect(*tile), RADIUS))
    screen.pen = pens["tile"]
    screen.shape(shape.rounded_rectangle(
        rect(tile[0] + 1, tile[1] + 1, tile[2] - 2, tile[3] - 2), RADIUS - 1))

    # The rings, always there.
    screen.pen = pens["red"]
    half = STROKE * scale / 2.0
    for ring in (OUTER, INNER):
        screen.shape(shape.arc(vec2(*centre), ring * scale - half, ring * scale + half,
                               0, 360))

    # The chevrons, a turn a minute each way, off the badge's own clock.
    turned = _seconds() * 6.0
    outer.transform = mat3().translate(*centre).rotate(turned)
    inner.transform = mat3().translate(*centre).rotate(-turned)
    screen.shape(outer)
    screen.shape(inner)

    # The time, its capitals centred on the face, as the board's central baseline puts
    # them. The board shows --:-- until its clock has the time.
    if _synced:
        hour, minute = time.localtime()[3:5]
        shown = f"{hour:02d}:{minute:02d}"
    else:
        shown = "--:--"
    size = int(TIME_UNITS * scale * CAP_RATIO + 0.5)
    ink = size * draw.CAP
    y = int(centre[1] - ink / 2.0 - (size - ink) + 0.5)
    draw.blit_label(shown, size, pens["time"], int(centre[0]), y, align=1, name=font)


pages.register("railclock", render, api=1, animated=True)
