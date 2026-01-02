from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class LogEntry(Base):
    __tablename__ = "log_entries"
    id       = Column(Integer, primary_key=True, index=True)
    user_id  = Column(String, index=True)
    issue    = Column(String, index=True)
    minutes  = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)


class AssignmentPointer(Base):
    __tablename__ = "assignment_pointer"
    id         = Column(Integer, primary_key=True, index=True)
    last_index = Column(Integer, default=-1)

class TicketAssignment(Base):
    __tablename__ = "ticket_assignments"
    id           = Column(Integer, primary_key=True, index=True)
    ticket_id    = Column(String, unique=True, index=True)
    engineer_id  = Column(String, index=True)
    assigned_at  = Column(DateTime, default=datetime.utcnow)
    resolved_at  = Column(DateTime, nullable=True)