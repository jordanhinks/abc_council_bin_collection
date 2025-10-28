from dataclasses import dataclass
from types import SimpleNamespace

@dataclass
class ConfigEntry:
    entry_id: str
    data: dict
    options: dict = None


class ConfigEntries:
    async def async_forward_entry_setups(self, entry, platforms):
        return None

    async def async_unload_platforms(self, entry, platforms):
        return True

# Provide an alias used in some test stubs
ConfigEntryType = ConfigEntry
