
import pytest
import aiohttp
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from types import SimpleNamespace

from homeassistant.helpers.update_coordinator import UpdateFailed
from custom_components.abc_council_bin_collection.coordinator import BinCollectionDataUpdateCoordinator
from custom_components.abc_council_bin_collection.const import DOMAIN

class DummySession:
    async def get(self, url):
        class DummyResponse:
            def raise_for_status(self): pass
            async def text(self): return "<html></html>"
        return DummyResponse()

@pytest.fixture
def mock_hass():
    hass = SimpleNamespace()
    async def fake_executor(func, arg):
        return func(arg)
    hass.async_add_executor_job = fake_executor
    return hass

@pytest.fixture
def mock_coord(mock_hass):
    coord = BinCollectionDataUpdateCoordinator.__new__(BinCollectionDataUpdateCoordinator)
    coord.hass = mock_hass
    coord.address = "123"
    coord.url = "http://test"
    coord.create_calendar_events = False
    coord.calendar_entity = ""
    coord.event_summaries = {}
    coord._base_update_interval = timedelta(hours=120)
    coord.update_interval = timedelta(hours=120)
    
    class FakeStorage:
        async def load_data(self): return {}
    coord.storage = FakeStorage()
    return coord

@pytest.mark.asyncio
async def test_parse_failures_trigger_issue(monkeypatch, mock_coord):
    # Mock issue registry methods
    mock_create_issue = MagicMock()
    mock_delete_issue = MagicMock()
    monkeypatch.setattr("custom_components.abc_council_bin_collection.coordinator.async_create_issue", mock_create_issue)
    monkeypatch.setattr("custom_components.abc_council_bin_collection.coordinator.async_delete_issue", mock_delete_issue)
    
    # Return HTML that has no dates
    monkeypatch.setattr("custom_components.abc_council_bin_collection.coordinator.async_get_clientsession", lambda h: DummySession())
    
    # First failure
    await mock_coord._async_update_data()
    assert mock_coord._consecutive_parse_failures == 1
    mock_create_issue.assert_not_called()
    
    # Second failure
    await mock_coord._async_update_data()
    assert mock_coord._consecutive_parse_failures == 2
    mock_create_issue.assert_not_called()
    
    # Third failure
    await mock_coord._async_update_data()
    assert mock_coord._consecutive_parse_failures == 3
    mock_create_issue.assert_called_once()
    assert mock_create_issue.call_args[0][1] == DOMAIN
    
    # Now simulate a success that clears it
    class SuccessSession:
        async def get(self, url):
            class SuccessResponse:
                def raise_for_status(self): pass
                async def text(self):
                    # valid HTML block
                    return '''
                    <div class="heading bg-black">Title</div><hr></div>
                    <div class="col-sm-12 col-md-9">
                        <h4><i class="fa fa-calendar"></i>15/01/2026</h4>
                    </div><div class="col-sm-12 col-md-3">
                    '''
            return SuccessResponse()
    monkeypatch.setattr("custom_components.abc_council_bin_collection.coordinator.async_get_clientsession", lambda h: SuccessSession())
    
    await mock_coord._async_update_data()
    assert mock_coord._consecutive_parse_failures == 0
    mock_delete_issue.assert_called_once()

@pytest.mark.asyncio
async def test_smart_interval_adjusts(monkeypatch, mock_coord):
    # Make sure we hit the ValueError in the date parsing as well by providing an invalid date string
    class SuccessSession:
        async def get(self, url):
            class SuccessResponse:
                def raise_for_status(self): pass
                async def text(self):
                    # Provide a valid future date and an invalid one to trigger ValueError
                    today = datetime.now()
                    future = today + timedelta(days=2)
                    future_str = future.strftime("%d/%m/%Y")
                    return f'''
                    <div class="heading bg-black">Title</div><hr></div>
                    <div class="col-sm-12 col-md-9">
                        <h4><i class="fa fa-calendar"></i>{future_str}</h4>
                    </div><div class="col-sm-12 col-md-3">
                    '''
            return SuccessResponse()
    monkeypatch.setattr("custom_components.abc_council_bin_collection.coordinator.async_get_clientsession", lambda h: SuccessSession())
    
    # Add a mock property just to bypass the error deletion if any
    monkeypatch.setattr("custom_components.abc_council_bin_collection.coordinator.async_delete_issue", MagicMock())
    
    mock_coord.update_interval = timedelta(hours=120)
    mock_coord._base_update_interval = timedelta(hours=120)
    
    await mock_coord._async_update_data()
    
    # Smart interval should be next_collection + 1 day. 
    # Next collection is today + 2 days. + 1 day = 3 days. 
    # 3 days is less than 5 days (120 hours), so it should update!
    assert mock_coord.update_interval == timedelta(days=3)

