import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from types import SimpleNamespace
from datetime import timedelta
import asyncio

from homeassistant.exceptions import HomeAssistantError

from custom_components.abc_council_bin_collection.coordinator import BinCollectionDataUpdateCoordinator

@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.data = {}
    return hass

@pytest.mark.asyncio
async def test_coordinator_init_kwargs(mock_hass):
    """Test coordinator passes config_entry to super kwargs if provided."""
    entry = MagicMock()
    
    # Needs a mock storage to prevent HA core exceptions during init
    with patch("custom_components.abc_council_bin_collection.coordinator.BinCollectionStorage", return_value=MagicMock()):
        coord = BinCollectionDataUpdateCoordinator(
            hass=mock_hass,
            address="123",
            update_interval=timedelta(hours=1),
            create_calendar_events=False,
            calendar_entity="calendar.test",
            event_summaries={},
            config_entry=entry
        )
        assert coord.config_entry == entry

@pytest.mark.asyncio
async def test_coordinator_parse_unknown_bin_class(mock_hass):
    """Test parser handles and logs unknown bin HTML classes."""
    with patch("custom_components.abc_council_bin_collection.coordinator.BinCollectionStorage", return_value=MagicMock()):
        coord = BinCollectionDataUpdateCoordinator(
            hass=mock_hass, address="123", update_interval=timedelta(hours=1),
            create_calendar_events=False, calendar_entity="", event_summaries={},
            config_entry=MagicMock()
        )
        
        # We can't use real HTML because the regex strictly filters (bg-black|bg-green|bg-brown).
        # We can't patch finditer directly because it's a read-only C extension attribute.
        # Instead, we replace the entire regex object on the instance.
        mock_regex = MagicMock()
        mock_match = MagicMock()
        mock_match.group.side_effect = lambda idx: "bg-unknown" if idx == 1 else "fake_block"
        mock_regex.finditer.return_value = [mock_match]
        
        coord.BIN_COLLECTION_BLOCK_PATTERN = mock_regex
        
        result = coord._parse_html('dummy_html')
        
        # Should populate default bins with "No collection scheduled" and ignore the unknown one
        assert "Domestic Collections" in result
        assert result["Domestic Collections"] == ["No collection scheduled"]

@pytest.mark.asyncio
async def test_coordinator_missing_calendar_entity(mock_hass):
    """Test missing calendar entity error line."""
    with patch("custom_components.abc_council_bin_collection.coordinator.BinCollectionStorage", return_value=MagicMock()):
        coord = BinCollectionDataUpdateCoordinator(
            hass=mock_hass, address="123", update_interval=timedelta(hours=1),
            create_calendar_events=True, calendar_entity="", event_summaries={},
            config_entry=MagicMock()
        )
        coord.load_stored_events = AsyncMock()
        mock_hass.async_add_executor_job = AsyncMock(return_value={})
        
        with patch("custom_components.abc_council_bin_collection.coordinator.async_get_clientsession") as mock_session:
            mock_response = AsyncMock()
            mock_response.text = AsyncMock(return_value="<html></html>")
            mock_response.raise_for_status = MagicMock() # Sync mock
            mock_session.return_value.get = AsyncMock(return_value=mock_response)
            
            await coord._async_update_data()
            assert getattr(coord, "_events_task", None) is None

@pytest.mark.asyncio
async def test_coordinator_skip_non_date(mock_hass):
    """Test _create_calendar_events skipping No collection scheduled placeholder."""
    with patch("custom_components.abc_council_bin_collection.coordinator.BinCollectionStorage") as mock_storage:
        coord = BinCollectionDataUpdateCoordinator(
            hass=mock_hass, address="123", update_interval=timedelta(hours=1),
            create_calendar_events=True, calendar_entity="calendar.test", event_summaries={},
            config_entry=MagicMock()
        )
        
        data = {"Domestic Collections": ["No collection scheduled"]}
        mock_hass.services.async_call = AsyncMock()
        
        await coord._create_calendar_events(data)
        # Should cleanly skip and never call async_call
        mock_hass.services.async_call.assert_not_called()

