from ..models.course import Course
from ..services.config_service import get_user_courses, get_term, convert_term_to_code, get_user_logfile
import asyncio
import logging

class CourseState:
    def __init__(self):
        self.is_open = False
        self.waitlist_available = False
        self.seats_available = 0
        self.waitlist_seats = 0
        self.last_notification = None

class CourseService:
    def __init__(self, notification_service):
        self.notification_service = notification_service
        self.courses = {}
        self.course_states = {}
        self.user_loggers = {}
        self.user_tasks = {}

    async def initialize_user_courses(self, user_uuid):
        user_courses = get_user_courses(user_uuid)
        term = get_term()
        term_code = convert_term_to_code(term)
        for crn in user_courses:
            course = Course(crn, term_code)
            self.courses[f"{user_uuid}_{crn}"] = course
            self.course_states[f"{user_uuid}_{crn}"] = CourseState()

        # Initialize user-specific logger
        logfile = get_user_logfile(user_uuid)
        if logfile:
            logger = logging.getLogger(f"user_{user_uuid}")
            logger.setLevel(logging.INFO)
            file_handler = logging.FileHandler(logfile)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            logger.addHandler(file_handler)
            self.user_loggers[user_uuid] = logger

    async def check_courses(self, user_uuid):
        logger = self.user_loggers.get(user_uuid)
        while True:
            user_courses = {key: course for key, course in self.courses.items() if key.startswith(f"{user_uuid}_")}
            for course_key, course in user_courses.items():
                course.refresh_course_data()
                current_state = self.course_states[course_key]
                registration_info = course.get_registration_info()

                new_is_open = registration_info['vacant'] > 0
                new_waitlist_available = registration_info['waitlist']['vacant'] > 0
                new_seats_available = registration_info['vacant']
                new_waitlist_seats = registration_info['waitlist']['vacant']

                messages = []

                if new_is_open and not current_state.is_open:
                    messages.append(f"Course open: {course.name}")
                elif not new_is_open and current_state.is_open:
                    messages.append(f"Course closed: {course.name}")

                if new_is_open:
                    if new_seats_available <= 5 and current_state.seats_available > 5:
                        messages.append(f"Only {new_seats_available} seats remaining for {course.name}")
                    elif new_seats_available - current_state.seats_available >= 3:
                        messages.append(f"{new_seats_available - current_state.seats_available} new seats opened for {course.name}")
                elif new_waitlist_available and not current_state.waitlist_available:
                    messages.append(f"Waitlist now available for {course.name}")
                elif new_waitlist_available:
                    if new_waitlist_seats <= 5 and current_state.waitlist_seats > 5:
                        messages.append(f"Only {new_waitlist_seats} waitlist spots remaining for {course.name}")
                    elif new_waitlist_seats - current_state.waitlist_seats >= 3:
                        messages.append(f"{new_waitlist_seats - current_state.waitlist_seats} new waitlist spots opened for {course.name}")

                for message in messages:
                    await self.notification_service.send_notification(user_uuid, message)
                    if logger:
                        logger.info(message)

                # Update the stored state
                current_state.is_open = new_is_open
                current_state.waitlist_available = new_waitlist_available
                current_state.seats_available = new_seats_available
                current_state.waitlist_seats = new_waitlist_seats

            await asyncio.sleep(10)  # Wait for 10 seconds before checking again

    def get_courses_info(self, user_uuid):
        return [str(course) for key, course in self.courses.items() if key.startswith(f"{user_uuid}_")]

    async def start_user_task(self, user_uuid):
        await self.initialize_user_courses(user_uuid)
        if user_uuid not in self.user_tasks or self.user_tasks[user_uuid].done():
            self.user_tasks[user_uuid] = asyncio.create_task(self.check_courses(user_uuid))

    async def stop_user_task(self, user_uuid):
        if user_uuid in self.user_tasks:
            self.user_tasks[user_uuid].cancel()
            await self.user_tasks[user_uuid]
            del self.user_tasks[user_uuid]
