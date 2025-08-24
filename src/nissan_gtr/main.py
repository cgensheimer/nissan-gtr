from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from nissan_gtr.routers import courses
from nissan_gtr.services.notification_service import NotificationService
from nissan_gtr.services.course_service import CourseService
from nissan_gtr.services.config_service import (
    get_users,
    get_user_by_uuid,
    add_user,
    add_crn_to_user,
    remove_crn_from_user,
    validate_user_password,
)
import asyncio

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

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


@app.get("/dashboard", response_class=HTMLResponse)
async def main_dashboard(request: Request):
    users = get_users()
    users_list = []
    for user_dict in users:
        for user_uuid, user_data in user_dict.items():
            users_list.append({"uuid": user_uuid, "name": user_data["name"]})

    return templates.TemplateResponse(
        request=request, name="users_list.html", context={"users": users_list}
    )


@app.post("/dashboard/create-user")
async def create_user(name: str = Form(...), password: str = Form(...)):
    if not name.strip() or not password.strip():
        raise HTTPException(status_code=400, detail="Name and password are required")

    user_uuid, user_data = add_user(name.strip(), password)

    # Start monitoring for this new user
    await course_service.start_user_task(user_uuid)

    return RedirectResponse(url=f"/dashboard/{user_uuid}", status_code=303)


@app.post("/dashboard/{user_uuid}/add-course")
async def add_course_to_user(
    user_uuid: str, crn: str = Form(...), password: str = Form(...)
):
    # Validate password
    if not validate_user_password(user_uuid, password):
        raise HTTPException(status_code=401, detail="Invalid password")

    if not crn.strip():
        raise HTTPException(status_code=400, detail="CRN is required")

    # Add the course
    success = add_crn_to_user(user_uuid, crn.strip())
    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    # Restart user monitoring to include new course
    await course_service.stop_user_task(user_uuid)
    await course_service.start_user_task(user_uuid)

    return RedirectResponse(url=f"/dashboard/{user_uuid}", status_code=303)


@app.post("/dashboard/{user_uuid}/remove-course")
async def remove_course_from_user(
    user_uuid: str, crn: str = Form(...), password: str = Form(...)
):
    # Validate password
    if not validate_user_password(user_uuid, password):
        raise HTTPException(status_code=401, detail="Invalid password")

    if not crn.strip():
        raise HTTPException(status_code=400, detail="CRN is required")

    # Remove the course
    success = remove_crn_from_user(user_uuid, crn.strip())

    if not success:
        raise HTTPException(status_code=404, detail="Course not found for this user")

    # Restart user monitoring to reflect the course removal
    await course_service.stop_user_task(user_uuid)
    await course_service.start_user_task(user_uuid)

    return RedirectResponse(url=f"/dashboard/{user_uuid}", status_code=303)


@app.get("/dashboard/{user_uuid}", response_class=HTMLResponse)
async def user_dashboard(request: Request, user_uuid: str):
    user = get_user_by_uuid(user_uuid)
    if not user:
        return templates.TemplateResponse(
            request=request, name="error.html", context={"error": "User not found"}
        )

    # Get course information for this user
    courses_info = []
    user_courses = {
        key: course
        for key, course in course_service.courses.items()
        if key.startswith(f"{user_uuid}_")
    }

    async def get_course_info(course_key, course):
        state = course_service.course_states.get(course_key)
        reg_info = await course.get_registration_info()

        return {
            "name": course.name,
            "crn": course.crn,
            "is_open": reg_info["vacant"] > 0,
            "seats_available": reg_info["vacant"],
            "total_seats": reg_info["seats"],
            "waitlist_available": reg_info["waitlist"]["vacant"] > 0,
            "waitlist_spots": reg_info["waitlist"]["vacant"],
            "total_waitlist": reg_info["waitlist"]["seats"],
            "url": course.url,
        }

    # Gather course info in parallel
    tasks = [
        get_course_info(course_key, course)
        for course_key, course in user_courses.items()
    ]
    if tasks:
        courses_info = await asyncio.gather(*tasks, return_exceptions=True)
        # Filter out any exceptions
        courses_info = [
            info for info in courses_info if not isinstance(info, Exception)
        ]

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"user": user, "user_uuid": user_uuid, "courses": courses_info},
    )
