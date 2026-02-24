import aiohttp
import logging
import re, json

_LOGGER = logging.getLogger(__name__)

class MyDutyApi:
    def __init__(self, share_id):
        # `share_id` is the identifier present in the shared page URL (/s/<share_id>).
        # The actual `userId` required by the POST schedule API is embedded in the page
        # and will be extracted when fetching duty types. We store it in `self.user_id`.
        self.share_id = share_id
        self.user_id = None

    async def fetch_duty_types(self):
        url = f"https://myduty.io/s/{self.share_id}"
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        _LOGGER.error("fetch_duty_types: unexpected status %s for %s", resp.status, url)
                        return []
                    html = await resp.text()
            except Exception as e:
                _LOGGER.exception("fetch_duty_types: request failed for %s", url)
                return []

        # Also extract the actual userId value embedded in the page javascript (if present)
        m_user = re.search(r'var\s+userId\s*=\s*"(\d+)"', html)
        if m_user:
            try:
                self.user_id = m_user.group(1)
            except Exception:
                self.user_id = None

        match = re.search(r'<div id="json_dutyUnits"[^>]*>(.*?)</div>', html, re.DOTALL)
        if match:
            json_str = match.group(1).strip()
            try:
                duty_units = json.loads(json_str)
                return duty_units
            except Exception:
                _LOGGER.exception("Failed to parse duty units JSON")
                return []
        else:
            _LOGGER.warning("json_dutyUnits div not found in HTML for user %s", self.user_id)
            return []

    async def fetch_schedule(self):
        url = "https://myduty.io/proxy/getUserDutySchedules"
        # The Referer must be the shared page (share_id). The POST payload requires
        # the actual `userId`; prefer the parsed `self.user_id` if available.
        headers = {"Referer": f"https://myduty.io/s/{self.share_id}"}
        # Prepare POST data
        from datetime import datetime
        now = datetime.now()
        data = {
            "userId": str(self.user_id),
            "yyyy": str(now.year),
            "mm": f"{now.month:02d}",
            "mode": "production"
        }
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.post(url, headers=headers, data=data) as resp:
                    if resp.status != 200:
                        _LOGGER.error("fetch_schedule: unexpected status %s for %s", resp.status, url)
                        return {}
                    return await resp.json()
            except Exception:
                _LOGGER.exception("fetch_schedule: request failed for %s", url)
                return {}

    async def fetch_data(self):
        duty_types = await self.fetch_duty_types()
        schedule = await self.fetch_schedule()
        return {"duty_types": duty_types, "schedule": schedule}
