from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models, crud, schemas

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
