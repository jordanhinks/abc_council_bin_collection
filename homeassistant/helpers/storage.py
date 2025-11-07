class Store:
    def __init__(self, hass, version, key):
        self._data = None

    async def async_load(self):
        return self._data

    async def async_save(self, data):
        self._data = data

# Provide a placeholder constant if code expects any
STORAGE_VERSION = 1
