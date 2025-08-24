import aiohttp
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


class Course:
    def __init__(self, crn: str, term: str):
        self.crn = crn
        self.term = term
        self.url = f"https://oscar.gatech.edu/bprod/bwckschd.p_disp_detail_sched?term_in={self.term}&crn_in={self.crn}"
        self.name = "Unknown"
        self.session = None

    async def get_session(self):
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=10)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def close_session(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def refresh_course_data(self):
        session = await self.get_session()
        try:
            async with session.get(self.url) as response:
                content = await response.text()
                soup = BeautifulSoup(content, "html.parser")
                headers = soup.find_all("th", class_="ddlabel")
                self.name = headers[0].getText() if headers else "Unknown"
                logger.info(f"Refreshed data for course: {self.name}")
        except Exception as e:
            logger.error(f"Error refreshing course data for {self.crn}: {e}")

    async def get_registration_info(self):
        session = await self.get_session()
        try:
            async with session.get(self.url) as response:
                content = await response.text()
                soup = BeautifulSoup(content, "html.parser")
                table = soup.find("caption", string="Registration Availability")

                if not table:
                    logger.warning(
                        f"Registration information not found for course: {self.name}"
                    )
                    return {
                        "seats": 0,
                        "taken": 0,
                        "vacant": 0,
                        "waitlist": {"seats": 0, "taken": 0, "vacant": 0},
                    }

                table = table.find_parent("table")
                data = [
                    int(info.getText())
                    for info in table.findAll("td", class_="dddefault")
                ]

                if len(data) < 6:
                    logger.warning(
                        f"Insufficient registration data for course: {self.name}"
                    )
                    return {
                        "seats": 0,
                        "taken": 0,
                        "vacant": 0,
                        "waitlist": {"seats": 0, "taken": 0, "vacant": 0},
                    }

                waitlist_data = {"seats": data[3], "taken": data[4], "vacant": data[5]}
                load = {
                    "seats": data[0],
                    "taken": data[1],
                    "vacant": data[2],
                    "waitlist": waitlist_data,
                }
                logger.info(
                    f"{self.name}: taken: {load['taken']}, vacant: {load['vacant']}, waitlist: {load['waitlist']['vacant']}"
                )
                return load
        except Exception as e:
            logger.error(f"Error getting registration info for {self.crn}: {e}")
            return {
                "seats": 0,
                "taken": 0,
                "vacant": 0,
                "waitlist": {"seats": 0, "taken": 0, "vacant": 0},
            }

    async def is_open(self) -> bool:
        info = await self.get_registration_info()
        return info["vacant"] > 0

    async def waitlist_available(self) -> bool:
        info = await self.get_registration_info()
        return info["waitlist"]["vacant"] > 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_session()

    def __str__(self) -> str:
        return f"{self.name} (CRN: {self.crn})"
