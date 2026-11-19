import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.database.connection import engine, Base
from app.models.job import JobDescription, JobSkill
from app.models.resume import Resume
from app.routes.job_routes import router as job_router
from app.routes.resume_routes import router as resume_router

try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Database initialization warning (will connect on requests): {e}")

app = FastAPI(
    title="AI Resume Parser",
    description="AI-powered Resume Matching and Candidate Ranking Platform",
    version="1.0.0",
)

origins = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(job_router)
app.include_router(resume_router)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

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


@app.get("/")
def home():
    return {"message": "AI Resume Parser API is running!"}
