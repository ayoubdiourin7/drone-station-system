# server.py - WebSocket Server for Drone Communication
import asyncio
import json
import time
import uuid
from typing import Dict, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
# local modules
#from modules.mask_generator import generate_mask
#from modules.image_reconstructor import reconstruct_image
#rom modules.database_manager import save_image, get_images

app = FastAPI(title="Drone Communication Server")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DroneConnection:
    def __init__(self, websocket: WebSocket, drone_id: str):
        self.websocket = websocket
        self.drone_id = drone_id
        self.is_connected = False
        self.last_telemetry = None

# Store active drone connections
active_drones: Dict[str, DroneConnection] = {}
active_ui_clients: Set[WebSocket] = set()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "active_drones": len(active_drones),
        "server_time": time.strftime("%Y-%m-%d %H:%M:%S")
    }

async def broadcast_drone_list():
    """Broadcast updated drone list to all UI clients"""
    # Only send available (not connected) drones
    available_drones = [
        drone_id for drone_id, conn in active_drones.items() 
        if not conn.is_connected
    ]
    
    message = {
        "type": "drone_list",
        "drones": available_drones,
        "timestamp": time.time()
    }
    await broadcast_to_ui_clients(message)

@app.websocket("/ws/drone/{drone_id}")
async def websocket_drone_endpoint(websocket: WebSocket, drone_id: str):
    """Handle WebSocket connections from drones"""
    await websocket.accept()
    
    # Generate a unique connection ID if not provided
    if not drone_id or drone_id == "new":
        drone_id = f"drone-{str(uuid.uuid4())[:8]}"
    
    # Register the drone
    drone_connection = DroneConnection(websocket, drone_id)
    active_drones[drone_id] = drone_connection
    print(f"[SERVER] ✅ Drone available: {drone_id}")
    
    # Broadcast updated drone list when a new drone becomes available
    await broadcast_drone_list()
    
    try:
        # Send welcome message to the drone
        await websocket.send_text(json.dumps({
            "type": "connection_confirmed",
            "drone_id": drone_id,
            "message": "Connection established with server",
            "timestamp": time.time()
        }))
        
        # Main communication loop
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                print(f"[SERVER] 📥 Received from {drone_id}: {message}")
                
                if message["type"] == "connection_approved":
                    drone_connection.is_connected = True
                    # Notify UI clients of successful connection
                    await broadcast_to_ui_clients({
                        "type": "connection_success",
                        "drone_id": drone_id,
                        "timestamp": time.time()
                    })
                
                elif message["type"] == "disconnect_confirmed":
                    drone_connection.is_connected = False
                    drone_connection.last_telemetry = None
                    # Notify UI clients of disconnection
                    await broadcast_to_ui_clients({
                        "type": "drone_disconnected",
                        "drone_id": drone_id,
                        "timestamp": time.time()
                    })
                    # Broadcast updated available drone list
                    await broadcast_drone_list()
                
                elif message["type"] == "telemetry":
                    # Store last telemetry
                    drone_connection.last_telemetry = message
                    # Add drone_id and broadcast to UI
                    telemetry_data = {
                        "type": "telemetry",
                        "drone_id": drone_id,
                        **message
                    }
                    await broadcast_to_ui_clients(telemetry_data)
                    print(f"[SERVER] 📡 Telemetry from {drone_id}: Battery: {message.get('battery', 'N/A')}%, Signal: {message.get('signal_strength', 'N/A')}%")
                
            except json.JSONDecodeError:
                print(f"[SERVER] ⚠️ Received invalid JSON from {drone_id}")
    
    except WebSocketDisconnect:
        print(f"[SERVER] ❌ Drone disconnected: {drone_id}")
        if drone_id in active_drones:
            if active_drones[drone_id].is_connected:
                # Notify UI clients of disconnection
                await broadcast_to_ui_clients({
                    "type": "drone_disconnected",
                    "drone_id": drone_id,
                    "timestamp": time.time()
                })
            active_drones.pop(drone_id)
            await broadcast_drone_list()
    
    except Exception as e:
        print(f"[SERVER] ⚠️ Error in drone {drone_id} connection: {str(e)}")
        if drone_id in active_drones:
            if active_drones[drone_id].is_connected:
                await broadcast_to_ui_clients({
                    "type": "drone_disconnected",
                    "drone_id": drone_id,
                    "timestamp": time.time()
                })
            active_drones.pop(drone_id)
            await broadcast_drone_list()

@app.websocket("/ws/ui")
async def websocket_ui_endpoint(websocket: WebSocket):
    """Handle WebSocket connections from UI clients"""
    await websocket.accept()
    client_id = f"ui-{str(uuid.uuid4())[:8]}"
    print(f"[SERVER] ✅ UI client connected: {client_id}")
    
    active_ui_clients.add(websocket)
    
    try:
        # Send initial drone list
        await websocket.send_text(json.dumps({
            "type": "drone_list",
            "drones": [drone_id for drone_id, conn in active_drones.items() if not conn.is_connected],
            "timestamp": time.time()
        }))
        
        # Handle UI client messages
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                
                if message["type"] == "connect_drone":
                    drone_id = message["drone_id"]
                    if drone_id in active_drones and not active_drones[drone_id].is_connected:
                        # Forward connection request to drone
                        await active_drones[drone_id].websocket.send_text(json.dumps({
                            "type": "connect_request",
                            "timestamp": time.time()
                        }))
                
                elif message["type"] == "disconnect_drone":
                    drone_id = message["drone_id"]
                    if drone_id in active_drones and active_drones[drone_id].is_connected:
                        # Forward disconnection request to drone
                        await active_drones[drone_id].websocket.send_text(json.dumps({
                            "type": "disconnect_request",
                            "timestamp": time.time()
                        }))
            
            except json.JSONDecodeError:
                print(f"[SERVER] ⚠️ Received invalid JSON from UI client {client_id}")
            
    except WebSocketDisconnect:
        print(f"[SERVER] ❌ UI client disconnected: {client_id}")
    finally:
        active_ui_clients.remove(websocket)

async def broadcast_to_ui_clients(message: dict):
    """Broadcast message to all UI clients"""
    disconnected_clients = set()
    
    for client in active_ui_clients:
        try:
            await client.send_text(json.dumps(message))
        except WebSocketDisconnect:
            disconnected_clients.add(client)
    
    active_ui_clients.difference_update(disconnected_clients)

if __name__ == "__main__":
    import uvicorn
    print("[SERVER] 🚀 Starting Drone Communication Server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)