"""The Rail Clock as a statsbadge page.

The time inside two red rings, whose chevrons go round a turn a minute in opposite
directions and meet as the double arrow on the minute and the half minute. The page is
drawn on the badge, which keeps time off the host's clock; all this side sends is that.
"""

import os
import time

from statsbadge.sources.base import Source

HERE = os.path.dirname(os.path.abspath(__file__))


class RailClock(Source):
    name = "railclock"
    label = "Rail Clock"
    provides = ("railclock",)

    # The badge-side code, pushed by `statsbadge install` and imported by the app.
    badge_module = os.path.join(HERE, "badge", "railclock.py")

    # Inter at weight 700 and optical size 32: its tabular digits, the colon it raises
    # between digits, and a dash for the placeholder, packed --wide.
    badge_assets = (os.path.join(HERE, "badge", "railclock_digits.af"),)

    badge_page = {
        "kind": "railclock",
        "title": "Rail Clock",
        "fields": [],
        "slots": {},
    }

    @classmethod
    def available(cls, _config=None):
        return True

    def sample(self, frame, dt):
        """Send the host's local time, which the badge sets its own clock from."""
        now = time.localtime()
        frame["railclock"] = {"hour": now.tm_hour, "minute": now.tm_min,
                              "seconds": now.tm_sec}