@pytest.mark.asyncio
async def test_coordinator_parent_async_stop(mock_hass):
    """Test base class async_stop executes."""
    with patch("custom_components.abc_council_bin_collection.coordinator.BinCollectionStorage", return_value=MagicMock()):
        coord = BinCollectionDataUpdateCoordinator(
            hass=mock_hass, address="123", update_interval=timedelta(hours=1),
            create_calendar_events=False, calendar_entity="", event_summaries={},
            config_entry=MagicMock()
        )
        
        # In Home Assistant, DataUpdateCoordinator doesn't strictly have async_stop, 
        # but our code uses getattr(super(), "async_stop", None) just in case. 
        # So we can patch it temporarily by adding it to the class before testing.
        from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
        
        # Add mock async_stop to the class just for this test
        mock_coro = AsyncMock()
        mock_parent_stop = MagicMock(return_value=mock_coro())
        setattr(DataUpdateCoordinator, "async_stop", mock_parent_stop)
        
        try:
            await coord.async_stop()
            mock_parent_stop.assert_called_once()
        finally:
            # Clean up the class
            delattr(DataUpdateCoordinator, "async_stop")

@pytest.mark.asyncio
async def test_coordinator_date_year_wrapping(mock_hass):
    """Test that missing years wrap correctly (e.g. December catching next January)."""
    with patch("custom_components.abc_council_bin_collection.coordinator.BinCollectionStorage", return_value=MagicMock()):
        coord = BinCollectionDataUpdateCoordinator(
            hass=mock_hass, address="123", update_interval=timedelta(hours=1),
            create_calendar_events=False, calendar_entity="", event_summaries={},
            config_entry=MagicMock()
        )
        
        # We simulate the current date being Dec 31, and we parse "1 Jan"
        # The block pattern needs class="heading bg-black" and then the date pattern needs <h4><i class="fa fa-calendar"></i> ... </h4>
        html = '<div class="heading bg-black">Fake</div><hr></div><div class="col-sm-12 col-md-9"><h4><i class="fa fa-calendar"></i>1 Jan</h4></div><div class="col-sm-12 col-md-3">'
        
        with patch("custom_components.abc_council_bin_collection.coordinator.datetime") as mock_datetime:
            from datetime import datetime
            # Mock now() to be Dec 31st 2025
            mock_datetime.now.return_value = datetime(2025, 12, 31)
            
            result = coord._parse_html(html)
            # The fuzzy parser should have pushed the year to 2026
            assert "2026-01-01" in result["Domestic Collections"]
            
        # Reverse case: we parse Dec 31st when current date is Jan 1
        with patch("custom_components.abc_council_bin_collection.coordinator.datetime") as mock_datetime:
            from datetime import datetime
            mock_datetime.now.return_value = datetime(2026, 1, 1)
            html = '<div class="heading bg-black">Fake</div><hr></div><div class="col-sm-12 col-md-9"><h4><i class="fa fa-calendar"></i>31 Dec</h4></div><div class="col-sm-12 col-md-3">'
            
            result = coord._parse_html(html)
            assert "2025-12-31" in result["Domestic Collections"]

@pytest.mark.asyncio
async def test_coordinator_invalid_date_skip(mock_hass):
    """Test that fully unparseable strings are skipped gracefully and empty date lists append default."""
    with patch("custom_components.abc_council_bin_collection.coordinator.BinCollectionStorage", return_value=MagicMock()):
        coord = BinCollectionDataUpdateCoordinator(
            hass=mock_hass, address="123", update_interval=timedelta(hours=1),
            create_calendar_events=False, calendar_entity="", event_summaries={},
            config_entry=MagicMock()
        )
        
        # Valid block but no valid date pattern match inside it
        html = '<div class="heading bg-black">Fake</div><hr></div><div class="col-sm-12 col-md-9"><h4>NO CALENDAR ICON HERE</h4></div><div class="col-sm-12 col-md-3">'
        
        result = coord._parse_html(html)
        assert result["Domestic Collections"] == ["No collection scheduled"]