@pytest.mark.asyncio
async def test_smart_interval_value_error(monkeypatch, mock_coord):
    # Provide a valid HTML but with a date string that parse() fails on when we convert back from ISO
    # Actually wait, _parse_html returns ISO format YYYY-MM-DD.
    # The smart interval parses back using datetime.strptime(date_str, "%Y-%m-%d").
    # Let's mock _parse_html directly to return an invalid ISO date
    mock_coord._parse_html = lambda html: {"Domestic Collections": ["invalid-date-format"]}
    
    monkeypatch.setattr("custom_components.abc_council_bin_collection.coordinator.async_get_clientsession", lambda h: DummySession())
    
    await mock_coord._async_update_data()
    # It should catch ValueError and ignore the date, not changing the interval
    assert mock_coord.update_interval == timedelta(hours=120)

@pytest.mark.asyncio
async def test_smart_interval_extreme_short_base(monkeypatch, mock_coord):
    """Test smart interval when user has configured a very short base interval (e.g. 6 hours)."""
    class SuccessSession:
        async def get(self, url):
            class SuccessResponse:
                def raise_for_status(self): pass
                async def text(self):
                    today = datetime.now()
                    future = today + timedelta(days=2)
                    future_str = future.strftime("%d/%m/%Y")
                    return f'''
                    <div class="heading bg-black">Title</div><hr></div>
                    <div class="col-sm-12 col-md-9">
                        <h4><i class="fa fa-calendar"></i>{future_str}</h4>
                    </div><div class="col-sm-12 col-md-3">
                    '''
            return SuccessResponse()
    monkeypatch.setattr("custom_components.abc_council_bin_collection.coordinator.async_get_clientsession", lambda h: SuccessSession())
    monkeypatch.setattr("custom_components.abc_council_bin_collection.coordinator.async_delete_issue", MagicMock())
    
    # User configured 6 hours. Next collection is 2 days away. 
    # Smart interval (day after) = 3 days. min(3 days, 6 hours) = 6 hours.
    mock_coord.update_interval = timedelta(hours=6)
    mock_coord._base_update_interval = timedelta(hours=6)
    
    await mock_coord._async_update_data()
    assert mock_coord.update_interval == timedelta(hours=6)

@pytest.mark.asyncio
async def test_smart_interval_collection_today(monkeypatch, mock_coord):
    """Test smart interval when a collection is scheduled for today."""
    class SuccessSession:
        async def get(self, url):
            class SuccessResponse:
                def raise_for_status(self): pass
                async def text(self):
                    today_str = datetime.now().strftime("%d/%m/%Y")
                    return f'''
                    <div class="heading bg-black">Title</div><hr></div>
                    <div class="col-sm-12 col-md-9">
                        <h4><i class="fa fa-calendar"></i>{today_str}</h4>
                    </div><div class="col-sm-12 col-md-3">
                    '''
            return SuccessResponse()
    monkeypatch.setattr("custom_components.abc_council_bin_collection.coordinator.async_get_clientsession", lambda h: SuccessSession())
    monkeypatch.setattr("custom_components.abc_council_bin_collection.coordinator.async_delete_issue", MagicMock())
    
    # Collection today. Poll day after = 1 day (24 hours).
    # Base interval is 120 hours. min(24h, 120h) = 24h.
    mock_coord.update_interval = timedelta(hours=120)
    mock_coord._base_update_interval = timedelta(hours=120)
    
    await mock_coord._async_update_data()
    assert mock_coord.update_interval == timedelta(hours=24)

@pytest.mark.asyncio
async def test_smart_interval_no_future_dates(monkeypatch, mock_coord):
    """Test smart interval reverts to base if only past dates exist."""
    class SuccessSession:
        async def get(self, url):
            class SuccessResponse:
                def raise_for_status(self): pass
                async def text(self):
                    past = datetime.now() - timedelta(days=2)
                    past_str = past.strftime("%d/%m/%Y")
                    return f'''
                    <div class="heading bg-black">Title</div><hr></div>
                    <div class="col-sm-12 col-md-9">
                        <h4><i class="fa fa-calendar"></i>{past_str}</h4>
                    </div><div class="col-sm-12 col-md-3">
                    '''
            return SuccessResponse()
    monkeypatch.setattr("custom_components.abc_council_bin_collection.coordinator.async_get_clientsession", lambda h: SuccessSession())
    monkeypatch.setattr("custom_components.abc_council_bin_collection.coordinator.async_delete_issue", MagicMock())
    
    # Set current interval to something weird (e.g. 24h) to see if it reverts to base 120h
    mock_coord.update_interval = timedelta(hours=24)
    mock_coord._base_update_interval = timedelta(hours=120)
    
    await mock_coord._async_update_data()
    assert mock_coord.update_interval == timedelta(hours=120)

