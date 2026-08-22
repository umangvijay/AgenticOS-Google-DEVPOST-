from datetime import datetime
import pytz

def get_current_time(timezone: str = "UTC") -> str:
    """Returns the current time for a given timezone."""
    try:
        tz = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError:
        tz = pytz.UTC
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %Z")
