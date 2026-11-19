from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.database.connection import engine, Base

# Import models so SQLAlchemy knows about the tables
from app.models.job import JobDescription, JobSkill
from app.models.resume import Resume

from app.routes.job_routes import router as job_router
from app.routes.resume_routes import router as resume_router
from fastapi.middleware.cors import CORSMiddleware


# ==========================================
# CREATE DATABASE TABLES
# ==========================================

try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Database initialization warning (will connect on requests): {e}")



# ==========================================
# FASTAPI APPLICATION
# ==========================================

app = FastAPI(
    title="AI Resume Parser",
    description="AI-powered Resume Matching and Candidate Ranking Platform",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# REGISTER ROUTES
# ==========================================

app.include_router(job_router)
app.include_router(resume_router)


# ==========================================
# CUSTOM OPENAPI SCHEMA
# ==========================================

def custom_openapi():

    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes
    )

    # Convert file upload schemas to Swagger-compatible format
    def update_file_schema(schema):

        if isinstance(schema, dict):

            if (
                schema.get("type") == "string"
                and schema.get("contentMediaType") == "application/octet-stream"
            ):
                schema["format"] = "binary"
                schema.pop("contentMediaType", None)

            for value in schema.values():
                update_file_schema(value)

        elif isinstance(schema, list):

            for item in schema:
                update_file_schema(item)

    update_file_schema(openapi_schema)

    app.openapi_schema = openapi_schema

    return app.openapi_schema


app.openapi = custom_openapi


# ==========================================
# HOME ROUTE
# ==========================================

@app.get("/")
def home():

    return {
        "message": "AI Resume Parser API is running!"
    }