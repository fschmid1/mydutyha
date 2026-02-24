from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity


def _create_base_attrs(share_id, suffix):
    return {
        "name": f"MyDuty {share_id} {suffix}",
        "unique_id": f"myduty_{share_id}_{suffix.lower().replace(' ', '_')}"
    }


class MyDutyDayCodeSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, share_id):
        super().__init__(coordinator)
        attrs = _create_base_attrs(share_id, "Day Code")
        self._attr_name = attrs["name"]
        self._attr_unique_id = attrs["unique_id"]

    @property
    def state(self):
        return self.coordinator.data.get("day_code")

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        return {
            "is_night_shift": self.coordinator.data.get("is_night_shift", False),
            "is_worked": self.coordinator.data.get("day_is_worked", False),
            "is_off": self.coordinator.data.get("day_is_off", False),
        }

    @property
    def available(self) -> bool:
        return bool(self.coordinator and getattr(self.coordinator, "last_update_success", True))


class MyDutyDayStartSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, share_id):
        super().__init__(coordinator)
        attrs = _create_base_attrs(share_id, "Day Start")
        self._attr_name = attrs["name"]
        self._attr_unique_id = attrs["unique_id"]

    @property
    def state(self):
        return self.coordinator.data.get("day_ha_start")

    @property
    def available(self) -> bool:
        return bool(self.coordinator and getattr(self.coordinator, "last_update_success", True))


class MyDutyDayEndSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, share_id):
        super().__init__(coordinator)
        attrs = _create_base_attrs(share_id, "Day End")
        self._attr_name = attrs["name"]
        self._attr_unique_id = attrs["unique_id"]

    @property
    def state(self):
        return self.coordinator.data.get("day_ha_end")

    @property
    def available(self) -> bool:
        return bool(self.coordinator and getattr(self.coordinator, "last_update_success", True))


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["mydutyha"][entry.entry_id]
    share_id = entry.data.get("share_id")
    entities = [
        MyDutyDayCodeSensor(coordinator, share_id),
        MyDutyDayStartSensor(coordinator, share_id),
        MyDutyDayEndSensor(coordinator, share_id),
    ]
    async_add_entities(entities, True)
