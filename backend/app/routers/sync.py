from fastapi import APIRouter, BackgroundTasks, HTTPException
import os
import sys
import subprocess
import requests
from app.ml_service import ml_service

router = APIRouter()

# Constants
SHEET_URL = "https://docs.google.com/spreadsheets/d/1myYlsoOTpXPPN9mKfZkEDrX_H5mlAiIPbM0HxA6L0OY/export?format=csv"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ML_DATA_DIR = os.path.join(BASE_DIR, 'ml_model', 'data')
ML_SRC_DIR = os.path.join(BASE_DIR, 'ml_model', 'src')
DATASET_PATH = os.path.join(ML_DATA_DIR, 'dataset.csv')

def run_sync_pipeline():
    print("Starting ML Synchronization Pipeline...")
    
    # 1. Run fetch_expanded_dataset.py
    try:
        print("Fetching latest data from Open-Meteo...")
        fetch_script = os.path.join(BASE_DIR, 'scripts', 'fetch_expanded_dataset.py')
        subprocess.run([sys.executable, fetch_script], cwd=BASE_DIR, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running fetch_expanded_dataset.py: {e}")
        return False
        
    # 2. Run production train_models.py
    try:
        print("Training models with physical PM2.5 targets...")
        train_script = os.path.join(ML_SRC_DIR, "train_models.py")
        subprocess.run([sys.executable, train_script], cwd=BASE_DIR, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running train_models.py: {e}")
        return False
        
    # 4. Hot-reload the models in the ML service
    try:
        print("Hot-reloading models in ML Service...")
        ml_service._load_models()
    except Exception as e:
        print(f"Error reloading models: {e}")
        return False
        
    print("ML Synchronization Pipeline completed successfully.")
    return True

@router.post("/sync")
def trigger_sync(background_tasks: BackgroundTasks):
    """
    Manually trigger the 24-hour sync pipeline for the Live Dataset.
    """
    background_tasks.add_task(run_sync_pipeline)
    return {"message": "Synchronization pipeline triggered in the background. Models will be hot-reloaded upon completion."}
