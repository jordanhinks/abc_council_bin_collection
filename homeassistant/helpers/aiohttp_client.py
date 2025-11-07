def async_get_clientsession(hass):
    # Caller will monkeypatch this in tests when necessary
    raise RuntimeError("async_get_clientsession must be monkeypatched in tests")
