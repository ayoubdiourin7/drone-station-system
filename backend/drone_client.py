# drone_client.py - Terminal-based Drone WebSocket Client
import asyncio
import json
import random
import signal
import sys
import time
from datetime import datetime

import websockets

# Configuration
SERVER_URL = "ws://localhost:8000/ws/drone/new"

class DroneSensors:
    def __init__(self):
        self.battery = 100
        self.storage_used = 0
        self.signal_strength = random.randint(85, 99)
    
    def get_telemetry(self):
        return {
            "battery": round(self.battery, 1),
            "storage_used": self.storage_used,
            "signal_strength": self.signal_strength,
            "timestamp": time.time()
        }

class DroneClient:
    def __init__(self):
        self.drone_id = None
        self.sensors = DroneSensors()
        self.running = True
        self.connected = False
        self.connection_approved = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, sig, frame):
        """Handle termination signals"""
        print("\n[DRONE] 🛑 Shutdown signal received, closing connection...")
        self.running = False
    
    def format_timestamp(self):
        """Format current time for display"""
        return datetime.now().strftime("%H:%M:%S")

    async def connect_and_communicate(self):
        """Connect to the server and handle communication"""
        print(f"[DRONE] 🔄 {self.format_timestamp()} Connecting to server at {SERVER_URL}...")
        
        reconnect_delay = 1
        
        while self.running:
            try:
                async with websockets.connect(SERVER_URL) as websocket:
                    self.connected = True
                    print(f"[DRONE] ✅ {self.format_timestamp()} Connected to server")
                    
                    # Reset reconnect delay after successful connection
                    reconnect_delay = 1
                    
                    # Wait for initial confirmation from server
                    response = await websocket.recv()
                    response_data = json.loads(response)
                    
                    if response_data["type"] == "connection_confirmed":
                        self.drone_id = response_data["drone_id"]
                        print(f"[DRONE] 🆔 {self.format_timestamp()} Assigned drone ID: {self.drone_id}")
                    
                    # Listen for commands
                    while self.running:
                        try:
                            message = await websocket.recv()
                            data = json.loads(message)
                            time_str = self.format_timestamp()

                            if data["type"] == "connect_request":
                                print(f"[DRONE] 🔗 {time_str} Connection request received")
                                # Send connection approval
                                await websocket.send(json.dumps({
                                    "type": "connection_approved",
                                    "timestamp": time.time()
                                }))
                                self.connection_approved = True
                                
                                # Send initial telemetry after connection approval
                                telemetry = self.sensors.get_telemetry()
                                await websocket.send(json.dumps({
                                    "type": "telemetry",
                                    **telemetry
                                }))
                                print(f"[DRONE] 📡 {time_str} Initial telemetry sent")

                            elif data["type"] == "disconnect_request":
                                print(f"[DRONE] 🔌 {time_str} Disconnect request received")
                                self.connection_approved = False
                                await websocket.send(json.dumps({
                                    "type": "disconnect_confirmed",
                                    "timestamp": time.time()
                                }))
                                
                        except json.JSONDecodeError:
                            print(f"[DRONE] ⚠️ {time_str} Received invalid JSON from server")
                
            except (websockets.exceptions.ConnectionClosed, 
                    websockets.exceptions.InvalidStatusCode,
                    ConnectionRefusedError) as e:
                self.connected = False
                self.connection_approved = False
                if self.running:
                    print(f"[DRONE] ❌ {self.format_timestamp()} Connection error: {e}")
                    print(f"[DRONE] 🔄 {self.format_timestamp()} Reconnecting in {reconnect_delay} seconds...")
                    await asyncio.sleep(reconnect_delay)
                    
                    # Exponential backoff with maximum of 30 seconds
                    reconnect_delay = min(reconnect_delay * 2, 30)
            
            except Exception as e:
                self.connected = False
                self.connection_approved = False
                if self.running:
                    print(f"[DRONE] ⚠️ {self.format_timestamp()} Unexpected error: {e}")
                    print(f"[DRONE] 🔄 {self.format_timestamp()} Reconnecting in {reconnect_delay} seconds...")
                    await asyncio.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 2, 30)
        
        print(f"[DRONE] 👋 {self.format_timestamp()} Drone client shutdown complete")

async def main():
    """Start the drone client"""
    print("[DRONE] 🚁 Starting Drone WebSocket Client...")
    print("[DRONE] ℹ️ Press Ctrl+C to exit")
    client = DroneClient()
    await client.connect_and_communicate()

if __name__ == "__main__":
    asyncio.run(main())