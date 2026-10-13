import sys
# fake HA if needed, but dt is just functions usually
try:
    from homeassistant.util.dt import parse_date, parse_datetime
    print(parse_date("13 October 2026"))
except Exception as e:
    print(f"Error: {e}")
