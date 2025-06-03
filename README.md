# Bin Collection for Northern Ireland ABC Council Area

Home Assistant component to pull data from Northern Ireland ABC Council website regarding bin collection dates based on address provided.

## Easy Installation:

1. Navigate to your HACs instance
2. Search ABC Council Bin Collection then download latest version
3. Restart your Home Assistant instance

<details>
<summary style="list-style: none"><h2><b style="cursor: pointer">Manual installation:</b></h2></summary>

  1. Install this component by copying [these files]([https://github.com/custom-components/sensor.sonarr_upcoming_media/tree/master/custom_components/sonarr_upcoming_media](https://github.com/jordanhinks/abc_council_bin_collection/tree/main/custom_components/abc_council_bin_collection)) to `/custom_components/abc_council_bin_collection/`.
  2. Restart your Home Assistant instance
</details>
</details>

## Setup Instructions:

<a href="https://my.home-assistant.io/redirect/config_flow_start?domain=abc_council_bin_collection" class="my badge" target="_blank"><img src="https://my.home-assistant.io/badges/config_flow_start.svg"></a>

1. Click above button **OR** navigate to Settings > Devices & Services, click Add Integration then search ABC Council Bin Collection
1. Open a new browser tab and navigate to [ABC Council website](https://www.armaghbanbridgecraigavon.gov.uk/resident/when-is-my-bin-day/)
2. Enter your post code, click submit then house number, click submit
3. Copy either the entire website address, or just the value after **?address=**
4. Navigate to Settings > Devices & Services
5. Click Add Integration, search **ABC Council Bin Collection** then add
6. Paste the website address/value from step 5, then click submit

### Configure options

When the integration is added, the **Configure** button offer additional options/features.

- Update Interval (default: 96, minimum: 6) - change the frequency it fetches data in hours.
- Create Calendar Events (default: unticked) - this depends on calendar such as Google Calendar to be installed and have read/write permissions. It allows you to choose for calendar events to be created automatically.
- Calendar Entity - Lets you specify the name of the calendar entity either as "calendar.my_calendar", or "my_calendar", you will find the calendar name in your Home Assistant instance.
- Domestic Collections Summary, Recycling Collections Summary, and Garden & Food Collections Summary - allows you to choose the preferred calendar event name for each such as if you prefer the bin color.

### Entities

For further control if you wish to use the dates; an entity has been created for each collection type with the state being the next collection date, then the subsequent dates being placed within the state attributes under **all_dates**.

A button entity has also been created which allows you to clear persistent storage for all calendar events created.

## Note

- If calendar events aren't automatically created after ticking option to create calendar events, just reload the integration.
