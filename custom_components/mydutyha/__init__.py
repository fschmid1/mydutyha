# MyDutyHA custom component initialization

from homeassistant.helpers.event import async_track_time_change
from .coordinator import MyDutyCoordinator
from .const import DOMAIN

async def async_setup_entry(hass, entry):
    # Setup coordinator and platforms
    coordinator = MyDutyCoordinator(hass, entry)

    hass.data.setdefault('mydutyha', {})[entry.entry_id] = coordinator
    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, ['sensor', 'binary_sensor'])

    # Schedule synchronizations based on user configuration
    async def scheduled_update(now):
        await coordinator.async_request_refresh()

    DEFAULT_SYNC_TIMES = ["00:05", "12:00", "17:30"]
    sync_times = entry.options.get("sync_times", DEFAULT_SYNC_TIMES)
    for sync_time in sync_times:
        try:
            hour, minute = map(int, sync_time.split(":"))
        except Exception:
            continue
        async_track_time_change(
            hass,
            scheduled_update,
            hour=hour,
            minute=minute,
            second=0,
        )
    # Register service to force sync
    async def handle_sync_now(call):
        share_id = call.data.get("share_id")
        # find matching entries
        entries = hass.config_entries.async_entries(DOMAIN)
        if share_id:
            for e in entries:
                if str(e.data.get("share_id")) == str(share_id):
                    coord = hass.data.get("mydutyha", {}).get(e.entry_id)
                    if coord:
                        await coord.async_request_refresh()
        else:
            for coord in hass.data.get("mydutyha", {}).values():
                await coord.async_request_refresh()

    hass.services.async_register(DOMAIN, "sync_now", handle_sync_now)
    return True

async def async_unload_entry(hass, entry):

    await hass.config_entries.async_unload_platforms(entry, ['sensor', 'binary_sensor'])
    hass.data['mydutyha'].pop(entry.entry_id)

    # If no more entries, remove the service
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        try:
            hass.services.async_remove(DOMAIN, "sync_now")
        except Exception:
            _ = None

    return True
