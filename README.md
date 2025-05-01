# Bin Collection for Northern Ireland ABC Council Area

Home Assistant component to pull data from Northern Ireland ABC Council website regarding bin collection dates based on address provided.

## Installation:

1. Install this component by copying [these files]([https://github.com/custom-components/sensor.sonarr_upcoming_media/tree/master/custom_components/sonarr_upcoming_media](https://github.com/jordanhinks/bin_collection/tree/main/custom_components/bin_collection)) to `/custom_components/bin_collection/`.
2. Restart your Home Assistant instance
3. Open a new browser tab and navigate to [ABC Council website](https://www.armaghbanbridgecraigavon.gov.uk/resident/when-is-my-bin-day/)
4. Enter your post code, click submit then house number, click submit
5. Copy either the entire website address, or just the value after **?address=**
6. Navigate to Settings > Devices & Services
7. Click Add Integration, search **Bin Collection** then add
8. Paste the website address/value from step 5, then click submit

### Configure options

When the integration is added, the **Configure** button offer additional options/features.

- Update Interval (default: 96) - change the frequency it fetches data in hours.
- Create Calendar Events (default: unticked) - this depends on calendar such as Google Calendar to be installed and have read/write permissions. It allows you to choose for calendar events to be created automatically.
- Calendar Entity - Lets you specify the name of the calendar entity either as "calendar.my_calendar", or "my_calendar", you will find the calendar name in your Home Assistant instance.
- Domestic Collections Summary, Recycling Collections Summary, and Garden & Food Collections Summary - allows you to choose the preferred calendar event name for each such as if you prefer the bin color.

## Note

If **Create Calendar Events** is ticked and then either the integration or Home Assistant instance is restarted, it will create the calendar events again until a suitable persistant solution is put in place.
