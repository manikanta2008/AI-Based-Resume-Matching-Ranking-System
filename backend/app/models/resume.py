from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
    func
)

from sqlalchemy.dialects.postgresql import JSONB

from app.database.connection import Base


# ==========================================
# RESUME TABLE
# ==========================================

class Resume(Base):

    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)

    # ======================================
    # RESUME FILE INFORMATION
    # ======================================

    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)
    file_path = Column(String(500), nullable=True)
    file_hash = Column(String(64), nullable=True, index=True)

    # ======================================
    # CANDIDATE PERSONAL INFORMATION
    # ======================================

    full_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True)

    # ======================================
    # SKILLS
    # ======================================

    technical_skills = Column(JSONB, nullable=True)
    soft_skills = Column(JSONB, nullable=True)

    # ======================================
    # EDUCATION
    # ======================================

    education = Column(JSONB, nullable=True)

    # ======================================
    # EXPERIENCE
    # ======================================

    work_experience = Column(Float, nullable=True)
    previous_companies = Column(JSONB, nullable=True)
    experience_details = Column(JSONB, nullable=True)

    # ======================================
    # PROJECTS
    # ======================================

    projects = Column(JSONB, nullable=True)

    # ======================================
    # CERTIFICATIONS
    # ======================================

    certifications = Column(JSONB, nullable=True)

    # ======================================
    # PROFESSIONAL LINKS
    # ======================================

    professional_links = Column(JSONB, nullable=True)

    # ======================================
    # ORIGINAL RESUME CONTENT
    # ======================================

    raw_text = Column(Text, nullable=True)

    # ======================================
    # TIMESTAMP
    # ======================================

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )