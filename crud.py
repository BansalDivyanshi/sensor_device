from sqlalchemy.orm import Session
from models import SensorReading
from schemas import ReadingCreate
from utils import (
    compute_moving_average,
    compute_linear_regression,
    detect_anomalies,
    calculate_quality
)
from datetime import datetime, timedelta

def create_sensor_reading(db: Session, sensor_id: int, reading: ReadingCreate):
    db_reading = SensorReading(
        sensor_id=sensor_id,
        timestamp=reading.timestamp,
        value=reading.value,
        unit=reading.unit
    )

    db.add(db_reading)
    db.commit()
    db.refresh(db_reading)

    return db_reading

def get_last_readings(db: Session, sensor_id: int, limit: int):
    readings = db.query(SensorReading)\
                 .filter(SensorReading.sensor_id == sensor_id)\
                 .order_by(SensorReading.timestamp.desc())\
                 .limit(limit)\
                 .all()

    return readings[::-1]

def get_readings_past_days(db: Session, sensor_id: int, days: int):
    cutoff = datetime.utcnow() - timedelta(days=days)

    readings = db.query(SensorReading)\
                 .filter(
                     SensorReading.sensor_id == sensor_id,
                     SensorReading.timestamp >= cutoff
                 )\
                 .order_by(SensorReading.timestamp)\
                 .all()

    return readings

def get_moving_average(db: Session, sensor_id: int, window: int):
    readings = get_last_readings(db, sensor_id, window + 10)
    values = [reading.value for reading in readings]

    return compute_moving_average(values, window)

def get_prediction(db: Session, sensor_id: int, days: int):
    readings = get_readings_past_days(db, sensor_id, 7)
    timestamps = [reading.timestamp for reading in readings]
    values = [reading.value for reading in readings]

    return compute_linear_regression(timestamps, values, days)

def get_anomalies(db: Session, sensor_id: int):
    readings = get_readings_past_days(db, sensor_id, 30)
    timestamps = [r.timestamp for r in readings]
    values = [r.value for r in readings]

    return detect_anomalies(values, timestamps)

def get_quality_report(db: Session, sensor_id: int):
    readings = get_readings_past_days(db, sensor_id, 7)
    timestamps = [r.timestamp for r in readings]
    values = [r.value for r in readings]

    return calculate_quality(timestamps, values)
    
