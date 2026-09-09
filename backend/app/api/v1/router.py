from fastapi import APIRouter
from app.api.v1 import (
    auth_routes,
    me_routes,
    resume_routes,
    alignment_routes,
    dashboard_routes,
    jd_routes,
    learning_routes,
    company_routes,
    note_routes,
    feedback_routes,
)

api_router = APIRouter()

api_router.include_router(auth_routes.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(me_routes.router, prefix="/me", tags=["Account"])
api_router.include_router(resume_routes.router, prefix="/resume", tags=["Resumes"])
api_router.include_router(alignment_routes.router, prefix="/alignment", tags=["Alignment"])
api_router.include_router(dashboard_routes.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(jd_routes.router, prefix="/jd", tags=["Job Descriptions"])
api_router.include_router(learning_routes.router, prefix="/learning", tags=["Learning"])
api_router.include_router(company_routes.router, prefix="/company", tags=["Company"])
api_router.include_router(note_routes.router, prefix="/notes", tags=["Notes"])
api_router.include_router(feedback_routes.router, prefix="/feedback", tags=["Feedback"])
