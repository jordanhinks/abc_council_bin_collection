"""
Constants for the ABC Council Bin Collection integration.

Defines all constants for integration.
"""

# Domain and Metadata
DOMAIN: str = "abc_council_bin_collection"

# Device metadata for consistency across entities
DEVICE_NAME: str = "ABC Council Bin Collection"
DEVICE_MANUFACTURER: str = "ABC Council"
DEVICE_MODEL: str = "Bin Collection Sensor"
DEVICE_VERSION: str = "1.0"
DEVICE_INTEGRATION: str = "Home Assistant"

# Update Interval Constants (in hours)

# Number of hours between automatic data updates.
DEFAULT_UPDATE_INTERVAL: int = 120  # hours

# Minimum allowed number of hours for an update interval to prevent excessive updates
MIN_UPDATE_INTERVAL: int = 6  # hours

# Event Creation Constants

# Delay (in seconds) before an event is created.
EVENT_CREATION_DELAY: int = 20  # seconds

# Delay (in seconds) between each calendar event creation
EVENT_CREATION_TIMEOUT = 1 # seconds

# Sensor and Event Storage Constants

# A list of default sensor names used for bin collection events - do not change as change needs made to sensor.py
DEFAULT_SENSOR_NAMES: list[str] = [
    "Domestic Collections",
    "Recycling Collections",
    "Garden/Food Collections"
]

# Number of days after which stored events are considered outdated and subject to cleanup.
EVENT_CLEANUP_THRESHOLD_DAYS: int = 14  # days