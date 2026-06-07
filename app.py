from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import logging
import os
from datetime import datetime
from typing import List
from pathlib import Path
from price_compare import PriceComparator
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Book Price Comparison API",
    description="WebSocket-based book price comparison across retailers",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

price_comparator = PriceComparator()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Disconnected. Remaining: {len(self.active_connections)}")
    
    async def send_to_client(self, websocket: WebSocket, message: dict):
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Send error: {e}")
    
    def get_connection_count(self) -> int:
        return len(self.active_connections)

manager = ConnectionManager()

@app.get("/")
async def root():
    return FileResponse("static/index.html", media_type="text/html")

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_connections": manager.get_connection_count()
    }

@app.get("/api/competitors")
async def get_competitors():
    competitors = price_comparator.get_competitors()
    return {
        "status": "success",
        "competitors": competitors,
        "count": len(competitors),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/locations")
async def get_locations():
    locations = [
        {"code": "US", "name": "United States", "currency": "USD", "flag": "🇺🇸"},
        {"code": "UK", "name": "United Kingdom", "currency": "GBP", "flag": "🇬🇧"},
        {"code": "CA", "name": "Canada", "currency": "CAD", "flag": "🇨🇦"},
        {"code": "AU", "name": "Australia", "currency": "AUD", "flag": "🇦🇺"},
        {"code": "IN", "name": "India", "currency": "INR", "flag": "🇮🇳"},
        {"code": "EU", "name": "Europe", "currency": "EUR", "flag": "🇪🇺"},
        {"code": "JP", "name": "Japan", "currency": "JPY", "flag": "🇯🇵"},
        {"code": "BR", "name": "Brazil", "currency": "BRL", "flag": "🇧🇷"},
    ]
    return {
        "status": "success",
        "locations": locations,
        "count": len(locations),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/compare")
async def compare_prices(product_name: str, location: str = "US"):
    if not product_name:
        raise HTTPException(status_code=400, detail="product_name is required")
    
    try:
        result = await price_comparator.compare_prices(product_name, location)
        return {
            "status": "success",
            "product": product_name,
            "location": location,
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    try:
        welcome_msg = {
            "type": "connection",
            "status": "connected",
            "message": "Welcome to Book Price Comparison Server",
            "timestamp": datetime.now().isoformat()
        }
        await manager.send_to_client(websocket, welcome_msg)
        
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            logger.info(f"WebSocket message: {msg_type}")
            
            if msg_type == "ping":
                response = {
                    "type": "pong",
                    "echo": data.get("data"),
                    "timestamp": datetime.now().isoformat()
                }
                await manager.send_to_client(websocket, response)
            
            elif msg_type == "compare_price":
                product_name = data.get("product_name")
                location = data.get("location", "US")
                
                if not product_name:
                    error_msg = {
                        "type": "error",
                        "message": "product_name is required",
                        "timestamp": datetime.now().isoformat()
                    }
                    await manager.send_to_client(websocket, error_msg)
                else:
                    logger.info(f"Comparing prices for '{product_name}' in {location}")
                    comparison_result = await price_comparator.compare_prices(
                        product_name,
                        location
                    )
                    
                    response = {
                        "type": "price_comparison",
                        "product": product_name,
                        "location": location,
                        "data": comparison_result,
                        "timestamp": datetime.now().isoformat()
                    }
                    await manager.send_to_client(websocket, response)
            
            elif msg_type == "get_competitors":
                competitors = price_comparator.get_competitors()
                response = {
                    "type": "competitors_list",
                    "competitors": competitors,
                    "timestamp": datetime.now().isoformat()
                }
                await manager.send_to_client(websocket, response)
            
            elif msg_type == "get_stats":
                response = {
                    "type": "stats",
                    "active_connections": manager.get_connection_count(),
                    "timestamp": datetime.now().isoformat()
                }
                await manager.send_to_client(websocket, response)
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    
    finally:
        manager.disconnect(websocket)

Path("static").mkdir(exist_ok=True)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
