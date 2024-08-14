import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

class Course:
    def __init__(self, crn: str, term: str):
        self.crn = crn
        self.term = term
        self.url = f'https://oscar.gatech.edu/bprod/bwckschd.p_disp_detail_sched?term_in={self.term}&crn_in={self.crn}'
        self.refresh_course_data()

    def refresh_course_data(self):
        with requests.Session() as s:
            with s.get(self.url) as page:
                soup = BeautifulSoup(page.content, 'html.parser')
                headers = soup.find_all('th', class_="ddlabel")
                self.name = headers[0].getText() if headers else "Unknown"
                logger.info(f"Refreshed data for course: {self.name}")

    def get_registration_info(self):
        with requests.Session() as s:
            with s.get(self.url) as page:
                soup = BeautifulSoup(page.content, 'html.parser')
                table = soup.find('caption', string='Registration Availability')

                if not table:
                    logger.warning(f"Registration information not found for course: {self.name}")
                    return {'seats': 0, 'taken': 0, 'vacant': 0, 'waitlist': {'seats': 0, 'taken': 0, 'vacant': 0}}

                table = table.find_parent('table')
                data = [int(info.getText()) for info in table.findAll('td', class_='dddefault')]

                if len(data) < 6:
                    logger.warning(f"Insufficient registration data for course: {self.name}")
                    return {'seats': 0, 'taken': 0, 'vacant': 0, 'waitlist': {'seats': 0, 'taken': 0, 'vacant': 0}}

                waitlist_data = {
                    'seats': data[3],
                    'taken': data[4],
                    'vacant': data[5]
                }
                load = {
                    'seats': data[0],
                    'taken': data[1],
                    'vacant': data[2],
                    'waitlist': waitlist_data
                }
                logger.info(f"{self.name}: taken: {load['taken']}, vacant: {load['vacant']}, waitlist: {load['waitlist']['vacant']}")
                return load

    def is_open(self) -> bool:
        return self.get_registration_info()['vacant'] > 0

    def waitlist_available(self) -> bool:
        return self.get_registration_info()['waitlist']['vacant'] > 0

    def __str__(self) -> str:
        data = self.get_registration_info()
        res = f"{self.name}\n"
        for name, value in data.items():
            if name != 'waitlist':
                res += f"{name}:\t{value}\n"
        res += f"waitlist open: {'yes' if self.waitlist_available() else 'no'}\n"
        return res
