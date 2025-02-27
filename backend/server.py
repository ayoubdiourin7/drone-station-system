# server.py - WebSocket Server for Drone Communication
import asyncio
import json
import time
import uuid
import os
import base64
from typing import Dict, Set
import cv2
import numpy as np

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from transmission.video_stream import VideoStreamManager


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

# Configuration
IMAGE_PATH = 'test.jpg'  # Change this to your image path
FRAMES_DIR = 'frames'  # Directory to store received frames

# Create frames directory if it doesn't exist
os.makedirs(FRAMES_DIR, exist_ok=True)

class DroneConnection:
    def __init__(self, websocket: WebSocket, drone_id: str):
        self.websocket = websocket
        self.drone_id = drone_id
        self.is_connected = False
        self.last_telemetry = None
        self.is_streaming = False
        self.current_frame = {}  # Store frame chunks
        self.frame_buffers = {}  # Buffer for incoming frame chunks

    def start_new_frame(self, frame_id: str, total_chunks: int, total_size: int):
        """Initialize a new frame buffer"""
        print(f"[SERVER] 🎬 Initializing buffer for frame {frame_id} ({total_chunks} chunks, {total_size} bytes)")
        self.frame_buffers[frame_id] = {
            'chunks': [None] * total_chunks,
            'received_chunks': 0,
            'total_size': total_size,
            'timestamp': time.time()
        }

    def add_frame_chunk(self, frame_id: str, chunk_index: int, chunk_data: str) -> bool:
        """Add a chunk to the frame buffer and return True if frame is complete"""
        if frame_id not in self.frame_buffers:
            print(f"[SERVER] ⚠️ Received chunk for unknown frame {frame_id}")
            return False
        
        buffer = self.frame_buffers[frame_id]
        if chunk_index >= len(buffer['chunks']):
            print(f"[SERVER] ⚠️ Invalid chunk index {chunk_index} for frame {frame_id}")
            return False
            
        if buffer['chunks'][chunk_index] is None:
            buffer['chunks'][chunk_index] = chunk_data
            buffer['received_chunks'] += 1
            
            # Log progress for every 25% completed
            progress = (buffer['received_chunks'] / len(buffer['chunks'])) * 100
            if progress % 25 == 0:
                print(f"[SERVER] 📊 Frame {frame_id}: {progress}% complete ({buffer['received_chunks']}/{len(buffer['chunks'])} chunks)")
            
        return buffer['received_chunks'] == len(buffer['chunks'])

    def get_complete_frame(self, frame_id: str) -> bytes:
        """Get the complete frame data and clear the buffer"""
        if frame_id not in self.frame_buffers:
            print(f"[SERVER] ⚠️ Attempted to get unknown frame {frame_id}")
            return None
        
        buffer = self.frame_buffers[frame_id]
        if buffer['received_chunks'] != len(buffer['chunks']):
            print(f"[SERVER] ⚠️ Attempted to get incomplete frame {frame_id}")
            return None
        
        # Check for missing chunks
        if None in buffer['chunks']:
            print(f"[SERVER] ⚠️ Frame {frame_id} has missing chunks")
            return None
        
        # Combine all chunks
        try:
            # First decode each chunk from base64
            decoded_chunks = []
            for chunk_base64 in buffer['chunks']:
                try:
                    chunk_data = base64.b64decode(chunk_base64)
                    decoded_chunks.append(chunk_data)
                except Exception as e:
                    print(f"[SERVER] ⚠️ Failed to decode chunk in frame {frame_id}: {str(e)}")
                    return None

            # Combine all decoded chunks
            frame_data = b''.join(decoded_chunks)
            actual_size = len(frame_data)
            expected_size = buffer['total_size']
            
            if actual_size != expected_size:
                print(f"[SERVER] ⚠️ Size mismatch for frame {frame_id}: expected {expected_size}, got {actual_size}")
                return None
            
            print(f"[SERVER] ✅ Frame {frame_id} assembled successfully ({actual_size} bytes)")
            
            # Clean up
            del self.frame_buffers[frame_id]
            return frame_data
                
        except Exception as e:
            print(f"[SERVER] ⚠️ Error assembling frame {frame_id}: {str(e)}")
            return None

# Initialize managers
stream_manager = VideoStreamManager()
active_drones: Dict[str, DroneConnection] = {}
active_ui_clients: Set[WebSocket] = set()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "active_drones": len(active_drones),
        "streaming_drones": len([d for d in active_drones.values() if d.is_streaming]),
        "server_time": time.strftime("%Y-%m-%d %H:%M:%S")
    }

async def broadcast_drone_list():
    """Broadcast the list of available drones to all UI clients"""
    await broadcast_to_ui_clients({
        "type": "drone_list",
        "drones": list(active_drones.keys()),
        "timestamp": time.time()
    })

