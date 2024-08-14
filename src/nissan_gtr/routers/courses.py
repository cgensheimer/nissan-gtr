from fastapi import APIRouter, Depends, HTTPException
from nissan_gtr.services.course_service import CourseService
from nissan_gtr.services.config_service import add_user, add_crn_to_user, get_users, get_user_by_uuid, get_user_uuid_by_name

router = APIRouter()

# We'll use dependency injection to get the course_service
def get_course_service():
    from nissan_gtr.main import course_service
    return course_service

@router.get("/courses/{user_uuid}")
async def get_courses(user_uuid: str, course_service: CourseService = Depends(get_course_service)):
    user = get_user_by_uuid(user_uuid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"courses": course_service.get_courses_info(user_uuid)}

@router.post("/users")
async def create_user(name: str, course_service: CourseService = Depends(get_course_service)):
    user_uuid, new_user = add_user(name)
    await course_service.start_user_task(user_uuid)
    return {"message": f"User {name} added successfully", "uuid": user_uuid, "ntfy_topic": new_user['ntfy_topic']}

@router.get("/users")
async def list_users():
    return {"users": get_users()}

@router.post("/users/{user_uuid}/courses")
async def add_course_to_user(user_uuid: str, crn: str, course_service: CourseService = Depends(get_course_service)):
    if add_crn_to_user(user_uuid, crn):
        await course_service.initialize_user_courses(user_uuid)
        return {"message": f"CRN {crn} added to user with UUID {user_uuid}"}
    else:
        raise HTTPException(status_code=404, detail="User not found or CRN already exists")

@router.get("/users/by-name/{name}")
async def get_user_uuid(name: str):
    user_uuid = get_user_uuid_by_name(name)
    if user_uuid:
        return {"uuid": user_uuid}
    else:
        raise HTTPException(status_code=404, detail="User not found")
