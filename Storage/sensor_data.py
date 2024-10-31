from base import Base
from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime

class SensorData(Base):
    __tablename__ = 'sensor_data'
    
    id = Column(Integer, primary_key=True)
    sensor_id = Column(String(36), nullable=False)
    temperature = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)  
    location = Column(String(255), nullable=True)
    trace_id = Column(String(36), nullable=True)
    date_created = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'sensor_id': self.sensor_id,
            'temperature': self.temperature,
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,  
            'location': self.location,
            'trace_id': self.trace_id,
            'date_created': self.date_created.isoformat() if isinstance(self.date_created, datetime) else self.date_created
        }
