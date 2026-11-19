from sqlalchemy import (
    Column,
    Integer,
    Float,
    Text,
    ForeignKey,
    DateTime,
    func,
    UniqueConstraint,
    Index
)

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database.connection import Base


# ==========================================
# RESUME MATCHING TABLE
# ==========================================

class ResumeMatch(Base):

    __tablename__ = "resume_matches"

    id = Column(Integer, primary_key=True, index=True)

    # ======================================
    # JOB AND RESUME REFERENCES
    # ======================================

    job_id = Column(
        Integer,
        ForeignKey("job_descriptions.id", ondelete="CASCADE"),
        nullable=False
    )

    resume_id = Column(
        Integer,
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False
    )

    # ======================================
    # OVERALL MATCHING SCORE
    # ======================================

    overall_score = Column(Float, nullable=False)

    # ======================================
    # INDIVIDUAL MATCHING SCORES
    # ======================================

    required_skills_score = Column(Float, nullable=True)

    preferred_skills_score = Column(Float, nullable=True)

    experience_score = Column(Float, nullable=True)

    semantic_score = Column(Float, nullable=True)

    education_score = Column(Float, nullable=True)

    # ======================================
    # SKILL MATCHING RESULTS
    # ======================================

    matched_required_skills = Column(JSONB, nullable=True)

    missing_required_skills = Column(JSONB, nullable=True)

    matched_preferred_skills = Column(JSONB, nullable=True)

    missing_preferred_skills = Column(JSONB, nullable=True)

    # ======================================
    # EXPERIENCE ANALYSIS
    # ======================================

    experience_analysis = Column(JSONB, nullable=True)

    # ======================================
    # EDUCATION ANALYSIS
    # ======================================

    education_analysis = Column(JSONB, nullable=True)

    # ======================================
    # SEMANTIC ANALYSIS
    # ======================================

    semantic_analysis = Column(JSONB, nullable=True)

    # ======================================
    # SCORE BREAKDOWN
    # ======================================

    score_breakdown = Column(JSONB, nullable=True)

    # ======================================
    # AI-GENERATED EXPLANATION
    # ======================================

    ai_explanation = Column(Text, nullable=True)

    # ======================================
    # TIMESTAMP
    # ======================================

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # ======================================
    # DATABASE RELATIONSHIPS
    # ======================================

    job = relationship("JobDescription")

    resume = relationship("Resume")

    # ======================================
    # CONSTRAINTS AND INDEXES
    # ======================================

    __table_args__ = (

        UniqueConstraint(
            "job_id",
            "resume_id",
            name="unique_job_resume_match"
        ),

        Index(
            "idx_resume_match_job",
            "job_id"
        ),

        Index(
            "idx_resume_match_score",
            "overall_score"
        )
    )