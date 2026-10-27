"""Simple, explainable severity estimate. This is a heuristic for a prototype,
NOT a calibrated engineering measurement."""


def estimate_severity(confidence, area_ratio, vibration_g=None):
    """
    confidence : 0..1 from YOLO
    area_ratio : bounding-box area / image area (bigger pothole in frame = bigger/closer)
    vibration_g: peak acceleration from IMU if available
    Returns (label, score)
    """
    size_score = min(max(area_ratio, 0) / 0.10, 1.0)      # 10% of frame = max
    if vibration_g is not None:
        vib_score = min(max(vibration_g, 0) / 2.0, 1.0)   # 2 g = max
        score = 0.3 * confidence + 0.4 * size_score + 0.3 * vib_score
    else:
        score = 0.4 * confidence + 0.6 * size_score
    if score < 0.40:
        label = "Low"
    elif score < 0.70:
        label = "Medium"
    else:
        label = "High"
    return label, round(score, 3)