@pytest.mark.asyncio
async def test_coordinator_date_parse_exception_caught(mock_hass):
    """Test that a matched date that throws ValueError is caught and skipped."""
    with patch("custom_components.abc_council_bin_collection.coordinator.BinCollectionStorage", return_value=MagicMock()):
        coord = BinCollectionDataUpdateCoordinator(
            hass=mock_hass, address="123", update_interval=timedelta(hours=1),
            create_calendar_events=False, calendar_entity="", event_summaries={},
            config_entry=MagicMock()
        )
        
        html = '<div class="heading bg-black">Fake</div><hr></div><div class="col-sm-12 col-md-9"><h4><i class="fa fa-calendar"></i>Bad Date</h4></div><div class="col-sm-12 col-md-3">'
        
        with patch("custom_components.abc_council_bin_collection.coordinator.parse", side_effect=ValueError):
            result = coord._parse_html(html)
            assert result["Domestic Collections"] == ["No collection scheduled"]
            
        from dateutil.parser import ParserError
        with patch("custom_components.abc_council_bin_collection.coordinator.parse", side_effect=ParserError("Bad date")):
            result = coord._parse_html(html)
            assert result["Domestic Collections"] == ["No collection scheduled"]

@pytest.mark.asyncio
async def test_coordinator_async_create_task_fallback(mock_hass):
    """Test fallback when hass.async_create_task is missing or errors."""
    with patch("custom_components.abc_council_bin_collection.coordinator.BinCollectionStorage", return_value=MagicMock()):
        coord = BinCollectionDataUpdateCoordinator(
            hass=mock_hass, address="123", update_interval=timedelta(hours=1),
            create_calendar_events=True, calendar_entity="calendar.test", event_summaries={},
            config_entry=MagicMock()
        )
        
        # Make async_create_task throw an AttributeError to trigger the asyncio.create_task fallback
        mock_hass.async_create_task.side_effect = AttributeError("Mocking missing task")
        mock_hass.async_add_executor_job = AsyncMock(return_value={})
        
        # Test the update cycle
        coord.load_stored_events = AsyncMock()
        
        with patch("custom_components.abc_council_bin_collection.coordinator.async_get_clientsession") as mock_session:
            mock_response = AsyncMock()
            mock_response.text = AsyncMock(return_value="<html></html>")
            mock_response.raise_for_status = MagicMock()

            # coordinator calls: response = await session.get(self.url) (no async with on the get call itself, it's just an awaitable)
            mock_session.return_value.get = AsyncMock(return_value=mock_response)

            await coord._async_update_data()
            
            assert coord._events_task is not None
            # Cleanup to avoid warnings, _events_task is an asyncio task so cancel is sync
            coord._events_task.cancel()

@pytest.mark.asyncio
async def test_coordinator_async_stop(mock_hass):
    """Test async_stop handles task cancellation logic thoroughly."""
    with patch("custom_components.abc_council_bin_collection.coordinator.BinCollectionStorage", return_value=MagicMock()):
        coord = BinCollectionDataUpdateCoordinator(
            hass=mock_hass, address="123", update_interval=timedelta(hours=1),
            create_calendar_events=False, calendar_entity="", event_summaries={},
            config_entry=MagicMock()
        )
        
        # 1. No task
        await coord.async_stop()
        
        # 2. Task exists and cancels cleanly
        loop = asyncio.get_running_loop()
        mock_task = loop.create_future()
        mock_task.cancel = MagicMock() # Sync mock
        mock_task.set_result(None)
        coord._events_task = mock_task
        await coord.async_stop()
        assert getattr(coord, "_events_task", "exists") is None
        mock_task.cancel.assert_called_once()
        
        # 3. Task throws CancelledError while awaiting
        mock_task = loop.create_future()
        mock_task.cancel = MagicMock()
        mock_task.set_exception(asyncio.CancelledError())
        coord._events_task = mock_task
        await coord.async_stop()
        
        # 4. Task throws standard exception while awaiting
        mock_task = loop.create_future()
        mock_task.cancel = MagicMock()
        mock_task.set_exception(ValueError("Test exception"))
        coord._events_task = mock_task
        await coord.async_stop()

