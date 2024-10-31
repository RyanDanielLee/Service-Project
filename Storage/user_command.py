from base import Base
from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime

class UserCommand(Base):
    __tablename__ = 'user_command'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(36), nullable=False)
    target_device = Column(String(255), nullable=False)
    target_temperature = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)  
    trace_id = Column(String(36), nullable=True)
    date_created = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'target_device': self.target_device,
            'target_temperature': self.target_temperature,
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,  
            'trace_id': self.trace_id,
            'date_created': self.date_created.isoformat() if isinstance(self.date_created, datetime) else self.date_created
        }
