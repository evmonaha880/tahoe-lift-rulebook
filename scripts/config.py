"""The one place that says which winters the project covers. A winter is named by its start year (2015 = 2015-16), Oct 1 to May 31.
To add a winter, change LAST_YEAR here; scripts that pull or build for 'all winters' read this."""
FIRST_YEAR, LAST_YEAR = 2015, 2025
YEARS = list(range(FIRST_YEAR, LAST_YEAR + 1))
WINTERS = [f"{y}-{str(y + 1)[2:]}" for y in YEARS]

from zoneinfo import ZoneInfo
LA = ZoneInfo("America/Los_Angeles")   # the project clock: posts are stamped in Los Angeles time, daylight saving included
CORE_FIRST_YEAR = 2018                                   # the 8 core winters (2018-19 to 2025-26) are the headline; 2015-18 are scored separately as the 11-winter view
CORE_WINTERS = [w for w in WINTERS if int(w[:4]) >= CORE_FIRST_YEAR]
