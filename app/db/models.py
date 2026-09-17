
# ORM models. Mirrors app/db/schema.sql — if you change one, change the other.

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.database import Base

EMBEDDING_DIM = 1024  # BAAI/bge-m3 output dimension


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    source_label = Column(String, nullable=True)
    storage_path = Column(String, nullable=True)  # Supabase Storage path to the raw file
    status = Column(String, nullable=False, default="pending")  # pending | processing | ready | failed
    failure_reason = Column(Text, nullable=True)
    uploaded_by = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk"),)

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=False)

    document = relationship("Document", back_populates="chunks")


class AppUser(Base):
    __tablename__ = "app_users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    role = Column(String, nullable=False, default="staff")  # staff | admin
    created_at = Column(DateTime, default=datetime.utcnow)


class EvalResult(Base):
    __tablename__ = "eval_results"

    id = Column(Integer, primary_key=True)
    question = Column(Text, nullable=False)
    expected_answer = Column(Text, nullable=True)
    model_name = Column(String, nullable=False)
    model_answer = Column(Text, nullable=True)
    accuracy_score = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    cost_usd = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)