@pytest.mark.asyncio
async def test_coordinator_parse_error_exception(mock_hass):
    """Test parse html hitting the ValueError/ParserError exception."""
    with patch("custom_components.abc_council_bin_collection.coordinator.BinCollectionStorage", return_value=MagicMock()):
        coord = BinCollectionDataUpdateCoordinator(
            hass=mock_hass, address="123", update_interval=timedelta(hours=1),
            create_calendar_events=False, calendar_entity="", event_summaries={},
            config_entry=MagicMock()
        )
        
        html = '<div class="heading bg-black">Fake</div><hr></div><div class="col-sm-12 col-md-9"><h4><i class="fa fa-calendar"></i>BAD DATE STRING</h4></div><div class="col-sm-12 col-md-3">'
        
        with patch("custom_components.abc_council_bin_collection.coordinator.parse", side_effect=ValueError("Bad date")):
            result = coord._parse_html(html)
            assert result["Domestic Collections"] == ["No collection scheduled"]

@pytest.mark.asyncio
async def test_coordinator_store_event_oserror(mock_hass):
    """Test create_calendar_events catches exception during store_event."""
    with patch("custom_components.abc_council_bin_collection.coordinator.BinCollectionStorage") as mock_storage:
        coord = BinCollectionDataUpdateCoordinator(
            hass=mock_hass, address="123", update_interval=timedelta(hours=1),
            create_calendar_events=True, calendar_entity="calendar.test", event_summaries={},
            config_entry=MagicMock()
        )
        
        mock_store_inst = mock_storage.return_value
        mock_store_inst.is_event_stored.return_value = False
        mock_store_inst.store_event = AsyncMock(side_effect=OSError("Disk full"))
        coord.storage = mock_store_inst
        
        data = {"Domestic Collections": ["2026-01-01"]}
        mock_hass.services.async_call = AsyncMock()
        
        with patch("custom_components.abc_council_bin_collection.coordinator.asyncio.sleep", new_callable=AsyncMock):
            await coord._create_calendar_events(data)
            # The async_call passes but store_event fails. It should catch OSError and log it.
            mock_store_inst.store_event.assert_called_once()
    """Test _run_create_events_task asyncio.CancelledError."""
    with patch("custom_components.abc_council_bin_collection.coordinator.BinCollectionStorage", return_value=MagicMock()):
        coord = BinCollectionDataUpdateCoordinator(
            hass=mock_hass, address="123", update_interval=timedelta(hours=1),
            create_calendar_events=False, calendar_entity="", event_summaries={},
            config_entry=MagicMock()
        )
        
        # Mock asyncio.sleep to instantly throw CancelledError
        with patch("custom_components.abc_council_bin_collection.coordinator.asyncio.sleep", side_effect=asyncio.CancelledError):
            with pytest.raises(asyncio.CancelledError):
                await coord._run_create_events_task({})

@pytest.mark.asyncio
async def test_coordinator_create_events_generic_exception(mock_hass):
    """Test _run_create_events_task handles random standard exceptions."""
    with patch("custom_components.abc_council_bin_collection.coordinator.BinCollectionStorage", return_value=MagicMock()):
        coord = BinCollectionDataUpdateCoordinator(
            hass=mock_hass, address="123", update_interval=timedelta(hours=1),
            create_calendar_events=False, calendar_entity="", event_summaries={},
            config_entry=MagicMock()
        )
        
        # Mock create events logic to fail
        coord._create_calendar_events = AsyncMock(side_effect=ValueError("Test exception"))
        
        # Mock sleep so it doesn't wait
        with patch("custom_components.abc_council_bin_collection.coordinator.asyncio.sleep", new_callable=AsyncMock):
            await coord._run_create_events_task({})
            # Should have set _events_task to None in finally block
            assert getattr(coord, "_events_task", "exists") is None

@pytest.mark.asyncio
async def test_coordinator_is_event_stored_exception(mock_hass):
    """Test _create_calendar_events catches storage read errors."""
    with patch("custom_components.abc_council_bin_collection.coordinator.BinCollectionStorage") as mock_storage:
        coord = BinCollectionDataUpdateCoordinator(
            hass=mock_hass, address="123", update_interval=timedelta(hours=1),
            create_calendar_events=True, calendar_entity="calendar.test", event_summaries={},
            config_entry=MagicMock()
        )
        
        mock_store_inst = mock_storage.return_value
        mock_store_inst.is_event_stored.side_effect = KeyError("Storage missing")
        mock_store_inst.store_event = AsyncMock()
        coord.storage = mock_store_inst
        
        # Provide valid data to parse
        data = {"Domestic Collections": ["2026-01-01"]}
        
        with patch("custom_components.abc_council_bin_collection.coordinator.asyncio.sleep", new_callable=AsyncMock):
            mock_hass.services.async_call = AsyncMock()
            await coord._create_calendar_events(data)
            
            # The exception in is_event_stored means `already` defaults to False, so create_event is called
            mock_hass.services.async_call.assert_called_once()

