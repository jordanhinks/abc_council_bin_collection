class DataUpdateCoordinator:
    def __init__(self, hass, logger, name: str, update_interval=None):
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.data = None

    async def async_config_entry_first_refresh(self):
        # call refresh once
        self.data = await self._async_update_data()

    async def _async_update_data(self):
        raise NotImplementedError

    async def async_stop(self):
        return None
