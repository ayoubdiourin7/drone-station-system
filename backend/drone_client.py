# drone_client.py - Terminal-based Drone WebSocket Client
import asyncio
import json
import random
import signal
import sys
import time
import uuid
from datetime import datetime

import websockets

# Configuration
SERVER_URL = "ws://localhost:8000/ws/drone/new"
TELEMETRY_INTERVAL = 5  # seconds

# Mock drone sensor data
class DroneSensors:
    def __init__(self):
        self.battery = 100
        self.storage_used = 0
        self.altitude = 0
        self.is_flying = False
        self.image_count = 0
    
    def get_telemetry(self):
        # Simulate battery drain
        if self.is_flying and self.battery > 0:
            self.battery -= 0.2
        elif self.battery < 100 and not self.is_flying:
            self.battery += 0.05
        
        self.battery = max(0, min(100, self.battery))
        
        return {
            "battery": round(self.battery, 1),
            "storage_used": self.storage_used,
            "altitude": self.altitude,
            "signal_strength": random.randint(85, 99),
            "temperature": 25 + random.randint(-3, 3),
            "is_flying": self.is_flying,
            "image_count": self.image_count,
            "gps": {
                "lat": 37.7749 + random.uniform(-0.01, 0.01),
                "lng": -122.4194 + random.uniform(-0.01, 0.01)
            }
        }

class DroneClient:
    def __init__(self):
        self.drone_id = None
        self.sensors = DroneSensors()
        self.running = True
        self.connected = False
        
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
    
    def simulate_command_execution(self, command, params):
        """Simulate executing drone commands"""
        time_str = self.format_timestamp()
        
        if command == "take_off":
            print(f"[DRONE] 🚁 {time_str} Taking off to altitude: {params.get('altitude', 10)}m")
            self.sensors.is_flying = True
            self.sensors.altitude = params.get('altitude', 10)
            return {"status": "success", "message": "Drone is now airborne"}
            
        elif command == "land":
            print(f"[DRONE] 🛬 {time_str} Landing drone...")
            self.sensors.is_flying = False
            self.sensors.altitude = 0
            return {"status": "success", "message": "Drone has landed"}
            
        elif command == "capture_image":
            print(f"[DRONE] 📸 {time_str} Capturing image...")
            self.sensors.image_count += 1
            self.sensors.storage_used += random.uniform(2.5, 4.0)
            return {"status": "success", "message": f"Image captured (#{self.sensors.image_count})"}
            
        else:
            print(f"[DRONE] ❓ {time_str} Unknown command: {command}")
            return {"status": "error", "message": f"Unknown command: {command}"}
    
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
                    
                    # Start the telemetry task
                    telemetry_task = asyncio.create_task(self.send_telemetry(websocket))
                    
                    # Listen for commands
                    while self.running:
                        try:
                            message = await websocket.recv()
                            data = json.loads(message)
                            time_str = self.format_timestamp()
                            
                            if data["type"] == "command":
                                command = data.get("command")
                                params = data.get("params", {})
                                print(f"[DRONE] 📥 {time_str} Received command: {command}")
                                
                                # Execute the command
                                result = self.simulate_command_execution(command, params)
                                
                                # Send response back to server
                                response = {
                                    "type": "command_response",
                                    "command": command,
                                    "status": result["status"],
                                    "message": result["message"],
                                    "timestamp": time.time()
                                }
                                await websocket.send(json.dumps(response))
                            
                            elif data["type"] == "telemetry_ack":
                                # Just for debugging, can be removed in production
                                print(f"[DRONE] 📡 {time_str} Telemetry acknowledged by server")
                                
                        except json.JSONDecodeError:
                            print(f"[DRONE] ⚠️ {time_str} Received invalid JSON from server")
                
                    # Cancel telemetry task when main loop exits
                    telemetry_task.cancel()
            
            except (websockets.exceptions.ConnectionClosed, 
                    websockets.exceptions.InvalidStatusCode,
                    ConnectionRefusedError) as e:
                self.connected = False
                if self.running:
                    print(f"[DRONE] ❌ {self.format_timestamp()} Connection error: {e}")
                    print(f"[DRONE] 🔄 {self.format_timestamp()} Reconnecting in {reconnect_delay} seconds...")
                    await asyncio.sleep(reconnect_delay)
                    
                    # Exponential backoff with maximum of 30 seconds
                    reconnect_delay = min(reconnect_delay * 2, 30)
            
            except Exception as e:
                self.connected = False
                if self.running:
                    print(f"[DRONE] ⚠️ {self.format_timestamp()} Unexpected error: {e}")
                    print(f"[DRONE] 🔄 {self.format_timestamp()} Reconnecting in {reconnect_delay} seconds...")
                    await asyncio.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 2, 30)
        
        print(f"[DRONE] 👋 {self.format_timestamp()} Drone client shutdown complete")
    
    async def send_telemetry(self, websocket):
        """Periodically send telemetry data to the server"""
        while self.running:
            try:
                telemetry = self.sensors.get_telemetry()
                message = {
                    "type": "telemetry",
                    "timestamp": time.time(),
                    **telemetry
                }
                
                time_str = self.format_timestamp()
                print(f"[DRONE] 📤 {time_str} Sending telemetry: Battery: {telemetry['battery']}%, Signal: {telemetry['signal_strength']}%")
                
                await websocket.send(json.dumps(message))
                await asyncio.sleep(TELEMETRY_INTERVAL)
                
            except Exception as e:
                print(f"[DRONE] ⚠️ {self.format_timestamp()} Error sending telemetry: {e}")
                break

async def main():
    """Start the drone client"""
    print("[DRONE] 🚁 Starting Drone WebSocket Client...")
    print("[DRONE] ℹ️ Press Ctrl+C to exit")
    client = DroneClient()
    await client.connect_and_communicate()

if __name__ == "__main__":
    asyncio.run(main())