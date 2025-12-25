import asyncio
from fastapi import FastAPI, WebSocket, Request
from fastapi.templating import Jinja2Templates
from scraper import VPSScraper
import database  # Import the new module

app = FastAPI()
templates = Jinja2Templates(directory="templates")

scraper = VPSScraper()

# Global variable to store SQL data
cw_reference_map = {}

@app.on_event("startup")
async def startup_event():
    global cw_reference_map
    
    # 1. Load SQL Data once on startup
    cw_reference_map = database.get_cw_reference_data()
    
    # 2. Start the Scraper
    await scraper.start_browser(total_tabs=11)
    asyncio.create_task(scraper.scrape_loop())

@app.on_event("shutdown")
async def shutdown_event():
    await scraper.stop()

@app.get("/")
async def get_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Get fresh data from scraper
            live_data = scraper.data_store
            
            # MERGE LOGIC: Combine Live Data + SQL Data
            merged_data = []
            if live_data:
                for item in live_data:
                    # Create a shallow copy so we don't modify the original scraper list repeatedly
                    new_item = item.copy()
                    
                    # Lookup ExercisePrice from SQL map using the Symbol
                    # Default to 0 if not found in DB
                    symbol = new_item.get('symbol', '')
                    new_item['exercise_price'] = cw_reference_map.get(symbol, 0.0)
                    
                    merged_data.append(new_item)
            
            # Send the merged result
            await websocket.send_json(merged_data)
            
            await asyncio.sleep(1) 
    except Exception:
        print("Client disconnected")