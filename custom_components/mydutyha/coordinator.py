import logging
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .api import MyDutyApi
from datetime import datetime, timedelta

_LOGGER = logging.getLogger(__name__)

class MyDutyCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        # Entry stores `share_id`; API will parse the real `userId` from the page.
        self.api = MyDutyApi(entry.data.get("share_id"))
        super().__init__(
            hass,
            _LOGGER,
            name="MyDutyHA Coordinator",
            update_interval=None,  # Will be set per user
        )

    async def _async_update_data(self):
        try:
            retries = 3
            delay = 1
            last_exc = None
            raw = {}
            for attempt in range(1, retries + 1):
                try:
                    raw = await self.api.fetch_data()
                    last_exc = None
                    break
                except Exception as err:
                    last_exc = err
                    _LOGGER.warning(
                        "Attempt %s/%s failed fetching MyDuty data: %s",
                        attempt,
                        retries,
                        err,
                    )
                    if attempt < retries:
                        import asyncio

                        await asyncio.sleep(delay)
                        delay *= 2
                    else:
                        _LOGGER.exception("All attempts failed fetching MyDuty data")
                        raise UpdateFailed(f"Error fetching data after {retries} attempts: {err}")

            duty_types = raw.get("duty_types", [])
            schedule = raw.get("schedule", {})

            # Build map of dutyUnitId -> duty type
            duty_map = {}
            for d in duty_types:
                # normalize ids to str
                duty_map[str(d.get("dutyUnitId"))] = d

            # Extract duty schedule entries
            duty_entries = []
            try:
                duty_entries = schedule.get("body", {}).get("schedules", {}).get("duty", [])
            except Exception:
                duty_entries = []

            # Find today's entry
            now = datetime.now()

            def find_entry_for_date(target_date):
                """Find entry for a specific date"""
                for entry in duty_entries:
                    if (
                        str(entry.get("year")) == str(target_date.year)
                        and str(entry.get("month")).zfill(2) == f"{target_date.month:02d}"
                        and str(entry.get("day")).zfill(2) == f"{target_date.day:02d}"
                    ):
                        return entry
                return None

            today_entry = find_entry_for_date(now)
            yesterday = now - timedelta(days=1)
            yesterday_entry = find_entry_for_date(yesterday)

            result = {
                "raw": raw,
                "day_code": None,
                "day_ha_start": None,
                "day_ha_end": None,
                "day_is_worked": False,
                "day_is_off": False,
                "is_night_shift": False,
            }

            def fmt(t):
                """Convert time like '0700' -> '07:00'"""
                if not t:
                    return None
                s = str(t).zfill(4)
                return f"{s[0:2]}:{s[2:4]}"

            def time_to_minutes(time_str):
                """Convert HH:MM to minutes since midnight"""
                if not time_str:
                    return 0
                h, m = map(int, time_str.split(":"))
                return h * 60 + m

            # Check if yesterday's shift extends into today (night shift)
            if yesterday_entry:
                uid_yesterday = str(yesterday_entry.get("dutyUnitId"))
                duty_yesterday = duty_map.get(uid_yesterday)
                
                if duty_yesterday:
                    start_time = fmt(duty_yesterday.get("startTime"))
                    end_time = fmt(duty_yesterday.get("endTime"))
                    
                    if start_time and end_time:
                        start_minutes = time_to_minutes(start_time)
                        end_minutes = time_to_minutes(end_time)
                        
                        # If end time < start time, it's a night shift
                        if end_minutes < start_minutes:
                            is_off = bool(duty_yesterday.get("isOffDay")) or bool(duty_yesterday.get("isVacation"))
                            
                            if not is_off:
                                # This is a night shift from yesterday extending into today
                                result["day_code"] = duty_yesterday.get("title")
                                result["day_ha_start"] = start_time
                                result["day_ha_end"] = end_time
                                result["day_is_worked"] = True
                                result["day_is_off"] = False
                                result["is_night_shift"] = True
                                
                                _LOGGER.debug("Night shift detected from yesterday: %s-%s", start_time, end_time)
                                return result

            # Process today's entry if no night shift from yesterday
            if today_entry:
                uid = str(today_entry.get("dutyUnitId"))
                duty = duty_map.get(uid)
                if duty:
                    # title as code
                    result["day_code"] = duty.get("title")

                    start_time = fmt(duty.get("startTime"))
                    end_time = fmt(duty.get("endTime"))
                    
                    result["day_ha_start"] = start_time
                    result["day_ha_end"] = end_time
                    
                    is_off = bool(duty.get("isOffDay")) or bool(duty.get("isVacation"))
                    result["day_is_off"] = is_off
                    result["day_is_worked"] = not is_off
                    
                    # Check if this is a night shift extending into tomorrow
                    if start_time and end_time:
                        start_minutes = time_to_minutes(start_time)
                        end_minutes = time_to_minutes(end_time)
                        
                        if end_minutes < start_minutes:
                            result["is_night_shift"] = True
                            _LOGGER.debug("Night shift detected for today: %s-%s", start_time, end_time)

            _LOGGER.debug("MyDutyCoordinator updated result: %s", result)
            return result
        except Exception as err:
            _LOGGER.exception("Error updating MyDuty data")
            raise UpdateFailed(f"Error fetching data: {err}")
