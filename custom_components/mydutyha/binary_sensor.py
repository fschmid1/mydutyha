from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity


class MyDutyIsWorkedSensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator, share_id):
        super().__init__(coordinator)
        self._attr_name = f"MyDuty {share_id} Is Worked"
        self._attr_unique_id = f"myduty_{share_id}_day_is_worked"

    @property
    def is_on(self):
        return self.coordinator.data.get("day_is_worked")

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        return {
            "start_time": self.coordinator.data.get("day_ha_start"),
            "end_time": self.coordinator.data.get("day_ha_end"),
            "is_night_shift": self.coordinator.data.get("is_night_shift", False),
            "day_code": self.coordinator.data.get("day_code"),
        }

    @property
    def available(self) -> bool:
        return bool(self.coordinator and getattr(self.coordinator, "last_update_success", True))


class MyDutyIsOffSensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator, share_id):
        super().__init__(coordinator)
        self._attr_name = f"MyDuty {share_id} Is Off"
        self._attr_unique_id = f"myduty_{share_id}_day_is_off"

    @property
    def is_on(self):
        return self.coordinator.data.get("day_is_off")

    @property
    def available(self) -> bool:
        return bool(self.coordinator and getattr(self.coordinator, "last_update_success", True))


class MyDutyIsNightShiftSensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator, share_id):
        super().__init__(coordinator)
        self._attr_name = f"MyDuty {share_id} Is Night Shift"
        self._attr_unique_id = f"myduty_{share_id}_is_night_shift"

    @property
    def is_on(self):
        return self.coordinator.data.get("is_night_shift")

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        return {
            "start_time": self.coordinator.data.get("day_ha_start"),
            "end_time": self.coordinator.data.get("day_ha_end"),
            "day_code": self.coordinator.data.get("day_code"),
        }

    @property
    def available(self) -> bool:
        return bool(self.coordinator and getattr(self.coordinator, "last_update_success", True))


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["mydutyha"][entry.entry_id]
    share_id = entry.data.get("share_id")
    entities = [
        MyDutyIsWorkedSensor(coordinator, share_id),
        MyDutyIsOffSensor(coordinator, share_id),
        MyDutyIsNightShiftSensor(coordinator, share_id),
    ]
    async_add_entities(entities, True)
