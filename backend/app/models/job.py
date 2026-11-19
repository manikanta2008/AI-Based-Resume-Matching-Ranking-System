from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime,
    func,
    UniqueConstraint
)

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database.connection import Base

# ==========================================
# JOB DESCRIPTION TABLE
# ==========================================

class JobDescription(Base):

    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True, index=True)

    # Original JD provided by recruiter
    original_jd = Column(Text, nullable=False)

    # text / pdf / docx
    source_type = Column(String(20), nullable=False)

    # AI extracted information
    title = Column(String(255), nullable=True)

    min_experience = Column(Integer, nullable=True)

    max_experience = Column(Integer, nullable=True)

    education = Column(JSONB, nullable=True)

    responsibilities = Column(JSONB, nullable=True)

    keywords = Column(JSONB, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationship with skills
    skills = relationship(
        "JobSkill",
        back_populates="job",
        cascade="all, delete-orphan"
    )


# ==========================================
# JOB SKILLS TABLE
# ==========================================

class JobSkill(Base):

    __tablename__ = "job_skills"

    id = Column(Integer, primary_key=True, index=True)

    job_id = Column(
        Integer,
        ForeignKey("job_descriptions.id", ondelete="CASCADE"),
        nullable=False
    )

    skill_name = Column(String(100), nullable=False)

    # required / preferred
    skill_type = Column(String(20), nullable=False)

    job = relationship(
        "JobDescription",
        back_populates="skills"
    )

    __table_args__ = (
        UniqueConstraint(
            "job_id",
            "skill_name",
            name="unique_job_skill"
        ),
    )