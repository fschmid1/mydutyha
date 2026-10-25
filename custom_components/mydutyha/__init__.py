# MyDutyHA custom component initialization

from homeassistant.helpers.event import async_track_time_change
from .coordinator import MyDutyCoordinator
from .const import DOMAIN

DEFAULT_SYNC_TIMES = ["00:05", "12:00", "17:30"]


async def async_setup_entry(hass, entry):
    # Setup coordinator and platforms
    coordinator = MyDutyCoordinator(hass, entry)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, ['sensor', 'binary_sensor'])

    # Schedule synchronizations based on user configuration
    async def scheduled_update(now):
        await coordinator.async_request_refresh()

    sync_times = entry.options.get("sync_times", DEFAULT_SYNC_TIMES)
    unsubs = []
    for sync_time in sync_times:
        try:
            hour, minute = map(int, sync_time.split(":"))
        except Exception:
            continue
        unsubs.append(
            async_track_time_change(
                hass,
                scheduled_update,
                hour=hour,
                minute=minute,
                second=0,
            )
        )

    def remove_time_listeners():
        while unsubs:
            unsubs.pop()()

    entry.async_on_unload(remove_time_listeners)

    # Changed sync times only apply once the entry is set up again
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    # Register service to force sync
    async def handle_sync_now(call):
        share_id = call.data.get("share_id")
        # find matching entries
        entries = hass.config_entries.async_entries(DOMAIN)
        if share_id:
            for e in entries:
                if str(e.data.get("share_id")) == str(share_id):
                    coord = hass.data.get(DOMAIN, {}).get(e.entry_id)
                    if coord:
                        await coord.async_request_refresh()
        else:
            for coord in hass.data.get(DOMAIN, {}).values():
                await coord.async_request_refresh()

    hass.services.async_register(DOMAIN, "sync_now", handle_sync_now)
    return True


async def _async_options_updated(hass, entry):
    """Reload the entry so new sync times take effect without a restart."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    await hass.config_entries.async_unload_platforms(entry, ['sensor', 'binary_sensor'])
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)

    # If no more entries, remove the service
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        try:
            hass.services.async_remove(DOMAIN, "sync_now")
        except Exception:
            _ = None

    return True
