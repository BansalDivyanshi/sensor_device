from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class SensorBase(BaseModel):
    name: str

class SensorCreate(SensorBase):
    pass

class Sensor(SensorBase):
    id: int
    class Config:
        orm_mode = True

class ReadingBase(BaseModel):
    timestamp: datetime
    value: float
    unit: str

class ReadingCreate(ReadingBase):
    pass

class Reading(ReadingBase):
    id: int
    sensor_id: int
    class Config:
        orm_mode = True

class MovingAverageResponse(BaseModel):
    sensor_id: int
    window: int
    moving_average: List[float]

class PredictionResponse(BaseModel):
    sensor_id: int
    predict_days: int
    predicted_values: List[dict]

class AnomalyResponse(BaseModel):
    sensor_id: int
    anomalies: List[dict]

class QualityReportResponse(BaseModel):
    sensor_id: int
    expected_interval_minutes: int
    missing_percentage: float
    out_of_range_percentage: float

class HealthMetricCreate(BaseModel):
    uptime_percentage: Optional[float]
    mtbf: Optional[float]
    last_anomaly_detected: Optional[datetime]

class HealthMetricOut(HealthMetricCreate):
    id: int
    sensor_id: int

    class Config:
        orm_mode = True
