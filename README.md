# Home Assistant National Rail API Integration

This is an integration for the national rail API into home assistant.
This allows you to have a schedule of the train at your station in your home assistant.

1. Register with national rail to get an api token [here](http://realtime.nationalrail.co.uk/OpenLDBWSRegistration/)
   
# Installation
## HACS
This repo is HACS compatible and can be added in to the custom repositories in HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=plutomedia987&repository=homeassistant_nationalrail&category=Integration)

## Manual
1. Copy the custom_components/nationalrailuk folder into your config/custom_components folder and restart home assistant
2. Find the crs code for your origin and destination station using the [National Rail website](https://www.nationalrail.co.uk/). If you live in Weybridge and commutte to Waterloo, the codes are WYB and WAT
3. You need to add 2 integration for for monitoring your morning journey WYB to WAT and one for your evening route WAT to WYB
4. This should create 2 sensors `sensor.train_schedule_wyb_wat` and `sensor.train_schedule_wat_wyb`

## Custom Card
A custom card for this integration can be found here:
https://github.com/plutomedia987/lovelace-nationalrail

# Fair use policy

National Rail limits API call to five million requests per four week railway period.
An update every minute for a 4 week period would require 40,320 request. You could therefore have 124 those sensors.

We are currently refreshing once every 15 minutes in normal conditions but starts updating every minutes if we are within 5 minutes of the planned departure time or if the train is delayed

# Support / Questions

Please raise questions in the thread on the 
[home assistant forum](https://community.home-assistant.io/t/national-rail-integration-fork-of-jfparis/803104/41)

