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
#from modules.database_manager import save_image, get_images

app = FastAPI(title="Drone Communication Server")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active drone connections
active_drones: Dict[str, WebSocket] = {}

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "active_drones": len(active_drones),
        "server_time": time.strftime("%Y-%m-%d %H:%M:%S")
    }

@app.websocket("/ws/drone/{drone_id}")
async def websocket_drone_endpoint(websocket: WebSocket, drone_id: str):
    """Handle WebSocket connections from drones"""
    await websocket.accept()
    
    # Generate a unique connection ID if not provided
    if not drone_id or drone_id == "new":
        drone_id = f"drone-{str(uuid.uuid4())[:8]}"
    
    # Register the drone
    active_drones[drone_id] = websocket
    print(f"[SERVER] ✅ Drone connected: {drone_id}")
    print(f"[SERVER] 📊 Active drones: {len(active_drones)}")
    
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
            # Wait for messages from the drone
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                print(f"[SERVER] 📥 Received from {drone_id}: {message}")
                
                # Process different message types
                if message["type"] == "telemetry":
                    # In a full implementation, we would broadcast to UI clients
                    print(f"[SERVER] 📡 Telemetry from {drone_id}: Battery: {message.get('battery', 'N/A')}%, Signal: {message.get('signal_strength', 'N/A')}%")
                    
                    # Echo back acknowledgement
                    await websocket.send_text(json.dumps({
                        "type": "telemetry_ack",
                        "timestamp": time.time(),
                        "message": "Telemetry received"
                    }))
                if message["type"] == "request_mask":
                    # Call mask generator module
                    mask = generate_mask(message["image_data"])
                    await websocket.send_text(json.dumps({
                        "type": "mask_data",
                        "mask": mask.tolist(),
                        "timestamp": time.time()
                    }))
                elif message["type"] == "corrupted_image":
                    # Call image reconstruction module
                    original = reconstruct_image(message["image_data"], message["mask_data"])
                    # Save to database
                    image_id = save_image(original, message["metadata"])
                    # Return result
                    await websocket.send_text(json.dumps({
                        "type": "reconstructed_image",
                        "image_id": image_id,
                        "timestamp": time.time() 
                    }))
                
                elif message["type"] == "command_response":
                    print(f"[SERVER] 🔄 Command response from {drone_id}: {message.get('status', 'unknown')} - {message.get('message', '')}")
                
            except json.JSONDecodeError:
                print(f"[SERVER] ⚠️ Received invalid JSON from {drone_id}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": time.time()
                }))
    
    except WebSocketDisconnect:
        # Handle disconnection
        print(f"[SERVER] ❌ Drone disconnected: {drone_id}")
        active_drones.pop(drone_id, None)
    
    except Exception as e:
        print(f"[SERVER] ⚠️ Error in drone {drone_id} connection: {str(e)}")
        active_drones.pop(drone_id, None)

@app.websocket("/ws/control")
async def websocket_control_endpoint(websocket: WebSocket):
    """Handle WebSocket connections from control interfaces"""
    await websocket.accept()
    control_id = f"control-{str(uuid.uuid4())[:8]}"
    print(f"[SERVER] ✅ Control interface connected: {control_id}")
    
    try:
        # Send drone list to the control interface
        await websocket.send_text(json.dumps({
            "type": "drone_list",
            "drones": list(active_drones.keys()),
            "timestamp": time.time()
        }))
        
        # Wait for commands from the control interface
        while True:
            data = await websocket.receive_text()
            try:
                command = json.loads(data)
                target_drone = command.get("drone_id")
                
                if target_drone in active_drones:
                    # Forward command to the specified drone
                    drone_ws = active_drones[target_drone]
                    print(f"[SERVER] 📤 Sending command to {target_drone}: {command.get('command', 'unknown')}")
                    await drone_ws.send_text(json.dumps({
                        "type": "command",
                        "command": command.get("command"),
                        "params": command.get("params", {}),
                        "timestamp": time.time()
                    }))
                else:
                    # Drone not found
                    print(f"[SERVER] ⚠️ Drone not found: {target_drone}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": f"Drone {target_drone} not connected",
                        "timestamp": time.time()
                    }))
            
            except json.JSONDecodeError:
                print("[SERVER] ⚠️ Received invalid JSON from control interface")
    
    except WebSocketDisconnect:
        print(f"[SERVER] ❌ Control interface disconnected: {control_id}")
    
    except Exception as e:
        print(f"[SERVER] ⚠️ Error in control interface connection: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("[SERVER] 🚀 Starting Drone Communication Server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)