@pytest.mark.asyncio
async def test_coordinator_is_event_stored_true_continue(mock_hass):
    """Test _create_calendar_events safely skips if already exists."""
    with patch("custom_components.abc_council_bin_collection.coordinator.BinCollectionStorage") as mock_storage:
        coord = BinCollectionDataUpdateCoordinator(
            hass=mock_hass, address="123", update_interval=timedelta(hours=1),
            create_calendar_events=True, calendar_entity="calendar.test", event_summaries={},
            config_entry=MagicMock()
        )
        
        mock_store_inst = mock_storage.return_value
        mock_store_inst.is_event_stored.return_value = True
        mock_store_inst.store_event = AsyncMock()
        coord.storage = mock_store_inst
        
        data = {"Domestic Collections": ["2026-01-01"]}
        mock_hass.services.async_call = AsyncMock()
        
        await coord._create_calendar_events(data)
        
        # Because is_event_stored is True, async_call should NEVER be called
        mock_hass.services.async_call.assert_not_called()

@pytest.mark.asyncio
async def test_coordinator_create_event_service_failure(mock_hass):
    """Test _create_calendar_events handles HA service failures."""
    with patch("custom_components.abc_council_bin_collection.coordinator.BinCollectionStorage") as mock_storage:
        coord = BinCollectionDataUpdateCoordinator(
            hass=mock_hass, address="123", update_interval=timedelta(hours=1),
            create_calendar_events=True, calendar_entity="calendar.test", event_summaries={},
            config_entry=MagicMock()
        )
        
        mock_store_inst = mock_storage.return_value
        mock_store_inst.is_event_stored.return_value = False
        mock_store_inst.store_event = AsyncMock()
        coord.storage = mock_store_inst
        
        data = {"Domestic Collections": ["2026-01-01"]}
        mock_hass.services.async_call = AsyncMock(side_effect=HomeAssistantError("Service failed"))
        
        with patch("custom_components.abc_council_bin_collection.coordinator.asyncio.sleep", new_callable=AsyncMock):
            await coord._create_calendar_events(data)
            # The exception is caught and logged, not raised.
            mock_hass.services.async_call.assert_called_once()

@pytest.mark.asyncio
async def test_coordinator_async_stop(mock_hass):
    """Test async_stop handles task cancellation logic thoroughly."""
    with patch("custom_components.abc_council_bin_collection.coordinator.BinCollectionStorage", return_value=MagicMock()):
        coord = BinCollectionDataUpdateCoordinator(
            hass=mock_hass, address="123", update_interval=timedelta(hours=1),
            create_calendar_events=False, calendar_entity="", event_summaries={},
            config_entry=MagicMock()
        )
        
        # 1. No task
        await coord.async_stop()
        
        # 2. Task exists and cancels cleanly
        loop = asyncio.get_running_loop()
        mock_task = loop.create_future()
        mock_task.cancel = MagicMock()
        mock_task.set_result(None)
        coord._events_task = mock_task
        await coord.async_stop()
        assert getattr(coord, "_events_task", "exists") is None
        mock_task.cancel.assert_called_once()
        
        # 3. Task throws CancelledError while awaiting
        mock_task = loop.create_future()
        mock_task.cancel = MagicMock()
        mock_task.set_exception(asyncio.CancelledError())
        coord._events_task = mock_task
        await coord.async_stop()
        
        # 4. Task throws standard exception while awaiting
        mock_task = loop.create_future()
        mock_task.cancel = MagicMock()
        mock_task.set_exception(ValueError("Test exception"))
        coord._events_task = mock_task
        await coord.async_stop()