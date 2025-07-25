from fastapi import APIRouter, BackgroundTasks, Request
import subprocess
import os
import json

router = APIRouter()
SCRAPE_STATUS_FILE = "scrape_status.json"

def run_scraper(brand, count=50):
    proc = subprocess.Popen(["python", "scrapper.py", "--brand", brand, "--count", str(count)])
    proc.wait()
    # Only write finished status if not stopped
    if os.path.exists(SCRAPE_STATUS_FILE):
        try:
            with open(SCRAPE_STATUS_FILE) as f:
                status = json.load(f)
            if status.get("stopped"):
                return
        except Exception:
            pass
    with open(SCRAPE_STATUS_FILE, "w") as f:
        json.dump({"brand": brand, "finished": True}, f)

@router.post("/api/scrape/{brand}")
def trigger_scrape(brand: str, background_tasks: BackgroundTasks, request: Request):
    # Clear status file at the start
    if os.path.exists(SCRAPE_STATUS_FILE):
        os.remove(SCRAPE_STATUS_FILE)
    count = int(request.query_params.get('count', 50))
    background_tasks.add_task(run_scraper, brand, count)
    return {"status": "started", "brand": brand}

@router.get("/api/scrape/status")
def scrape_status():
    if os.path.exists(SCRAPE_STATUS_FILE):
        with open(SCRAPE_STATUS_FILE) as f:
            return json.load(f)
    return {"status": "idle"}

@router.post("/api/scrape/clear-status")
def clear_scrape_status():
    if os.path.exists(SCRAPE_STATUS_FILE):
        os.remove(SCRAPE_STATUS_FILE)
    return {"status": "cleared"} 