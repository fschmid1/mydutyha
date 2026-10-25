import aiohttp
import logging
import re, json
from datetime import datetime
from urllib.parse import urlsplit

_LOGGER = logging.getLogger(__name__)

# Share links come in two shapes. myduty.io/s/<share_id> is the original one;
# link.myduty.io/duty-share/<share_id> is what the app hands out today and it
# serves its schedule API from the same origin. Both pages are read-only and
# embed the real userId that the POST schedule API needs.
SHARE_URLS = (
    "https://link.myduty.io/duty-share/{share_id}",
    "https://myduty.io/s/{share_id}",
)
SCHEDULE_PATH = "/proxy/getUserDutySchedules"
TIMEOUT = aiohttp.ClientTimeout(total=10)


class MyDutyApi:
    def __init__(self, share_id):
        # `share_id` is the identifier present in the shared page URL.
        # The actual `userId` required by the POST schedule API is embedded in
        # the page and is extracted here, together with the origin that served
        # the page (`link.myduty.io` or `myduty.io`).
        self.share_id = str(share_id)
        self.user_id = None
        self.mode = "production"
        self.share_url = None
        self.schedule_url = None

    async def _async_load_share_page(self):
        """Fetch the share page, remember its origin, and return the duty units."""
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            for template in SHARE_URLS:
                url = template.format(share_id=self.share_id)
                try:
                    async with session.get(url, allow_redirects=False) as resp:
                        if resp.status != 200:
                            _LOGGER.debug("share page %s returned status %s", url, resp.status)
                            continue
                        html = await resp.text()
                except Exception:
                    _LOGGER.exception("share page request failed for %s", url)
                    continue

                units = self._parse_share_page(html)
                if not units:
                    _LOGGER.debug("share page %s carried no duty units", url)
                    continue

                split = urlsplit(url)
                self.share_url = url
                self.schedule_url = f"{split.scheme}://{split.netloc}{SCHEDULE_PATH}"
                return units

        return None

    def _parse_share_page(self, html):
        """Extract userId + duty units from a share page. Returns the units or None."""
        boot = self._parse_bootstrap(html)
        if boot is not None:
            if boot.get("userId"):
                self.user_id = str(boot["userId"])
            if boot.get("mode"):
                self.mode = boot["mode"]
            return boot.get("dutyUnits") or []

        # Legacy share page: userId in a script variable, units in a div.
        match = re.search(r'var\s+userId\s*=\s*"(\d+)"', html)
        if match:
            self.user_id = match.group(1)

        match = re.search(r'<div id="json_dutyUnits"[^>]*>(.*?)</div>', html, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(1).strip())
        except Exception:
            _LOGGER.exception("Failed to parse duty units JSON")
            return None

    @staticmethod
    def _parse_bootstrap(html):
        """The current share page embeds its data as a JSON script tag."""
        match = re.search(r'<script id="__myduty_bootstrap__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except Exception:
            _LOGGER.exception("Failed to parse share bootstrap JSON")
            return None

    async def fetch_duty_types(self):
        units = await self._async_load_share_page()
        if units is None:
            _LOGGER.error("Could not read a share page for share id %s", self.share_id)
            return []
        return units

    async def fetch_schedule(self):
        if self.schedule_url is None or self.user_id is None:
            await self.fetch_duty_types()
        if self.schedule_url is None or self.user_id is None:
            _LOGGER.error("Cannot fetch a schedule without a share page for %s", self.share_id)
            return {}

        # The Referer must be the share page itself, the same as the web view.
        headers = {"Referer": self.share_url}
        now = datetime.now()
        data = {
            "userId": str(self.user_id),
            "yyyy": str(now.year),
            "mm": f"{now.month:02d}",
            "mode": self.mode,
        }
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            try:
                async with session.post(self.schedule_url, headers=headers, data=data) as resp:
                    if resp.status != 200:
                        _LOGGER.error(
                            "fetch_schedule: unexpected status %s for %s",
                            resp.status,
                            self.schedule_url,
                        )
                        return {}
                    return await resp.json(content_type=None)
            except Exception:
                _LOGGER.exception("fetch_schedule: request failed for %s", self.schedule_url)
                return {}

    async def fetch_data(self):
        duty_types = await self.fetch_duty_types()
        schedule = await self.fetch_schedule()
        return {"duty_types": duty_types, "schedule": schedule}
