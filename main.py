from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal, engine, get_db
import models, crud, schemas
from datetime import datetime, timedelta, timezone
import pandas as pd
from models import SensorReading, SensorSTSI 
from models import Sensor 
from pydantic import BaseModel
from typing import List
from crud import get_sensor_readings
from crud import get_sensor_readings
import numpy as np
from scipy.stats import ttest_ind

models.Base.metadata.create_all(bind=engine)
app = FastAPI()


class SensorCreate(BaseModel):
    name: str

@app.post("/sensors/")
def create_sensor(sensor: SensorCreate, db: Session = Depends(get_db)):
    new_sensor = Sensor(name=sensor.name)
    db.add(new_sensor)
    db.commit()
    db.refresh(new_sensor)
    return {
        "sensor_id": new_sensor.id,
        "name": new_sensor.name,
        "message": "Sensor created successfully"
    }


@app.post("/sensors/{sensor_id}/data")
def add_sensor_data(sensor_id: int, readings: list[schemas.ReadingCreate], db: Session = Depends(get_db)):
    for reading in readings:
        if reading.value < -50 or reading.value > 100:
            raise HTTPException(status_code=400, detail="Value out of range")

    readings_sorted = sorted(readings, key=lambda x: x.timestamp)

    for i in range(1, len(readings_sorted)):
        if readings_sorted[i].timestamp <= readings_sorted[i - 1].timestamp:
            raise HTTPException(status_code=400, detail="Timestamps not in order")

    stored_readings = []

    for reading in readings_sorted:
        stored = crud.create_sensor_reading(db, sensor_id, reading)
        stored_readings.append(stored)

    return stored_readings

@app.get("/sensors/{sensor_id}/trend/moving-average", response_model=schemas.MovingAverageResponse)
def get_moving_average(sensor_id: int, window: int = 10, db: Session = Depends(get_db)):
    average = crud.get_moving_average(db, sensor_id, window)

    return {
        "sensor_id": sensor_id,
        "window": window,
        "moving_average": average
    }

@app.get("/sensors/{sensor_id}/trend/predict", response_model=schemas.PredictionResponse)
def get_prediction(sensor_id: int, days: int = 3, db: Session = Depends(get_db)):
    predictions = crud.get_prediction(db, sensor_id, days)

    return {
        "sensor_id": sensor_id,
        "predict_days": days,
        "predicted_values": predictions
    }

@app.get("/sensors/{sensor_id}/anomalies/statistical", response_model=schemas.AnomalyResponse)
def get_anomalies(sensor_id: int, db: Session = Depends(get_db)):
    anomalies = crud.get_anomalies(db, sensor_id)

    return {
        "sensor_id": sensor_id,
        "anomalies": anomalies
    }

@app.get("/sensors/{sensor_id}/quality-report", response_model=schemas.QualityReportResponse)
def quality_report(sensor_id: int, db: Session = Depends(get_db)):
    missing, out_of_range = crud.get_quality_report(db, sensor_id)

    return {
        "sensor_id": sensor_id,
        "expected_interval_minutes": 5,
        "missing_percentage": missing,
        "out_of_range_percentage": out_of_range
    }

