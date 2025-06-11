from sqlalchemy import Column, Integer, Float, String, ForeignKey, Date, DateTime, Enum, PrimaryKeyConstraint, func
from sqlalchemy.orm import relationship
from database import Base 
import enum

class SensorStatus(str, enum.Enum):
    active = "active"
    offline = "offline"
    maintenance = "maintenance"

class Sensor(Base):
    __tablename__ = "sensors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    location = Column(String)
    type = Column(String)
    status = Column(Enum(SensorStatus), default=SensorStatus.active)
    install_date = Column(Date)
    last_maintenance_date = Column(Date)

    readings = relationship("SensorReading", back_populates="sensor")
    health_metrics = relationship("SensorHealthMetric", back_populates="sensor", cascade="all, delete")

class SensorReading(Base):
    __tablename__ = "sensor_readings"
    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=False)

    sensor = relationship("Sensor", back_populates="readings")

class SensorSTSI(Base):
    __tablename__ = "sensor_stsi"
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=False)
    date = Column(Date, nullable=False)
    stsi = Column(Float, nullable=False)

    __table_args__ = (PrimaryKeyConstraint('sensor_id', 'date'),)

class SensorHealthMetric(Base):
    __tablename__ = "sensor_health_metrics"
    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=False)
    uptime_percentage = Column(Float, nullable=True)
    mtbf = Column(Float, nullable=True)
    last_anomaly_detected = Column(DateTime, nullable=True)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    sensor = relationship("Sensor", back_populates="health_metrics")