async def save_frame(frame_data: bytes, drone_id: str, frame_id: str) -> bool:
    """Save a frame to disk"""
    try:
        # Convert frame data to numpy array
        nparr = np.frombuffer(frame_data, np.uint8)
        # Decode the image data
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Check if image was decoded successfully
        if frame is None:
            print(f"[SERVER] ⚠️ Failed to decode image data for frame {frame_id}")
            return False
            
        # Ensure the frame is not empty
        if frame.size == 0:
            print(f"[SERVER] ⚠️ Empty frame received for frame {frame_id}")
            return False
        
        # Generate filename with timestamp
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{drone_id}_{frame_id}_{timestamp}.jpg"
        filepath = os.path.join(FRAMES_DIR, filename)
        
        # Save the frame with specific encoding parameters
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 95]
        success = cv2.imwrite(filepath, frame, encode_params)
        
        if success:
            print(f"[SERVER] 💾 Frame saved: {filename}")
            return True
        else:
            print(f"[SERVER] ⚠️ Failed to save frame to {filepath}")
            return False
            
    except Exception as e:
        print(f"[SERVER] ⚠️ Error saving frame: {str(e)}")
        # Additional debug information
        print(f"[SERVER] 🔍 Frame data size: {len(frame_data)} bytes")
        return False

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
                print(f"[SERVER] 📥 Received from {drone_id}: {message['type']}")
                
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
                    drone_connection.is_streaming = False
                    drone_connection.last_telemetry = None
                    stream_manager.remove_drone_stream(drone_id)
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
                
                elif message["type"] == "start_streaming":
                    print(f"[SERVER] 🎥 Starting stream for drone: {drone_id}")
                    # Tell drone to start streaming
                    await websocket.send_text(json.dumps({
                        "type": "start_streaming",
                        "parameters": message.get("parameters", {}),
                        "timestamp": time.time()
                    }))
                    
                    # Mark drone as streaming
                    drone_connection.is_streaming = True
                    
                    # Notify UI clients that streaming has started
                    await broadcast_to_ui_clients({
                        "type": "stream_started",
                        "drone_id": drone_id,
                        "timestamp": time.time()
                    })
                    print(f"[SERVER] ✅ Stream started for drone: {drone_id}")
                
                elif message["type"] == "frame_start":
                    frame_id = message["frame_id"]
                    total_chunks = message["total_chunks"]
                    total_size = message["total_size"]
                    drone_connection.start_new_frame(frame_id, total_chunks, total_size)
                    print(f"[SERVER] 🎬 Starting new frame {frame_id} ({total_chunks} chunks)")
                
                elif message["type"] == "frame_chunk":
                    frame_id = message["frame_id"]
                    chunk_index = message["chunk_index"]
                    chunk_data = message["data"]
                    
                    if drone_connection.add_frame_chunk(frame_id, chunk_index, chunk_data):
                        print(f"[SERVER] ✅ Frame {frame_id} complete, processing...")
                        frame_data = drone_connection.get_complete_frame(frame_id)
                        if frame_data:
                            # Save frame locally first
                            #save_success = await save_frame(frame_data, drone_id, frame_id)
                            save_success = True
                            if save_success:
                                # Convert back to base64 for sending to UI
                                frame_base64 = base64.b64encode(frame_data).decode('utf-8')
                                await broadcast_to_ui_clients({
                                    "type": "video_frame",
                                    "drone_id": drone_id,
                                    "frame": frame_base64,
                                    "timestamp": time.time()
                                })
                                print(f"[SERVER] 📤 Frame {frame_id} saved and broadcasted")
                            else:
                                print(f"[SERVER] ⚠️ Failed to save frame {frame_id}")
                
                elif message["type"] == "frame_end":
                    frame_id = message["frame_id"]
                    print(f"[SERVER] 🏁 Frame {frame_id} transmission ended")
                
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
            stream_manager.remove_drone_stream(drone_id)
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
            stream_manager.remove_drone_stream(drone_id)
            active_drones.pop(drone_id)
            await broadcast_drone_list()

@app.websocket("/ws/ui")
async def websocket_ui_endpoint(websocket: WebSocket):
    """Handle WebSocket connections from UI clients"""
    await websocket.accept()
    active_ui_clients.add(websocket)
    print("[SERVER] 🖥️ UI client connected")
    
    try:
        # Send initial drone list
        await broadcast_drone_list()
        
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                print(f"[SERVER] 📥 Received from UI: {message['type']}")
                
                if message["type"] == "connect_drone":
                    drone_id = message["drone_id"]
                    if drone_id in active_drones:
                        await active_drones[drone_id].websocket.send_text(json.dumps({
                            "type": "connect_request",
                            "timestamp": time.time()
                        }))
                
                elif message["type"] == "disconnect_drone":
                    drone_id = message["drone_id"]
                    if drone_id in active_drones:
                        await active_drones[drone_id].websocket.send_text(json.dumps({
                            "type": "disconnect_request",
                            "timestamp": time.time()
                        }))
                
                elif message["type"] == "start_streaming":
                    print(f"[SERVER] 🎥 Received start streaming request from UI")
                    drone_id = message["drone_id"]
                    if drone_id in active_drones:
                        # Forward the streaming request to the drone
                        await active_drones[drone_id].websocket.send_text(json.dumps({
                            "type": "start_streaming",
                            "parameters": message.get("parameters", {}),
                            "timestamp": time.time()
                        }))
                        print(f"[SERVER] 🎥 Forwarded streaming request to drone: {drone_id}")
            
            except json.JSONDecodeError:
                print("[SERVER] ⚠️ Received invalid JSON from UI")
    
    except WebSocketDisconnect:
        print("[SERVER] ❌ UI client disconnected")
        active_ui_clients.remove(websocket)
    
    except Exception as e:
        print(f"[SERVER] ⚠️ Error in UI client connection: {str(e)}")
        active_ui_clients.remove(websocket)

async def broadcast_to_ui_clients(message: dict):
    """Broadcast a message to all connected UI clients"""
    disconnected_clients = set()
    
    for client in active_ui_clients:
        try:
            await client.send_text(json.dumps(message))
        except Exception as e:
            print(f"[SERVER] ⚠️ Error broadcasting to UI client: {str(e)}")
            disconnected_clients.add(client)
    
    # Remove disconnected clients
    for client in disconnected_clients:
        active_ui_clients.remove(client)

if __name__ == "__main__":
    import uvicorn
    print("[SERVER] 🚀 Starting Drone Communication Server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)