from fastapi import FastAPI
from nissan_gtr.routers import courses
from nissan_gtr.services.notification_service import NotificationService
from nissan_gtr.services.course_service import CourseService
from nissan_gtr.services.config_service import get_users
import asyncio

app = FastAPI()

notification_service = NotificationService()
course_service = CourseService(notification_service)

app.include_router(courses.router)

@app.on_event("startup")
async def startup_event():
    users = get_users()
    if users:
        for user in users:
            user_uuid = list(user.keys())[0]  # Get the UUID (key) of the user
            await course_service.start_user_task(user_uuid)
    else:
        print("No users found. Please add users to start monitoring courses.")

@app.get("/")
async def root():
    return {"message": "Welcome to the Registration Helper"}
