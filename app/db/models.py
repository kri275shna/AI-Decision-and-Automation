from sqlalchemy import Column, Integer, String, Text, Float, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
import datetime
from .database import Base

class RequestModel(Base):
    __tablename__ = "requests"
    id = Column(String(50), primary_key=True, index=True)
    input_text = Column(Text, nullable=False)
    input_metadata = Column(JSON, nullable=True)
    status = Column(String(50), default="INIT")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    ai_output = relationship("AIOutputModel", back_populates="request", uselist=False)
    workflow = relationship("WorkflowModel", back_populates="request", uselist=False)
    audit_logs = relationship("AuditLogModel", back_populates="request")

class AIOutputModel(Base):
    __tablename__ = "ai_outputs"
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(50), ForeignKey("requests.id"))
    retrieved_context = Column(JSON)
    raw_output = Column(JSON)
    decision = Column(String(50))
    confidence = Column(Float)
    uncertainty = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    request = relationship("RequestModel", back_populates="ai_output")

class WorkflowModel(Base):
    __tablename__ = "workflows"
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(50), ForeignKey("requests.id"))
    state = Column(String(50), default="INIT")
    retry_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    request = relationship("RequestModel", back_populates="workflow")

class RuleModel(Base):
    __tablename__ = "rules"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True)
    condition = Column(JSON)
    action = Column(String(50))
    is_active = Column(Boolean, default=True)

class AuditLogModel(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(50), ForeignKey("requests.id"))
    old_state = Column(String(50))
    new_state = Column(String(50))
    reason = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    request = relationship("RequestModel", back_populates="audit_logs")

class IdempotencyKeyModel(Base):
    __tablename__ = "idempotency_keys"
    idempotency_key = Column(String(100), primary_key=True, index=True)
    request_id = Column(String(50), nullable=False)
    response_body = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
