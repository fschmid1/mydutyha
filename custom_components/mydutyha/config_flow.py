from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN
import re
import voluptuous as vol
from .api import MyDutyApi

DEFAULT_SYNC_TIMES = ["00:05", "12:00", "17:30"]


class MyDutyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            share_id = user_input.get("share_id")
            name = user_input.get("name")
            # Validate user_id format
            if not share_id or not str(share_id).isdigit():
                errors["share_id"] = "invalid_share_id"
            else:
                # Verify share exists by fetching duty types (this will also parse real userId)
                api = MyDutyApi(share_id)
                try:
                    duty_types = await api.fetch_duty_types()
                    if not duty_types:
                        # Try schedule as fallback
                        sched = await api.fetch_schedule()
                        body = sched.get("body") if isinstance(sched, dict) else None
                        if not body:
                            errors["share_id"] = "invalid_share_id"
                except Exception:
                    errors["share_id"] = "invalid_share_id"

            if not errors:
                # Store share_id in the config entry data
                entry_data = {"name": name, "share_id": share_id}
                return self.async_create_entry(title=name, data=entry_data)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("name"): str,
                vol.Required("share_id"): str,
            }),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return MyDutyOptionsFlowHandler(config_entry)


class MyDutyOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}
        
        if user_input is not None:
            # Collect times from the three separate fields
            times = []
            for i in range(1, 4):
                time_value = user_input.get(f"sync_time_{i}", "").strip()
                if time_value:
                    # Validate HH:MM format
                    if not re.match(r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$", time_value):
                        errors[f"sync_time_{i}"] = "invalid_format"
                    else:
                        times.append(time_value)
            
            # Ensure at least one time is provided
            if not times and not errors:
                errors["base"] = "at_least_one_time"
            
            if not errors:
                return self.async_create_entry(title="Sync Times", data={"sync_times": times})
        
        # Load existing sync times with defaults
        sync_times = self._config_entry.options.get("sync_times", DEFAULT_SYNC_TIMES)
        
        # Ensure we have at least 3 slots (pad with empty strings if needed)
        while len(sync_times) < 3:
            sync_times.append("")
        
        data_schema = vol.Schema({
            vol.Optional("sync_time_1", default=sync_times[0]): str,
            vol.Optional("sync_time_2", default=sync_times[1]): str,
            vol.Optional("sync_time_3", default=sync_times[2]): str,
        })
        
        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors,
        )
