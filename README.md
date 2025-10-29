# Bin Collection for Northern Ireland ABC Council Area

Home Assistant component to pull data from Northern Ireland ABC Council website regarding bin collection dates based on address provided.

## Easy Installation:

1. Navigate to your HACs instance
2. Search ABC Council Bin Collection then download latest version
3. Restart Home Assistant

<details>
<summary style="list-style: none; cursor: pointer"><h2>Manual installation:</h2></summary>

1. Install this component by copying [these files](<[https://github.com/custom-components/sensor.sonarr_upcoming_media/tree/master/custom_components/sonarr_upcoming_media](https://github.com/jordanhinks/abc_council_bin_collection/tree/main/custom_components/abc_council_bin_collection)>) to `/custom_components/abc_council_bin_collection/`.
2. Restart Home Assistant
 </details>

## Setup Instructions:

<a href="https://my.home-assistant.io/redirect/config_flow_start?domain=abc_council_bin_collection" class="my badge" target="_blank"><img src="https://my.home-assistant.io/badges/config_flow_start.svg"></a>

1. Click above button **OR** navigate to Settings > Devices & Services
2. Click Add Integration, search ABC Council Bin Collection, then click the ABC Council Bin Collection
3. Navigate to [ABC Council website](https://www.armaghbanbridgecraigavon.gov.uk/resident/when-is-my-bin-day/) via the link in the setup
4. Enter your postcode, click Submit, then enter your house number, click Submit
5. Copy the complete URL, or copy the value after **?address=**
6. Paste the URL/value into the input field then click Submit

### Configure options

When the integration is added, the **Configure** button offers additional options/features.

-   Update Interval (default: 120, minimum: 6) - Change the frequency it fetches data in hours.
-   Create Calendar Events (default: unticked) - Creates calendar events automatically
    -   **Note:** Requires calendar such as Google Calendar to be installed and have read/write permission.
-   Calendar Entity - Specify the calendar entity to create the events under
    -   This accepts the entity of for example "calendar.my_calendar" or "my_calendar"
-   Domestic Collections Summary, Recycling Collections Summary, and Garden & Food Collections Summary - allows you to specify the preferred calendar event name for the calendar events for each such as if you prefer the bin color.

#### Note

-   If Create Calendar Events is ticked, the integration must be reloaded to take effect.

### Notification automation

If you wish to be notified a day before as a reminder then please use the code found in **automation.yaml** file which serves as a baseline on how to set it up. In my example it triggers at 20:00 the day before by showing a Home Assistant app notification specifying which bin needs to be placed out.

#### Note

-   This doesn't require the calendar feature to be enabled.

### Entities

-   x3 sensor entities for the types of bins - the state will be the next collection date, then subsequent dates are placed in state attributes called **all_dates**
    -   sensor.domestic_collections
    -   sensor.recycling_collections
    -   sensor.garden_food_collections
-   button entity for clearing persistent storage for the calendar bin events
    -   button.clear_bin_events
