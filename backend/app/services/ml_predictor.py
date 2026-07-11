import os
import pickle
import numpy as np
import logging
from sqlalchemy.orm import Session
from sklearn.ensemble import RandomForestRegressor

from app.models.schedule import Faculty
from app.models.leave import LeaveRequest, SwapRequest

logger = logging.getLogger("ml_predictor")

MODEL_PATH = "burnout_model.pkl"
_cached_model = None

def get_faculty_features(faculty: Faculty, db: Session) -> np.ndarray:
    """
    Extracts features for the faculty member to predict burnout risk:
    [workload_ratio, approved_leaves_count, swaps_requested_count]
    """
    # Feature 1: Workload ratio
    workload_ratio = faculty.current_workload / max(1, faculty.max_hours_per_week)
    
    # Feature 2: Leave requests in the last 30 days
    leaves_count = db.query(LeaveRequest).filter(
        LeaveRequest.faculty_id == faculty.id,
        LeaveRequest.status == "APPROVED"
    ).count()
    
    # Feature 3: Swaps requested in the last 30 days
    swaps_count = db.query(SwapRequest).filter(
        SwapRequest.sender_faculty_id == faculty.id
    ).count()
    
    return np.array([workload_ratio, leaves_count, swaps_count], dtype=float)

def train_burnout_model():
    """
    Generates synthetic training dataset representing faculty fatigue patterns
    and fits a RandomForestRegressor model.
    """
    global _cached_model
    
    logger.info("Training lightweight burnout prediction model...")
    # Features: [workload_ratio, leaves_count, swaps_count]
    # Label: Burnout index (0.0 to 1.0)
    X = np.array([
        # High workload, high leaves, high swaps -> High burnout
        [0.9, 4, 5],
        [0.85, 3, 4],
        [0.95, 2, 3],
        [1.0, 5, 2],
        
        # Low workload, low leaves, low swaps -> Low burnout
        [0.3, 0, 0],
        [0.4, 1, 1],
        [0.5, 0, 1],
        [0.2, 0, 0],
        
        # Moderate workload, moderate leaves/swaps -> Medium burnout
        [0.7, 2, 2],
        [0.6, 1, 2],
        [0.75, 2, 1],
        [0.65, 3, 1]
    ], dtype=float)
    
    y = np.array([
        0.90, 0.82, 0.78, 0.85, # High
        0.05, 0.15, 0.20, 0.02, # Low
        0.50, 0.42, 0.48, 0.55  # Medium
    ], dtype=float)
    
    model = RandomForestRegressor(n_estimators=10, random_state=42)
    model.fit(X, y)
    
    try:
        with open(MODEL_PATH, "wb") as f:
            pickle.dump(model, f)
    except Exception as e:
        logger.warning(f"Could not persist ML model to disk: {e}")
        
    _cached_model = model
    return model

def get_model():
    global _cached_model
    if _cached_model is not None:
        return _cached_model
        
    if os.path.exists(MODEL_PATH):
        try:
            with open(MODEL_PATH, "rb") as f:
                _cached_model = pickle.load(f)
                return _cached_model
        except Exception as e:
            logger.warning(f"Error loading saved ML model: {e}")
            
    return train_burnout_model()

def predict_burnout_risk(faculty: Faculty, db: Session) -> float:
    """
    Feeds faculty features into the scikit-learn model and returns a burnout risk prediction (0.0 to 1.0).
    """
    try:
        model = get_model()
        features = get_faculty_features(faculty, db)
        # Reshape to 2D array for sklearn
        prediction = model.predict(features.reshape(1, -1))[0]
        # Bound between 0.0 and 1.0
        return float(np.clip(prediction, 0.0, 1.0))
    except Exception as e:
        logger.error(f"Failed to predict burnout risk: {e}")
        # Fallback to simple heuristic if model fails
        workload_ratio = faculty.current_workload / max(1, faculty.max_hours_per_week)
        return float(np.clip(workload_ratio * 0.7, 0.0, 1.0))
