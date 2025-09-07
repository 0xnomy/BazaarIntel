from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from routers import trends, scrape, seo, report as report_router
from routers.agent import router as agent_router
from fastapi.responses import HTMLResponse

app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.include_router(trends.router)
app.include_router(scrape.router)
app.include_router(seo.router)
app.include_router(agent_router)
app.include_router(report_router.router)

@app.get("/")
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/seo")
def seo_page(request: Request):
    return templates.TemplateResponse("seo.html", {"request": request})

@app.get("/report", response_class=HTMLResponse)
def report_page(request: Request):
    return templates.TemplateResponse("report.html", {"request": request})
