# MyDutyHA

## Introduction

This integration was made for my wife, a nurse at the Geneva University Hospitals (Hopitaux Universitaires de Genève).

Retrieve your share id from your url, this way this components only access to your calendar readonly.

You can add multiple share id to handle more person inside the same home assistant entity.

## Installation

This integration is fully HACS compliant. Find it at:
https://github.com/Maypeur/MyDutyHA

1. Install via HACS (Home Assistant Community Store)
2. Restart Home Assistant
3. Add the MyDutyHA integration through the Home Assistant interface

## Configuration

- Add one or more persons (name, share_id, sync times)
- Customize sync times per person

## Automations

Example YAML automation to detect a worked day:

```yaml
alias: Notification for worked day
trigger:
  - platform: state
    entity_id: binary_sensor.myduty_1234567890123456_day_is_worked
    to: 'on'
action:
  - service: notify.mobile_app_your_app
    data:
      message: "You are working today!"
```

## Exposed Entities

- sensor.myduty_{share_id}_day_code
The code of the service.

- sensor.myduty_{share_id}_day_start
The hour your service start.

- sensor.myduty_{share_id}_day_end
The hour your service end.

- binary_sensor.myduty_{share_id}_day_is_worked
If your work the current day.

- binary_sensor.myduty_{share_id}_day_is_off
If your are on vacation this day.

- binary_sensor.myduty_{share_id}_is_night_shift
If your service started from the day before.


## Services

- `mydutyha.sync_now`: manual synchronization

## Logs

- Network and synchronization errors are logged in Home Assistant
