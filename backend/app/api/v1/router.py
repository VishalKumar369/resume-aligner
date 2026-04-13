from fastapi import APIRouter
from app.api.v1 import (
    auth_routes,
    resume_routes,
    alignment_routes,
    dashboard_routes
)

api_router = APIRouter()

api_router.include_router(auth_routes.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(resume_routes.router, prefix="/resume", tags=["Resumes"])
api_router.include_router(alignment_routes.router, prefix="/alignment", tags=["Alignment"])
api_router.include_router(dashboard_routes.router, prefix="/dashboard", tags=["Dashboard"])
