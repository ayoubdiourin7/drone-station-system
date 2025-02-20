# control_client.py - Simple Terminal Control Client
import asyncio
import json
import signal
import sys
import time
from datetime import datetime

import websockets

# Configuration
SERVER_URL = "ws://localhost:8000/ws/control"

class ControlClient:
    def __init__(self):
        self.running = True
        self.connected = False
        self.available_drones = []
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, sig, frame):
        """Handle termination signals"""
        print("\n[CONTROL] 🛑 Shutdown signal received, closing connection...")
        self.running = False
    
    def format_timestamp(self):
        """Format current time for display"""
        return datetime.now().strftime("%H:%M:%S")

    def print_menu(self):
        """Print the command menu"""
        print("\n====== DRONE CONTROL MENU ======")
        if not self.available_drones:
            print("No drones connected. Waiting for drones...")
            return None
        
        print("Available drones:")
        for i, drone_id in enumerate(self.available_drones, 1):
            print(f"  {i}. {drone_id}")
        
        print("\nCommands:")
        print("  1. Take off")
        print("  2. Land")
        print("  3. Capture image")
        print("  4. Refresh drone list")
        print("  0. Exit")
        
        try:
            # Get drone selection
            drone_idx = int(input("\nSelect drone (number): ")) - 1
            if drone_idx < 0 or drone_idx >= len(self.available_drones):
                raise ValueError()
            
            selected_drone = self.available_drones[drone_idx]
            print(f"Selected drone: {selected_drone}")
            
            # Get command selection
            cmd = int(input("Select command (number): "))
            
            if cmd == 0:
                self.running = False
                return None
            elif cmd == 1:
                altitude = input("Enter altitude (meters): ")
                return {
                    "drone_id": selected_drone,
                    "command": "take_off",
                    "params": {"altitude": float(altitude)}
                }
            elif cmd == 2:
                return {
                    "drone_id": selected_drone,
                    "command": "land",
                    "params": {}
                }
            elif cmd == 3:
                return {
                    "drone_id": selected_drone,
                    "command": "capture_image",
                    "params": {}
                }
            elif cmd == 4:
                # Just refresh - no command to send
                return "refresh"
            else:
                print("Invalid command selection")
                return None
                
        except (ValueError, IndexError):
            print("Invalid selection. Please try again.")
            return None
    
    async def connect_and_communicate(self):
        """Connect to the server and handle communication"""
        print(f"[CONTROL] 🔄 {self.format_timestamp()} Connecting to server at {SERVER_URL}...")
        
        reconnect_delay = 1
        
        while self.running:
            try:
                async with websockets.connect(SERVER_URL) as websocket:
                    self.connected = True
                    print(f"[CONTROL] ✅ {self.format_timestamp()} Connected to server")
                    
                    # Reset reconnect delay after successful connection
                    reconnect_delay = 1
                    
                    # Start the message listener task
                    listener_task = asyncio.create_task(self.listen_for_messages(websocket))
                    
                    # Command input loop
                    while self.running:
                        command = self.print_menu()
                        
                        if not self.running:
                            break
                            
                        if command == "refresh":
                            # Just refresh the UI
                            continue
                            
                        if command:
                            # Send command to server
                            time_str = self.format_timestamp()
                            print(f"[CONTROL] 📤 {time_str} Sending command: {command['command']} to {command['drone_id']}")
                            await websocket.send(json.dumps(command))
                        
                        # Small delay to prevent UI flicker
                        await asyncio.sleep(0.5)
                    
                    # Cancel listener task when main loop exits
                    listener_task.cancel()
            
            except (websockets.exceptions.ConnectionClosed, 
                    websockets.exceptions.InvalidStatusCode,
                    ConnectionRefusedError) as e:
                self.connected = False
                if self.running:
                    print(f"[CONTROL] ❌ {self.format_timestamp()} Connection error: {e}")
                    print(f"[CONTROL] 🔄 {self.format_timestamp()} Reconnecting in {reconnect_delay} seconds...")
                    await asyncio.sleep(reconnect_delay)
                    
                    # Exponential backoff with maximum of 30 seconds
                    reconnect_delay = min(reconnect_delay * 2, 30)
            
            except Exception as e:
                self.connected = False
                if self.running:
                    print(f"[CONTROL] ⚠️ {self.format_timestamp()} Unexpected error: {e}")
                    print(f"[CONTROL] 🔄 {self.format_timestamp()} Reconnecting in {reconnect_delay} seconds...")
                    await asyncio.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 2, 30)
        
        print(f"[CONTROL] 👋 {self.format_timestamp()} Control client shutdown complete")
    
    async def listen_for_messages(self, websocket):
        """Listen for messages from the server"""
        while self.running:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                time_str = self.format_timestamp()
                
                if data["type"] == "drone_list":
                    self.available_drones = data["drones"]
                    print(f"[CONTROL] 🔄 {time_str} Updated drone list: {len(self.available_drones)} connected")
                
                elif data["type"] == "error":
                    print(f"[CONTROL] ⚠️ {time_str} Error from server: {data['message']}")
                
            except json.JSONDecodeError:
                print(f"[CONTROL] ⚠️ {time_str} Received invalid JSON from server")
            
            except Exception as e:
                print(f"[CONTROL] ⚠️ {time_str} Error receiving message: {e}")
                break

async def main():
    """Start the control client"""
    print("[CONTROL] 🎮 Starting Drone Control Terminal Client...")
    print("[CONTROL] ℹ️ Press Ctrl+C to exit")
    client = ControlClient()
    await client.connect_and_communicate()

if __name__ == "__main__":
    asyncio.run(main())