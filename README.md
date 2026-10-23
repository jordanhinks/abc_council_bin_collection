# Bin Collection for Northern Ireland ABC Council Area

Home Assistant component to pull data from Northern Ireland ABC Council website regarding bin collection dates based on address provided.

## Easy Installation:

1. Navigate to your HACs instance
2. Search ABC Council Bin Collection then download latest version

<details>
<summary style="list-style: none; cursor: pointer"><h2>Manual installation:</h2></summary>

1. Install this component by copying [these files](<[https://github.com/custom-components/sensor.sonarr_upcoming_media/tree/master/custom_components/sonarr_upcoming_media](https://github.com/jordanhinks/abc_council_bin_collection/tree/main/custom_components/abc_council_bin_collection)>) to `/custom_components/abc_council_bin_collection/`.
2. Restart Home Assistant
 </details>

## Setup Instructions:

<a href="https://my.home-assistant.io/redirect/config_flow_start?domain=abc_council_bin_collection" class="my badge" target="_blank"><img src="https://my.home-assistant.io/badges/config_flow_start.svg"></a>

1. Click above button **OR** navigate to Settings > Devices & Services
2. Click Add Integration, search ABC Council Bin Collection, then click the ABC Council Bin Collection
3. Enter your **postcode** into the input field and click Submit.
4. Select your specific address from the dropdown list and click Submit.

### Alternative Setup (Manual URL)

If the postcode lookup fails or you prefer manual entry:

1. Navigate to the [ABC Council website](https://www.armaghbanbridgecraigavon.gov.uk/resident/when-is-my-bin-day/).
2. Enter your postcode, click Submit, then select your house number and click Submit.
3. Copy the complete URL, or copy the ID value after **?address=**.
4. Paste the URL or value directly into the integration setup input field.

### Configure options

When the integration is added, the **Configure** button offers additional options/features.

- Update Interval (default: 120, minimum: 6) - Change the frequency it fetches data in hours. _(Note: The integration uses smart polling to automatically update on the day after a scheduled collection, up to this maximum interval)._
- Create Calendar Events (default: unticked) - Creates calendar events automatically
    - **Note:** Requires calendar such as Google Calendar to be installed and have read/write permission.
- Calendar Entity - Specify the calendar entity to create the events under
    - This accepts the entity of for example "calendar.my_calendar" or "my_calendar"
- Domestic Collections Summary, Recycling Collections Summary, and Garden & Food Collections Summary - allows you to specify the preferred calendar event name for the calendar events for each such as if you prefer the bin color.

### Notification automation

The easiest way to set up a reminder notification for your bins is by using our official Home Assistant Blueprint. This allows you to easily select your phone and preferred time without writing any YAML code.

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fjordanhinks%2Fabc_council_bin_collection%2Fblob%2Fmain%2Fblueprints%2Fbin_reminder.yaml)

If you prefer to create your own custom automations, you can use the newly added `sensor.[id]_next_collection` entity. It features a `days_until_collection` numeric attribute making it incredibly easy to trigger conditions (e.g., `days_until_collection < 2`).

### Entities

- x3 sensor entities for the types of bins - the state will be the next collection date, then subsequent dates are placed in state attributes called **all_dates**
    - sensor.[id]\_domestic_collection
    - sensor.[id]\_recycling_collection
    - sensor.[id]\_garden_food_collection
- x1 meta-sensor entity for the upcoming collections - the state will list all bins being collected next.
    - sensor.[id]\_next_collection
- button entity for clearing persistent storage for the calendar bin events
    - button.[id]\_clear_bin_events
