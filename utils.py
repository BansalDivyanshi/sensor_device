from statistics import mean, stdev
from datetime import timedelta
from sklearn.linear_model import LinearRegression
import numpy as np

def compute_moving_average(values, window):
    result = []

    for i in range(len(values) - window + 1):
        window_values = values[i:i + window]
        avg = round(mean(window_values), 2)
        result.append(avg)

    return result

def compute_linear_regression(timestamps, values, predict_days):
    if len(timestamps) < 2:
        return []

    X = np.array([(ts - timestamps[0]).total_seconds() / 86400 for ts in timestamps]).reshape(-1, 1)
    y = np.array(values)
    model = LinearRegression().fit(X, y)


    slope = model.coef_[0]
    if abs(slope) > 10:
        slope = 0
        model.coef_ = np.array([0])
        model.intercept_ = np.mean(values)

    X_pred = np.array([X[-1][0] + i for i in range(1, predict_days + 1)]).reshape(-1, 1)
    predictions = model.predict(X_pred)

    return [
        {"date": (timestamps[-1] + timedelta(days=i)).date().isoformat(), "value": round(val, 2)}
        for i, val in enumerate(predictions, 1)
    ]

def detect_anomalies(values, timestamps):
    if len(values) < 2:
        return []

    a = mean(values)
    b = stdev(values)

    anomalies = []

    for val, ts in zip(values, timestamps):
        if abs(val - a) > 2 * b:
            anomalies.append({
                "timestamp": ts.isoformat(),
                "value": val,
                "type": "2std"
            })

    return anomalies

def calculate_quality(timestamps, values, expected_interval_minutes=5):
    if not timestamps:
        return 0.0, 0.0

    timestamps = sorted(timestamps)

    total_seconds = (timestamps[-1] - timestamps[0]).total_seconds()
    expected_total = int(total_seconds // (expected_interval_minutes * 60))

    missing = expected_total - len(timestamps) + 1
    missing_pct = 100 * missing / expected_total if expected_total else 0

    outliers = [
        v for v in values
        if v < -50 or v > 100
    ]

    outlier_pct = 100 * len(outliers) / len(values) if values else 0

    return round(missing_pct, 2), round(outlier_pct, 2)