@app.get("/sensor/{id}/stsi")
def get_stsi_trend(id: int, start: str, end: str):
    session = SessionLocal()
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format.")
    

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    readings = session.query(SensorReading).filter(
        SensorReading.sensor_id == id,
        SensorReading.timestamp >= cutoff
    ).order_by(SensorReading.timestamp).all()

    if not readings:
        raise HTTPException(status_code=404, detail="No readings found")

    df = pd.DataFrame([(r.timestamp, r.value) for r in readings], columns=["timestamp", "value"])
    df.set_index("timestamp", inplace=True)
    
    hourly = df.resample("1h").mean().interpolate()

    rolling_std = hourly.rolling("3h").std().fillna(0)
    normalized_std = (rolling_std - rolling_std.min()) / (rolling_std.max() - rolling_std.min() + 1e-8)
    stsi = 1 - normalized_std  


    daily_stsi = stsi.resample("1D").mean()
    daily_stsi["sensor_id"] = id
    daily_stsi = daily_stsi.reset_index().rename(columns={"timestamp": "date", "value": "stsi"})


    for i, row in daily_stsi.iterrows():
        row_date = row["date"].date()
        if start_date <= row_date <= end_date:
            stsi_entry = SensorSTSI(sensor_id=row["sensor_id"], date=row_date, stsi=row["stsi"])
            session.merge(stsi_entry)
    session.commit()

    result = [
        {
            "date": row["date"].strftime("%Y-%m-%d"),
            "average_stsi": round(row["stsi"], 2)
        }
        for _, row in daily_stsi.iterrows()
        if start_date <= row["date"].date() <= end_date
    ]

    return {
        "sensor_id": id,
        "stsi_trend": result,
        "metadata": {
            "window_size": "1 hour",
            "description": "Daily average Sensor Trend Stability Index (STSI) from rolling std dev of hourly values. Higher = more stable."
        }
    }


@app.post("/sensors/{id}/metrics", response_model=schemas.HealthMetricOut)
def add_health_metric(id: int, metric: schemas.HealthMetricCreate, db: Session = Depends(get_db)):
    sensor = db.get(models.Sensor, id)
    if not sensor:
        raise HTTPException(404, "Sensor not found")
    hm = models.SensorHealthMetric(sensor_id=id, **metric.dict())
    db.add(hm)
    db.commit()
    db.refresh(hm)
    return hm

@app.get("/sensors/{id}/metrics", response_model=List[schemas.HealthMetricOut])
def list_health_metrics(id: int, db: Session = Depends(get_db)):
    return db.query(models.SensorHealthMetric).filter_by(sensor_id=id).all()

@app.put("/metrics/{mid}", response_model=schemas.HealthMetricOut)
def update_health_metric(mid: int, updates: schemas.HealthMetricCreate, db: Session = Depends(get_db)):
    hm = db.get(models.SensorHealthMetric, mid)
    if not hm:
        raise HTTPException(404, "Metric not found")
    for k, v in updates.dict(exclude_unset=True).items():
        setattr(hm, k, v)
    db.commit()
    db.refresh(hm)
    return hm

@app.delete("/metrics/{mid}")
def delete_health_metric(mid: int, db: Session = Depends(get_db)):
    hm = db.get(models.SensorHealthMetric, mid)
    if not hm:
        raise HTTPException(404, "Metric not found")
    db.delete(hm)
    db.commit()
    return {"detail": "Deleted"}

class DriftResult(BaseModel):
    sensor_id: int
    drift_detected: bool
    recent_mean: float
    previous_mean: float
    t_statistic: float
    p_value: float

@app.get("/sensor/{sensor_id}/drift", response_model=DriftResult)
def detect_drift(sensor_id: int, days: int = 6, window: int = 3, db: Session = Depends(get_db)):
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)
    recent_window_start = end_date - timedelta(days=window)
    previous_window_start = start_date
    previous_window_end = recent_window_start

    recent_data = get_sensor_readings(sensor_id, recent_window_start, end_date, db)
    previous_data = get_sensor_readings(sensor_id, previous_window_start, previous_window_end, db)

    if not recent_data or not previous_data:
        raise HTTPException(status_code=404, detail="Not enough data for statistical test.")

    recent_arr = np.array(recent_data)
    previous_arr = np.array(previous_data)

    mean_recent = float(np.mean(recent_arr))
    mean_previous = float(np.mean(previous_arr))

    t_stat, p_value = ttest_ind(previous_arr, recent_arr, equal_var=False, nan_policy='omit')
    drift = bool(p_value < 0.05)

    return DriftResult(
        sensor_id=sensor_id,
        drift_detected=drift,
        recent_mean=mean_recent,
        previous_mean=mean_previous,
        t_statistic=float(t_stat),
        p_value=float(p_value)
    )




