# drone_client.py - Terminal-based Drone WebSocket Client
import asyncio
import json
import random
import signal
import sys
import time
from datetime import datetime
import cv2
import base64

import websockets
from transmission.camera_simulator import CameraSimulator
from transmission.video_stream import VideoStreamManager
from transmission.ImageCompressor import ImageCompressor
import numpy as np

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
        self.camera = CameraSimulator()
        self.streaming = False
        
        # Initialize image compression components
        self.HEIGHT = 64
        self.WIDTH = 64
        self.mask = self.generate_defined_mask(self.HEIGHT, self.WIDTH)
        self.compressor = ImageCompressor(self.mask)
        
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

    def generate_defined_mask(self, height=64, width=64):
        """Generate a defined mask for image sampling"""
        mask = np.ones((height, width), dtype=np.uint8)*255
        mask[1::5, 1::5] = 0
        return mask

    async def send_compressed_frame(self, websocket, image_size=None):
        """Send a compressed frame using chunked transfer"""
        try:
            # Read the test image
            frame = cv2.imread("test.jpg")  # Make sure this file exists
            if frame is None:
                print("[DRONE] ⚠️ Could not read test image, generating test pattern")
                frame = self.generate_test_pattern()
            
            # Resize only if a specific size is requested and it's not 'original'
            if image_size and image_size != 'original':
                try:
                    # Extract numeric value from string like "64x64"
                    size = int(image_size.split('x')[0])
                    frame = cv2.resize(frame, (size, size))
                    print(f"[DRONE] 📏 Resized frame to {size}x{size}")
                except (ValueError, TypeError, IndexError) as e:
                    print(f"[DRONE] ⚠️ Invalid image size: {image_size}, using original size. Error: {e}")
            else:
                print(f"[DRONE] 📏 Using original frame size: {frame.shape[1]}x{frame.shape[0]}")
            
            # Compress frame with high quality JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 95]
            _, buffer = cv2.imencode('.jpg', frame, encode_param)
            frame_data = buffer.tobytes()
            
            # Split the data into chunks (max 64KB per chunk)
            chunk_size = 64 * 1024  # 64KB chunks
            total_chunks = (len(frame_data) + chunk_size - 1) // chunk_size
            frame_id = str(time.time())  # Unique ID for this frame
            
            # Send frame start message
            await websocket.send(json.dumps({
                "type": "frame_start",
                "frame_id": frame_id,
                "total_chunks": total_chunks,
                "total_size": len(frame_data),
                "timestamp": time.time()
            }))
            
            # Send chunks
            for i in range(total_chunks):
                chunk = frame_data[i * chunk_size : (i + 1) * chunk_size]
                chunk_base64 = base64.b64encode(chunk).decode('utf-8')
                
                await websocket.send(json.dumps({
                    "type": "frame_chunk",
                    "frame_id": frame_id,
                    "chunk_index": i,
                    "data": chunk_base64,
                    "timestamp": time.time()
                }))
                
                # Small delay between chunks to prevent overwhelming the connection
                await asyncio.sleep(0.001)
            
            # Send frame end message
            await websocket.send(json.dumps({
                "type": "frame_end",
                "frame_id": frame_id,
                "timestamp": time.time()
            }))
            
            print(f"[DRONE] 📤 Sent frame {frame_id} in {total_chunks} chunks")
            return True
            
        except Exception as e:
            print(f"[DRONE] ⚠️ Error sending compressed frame: {e}")
            return False

    def generate_test_pattern(self):
        """Generate a test pattern if image file is not available"""
        frame = np.zeros((self.HEIGHT, self.WIDTH, 3), dtype=np.uint8)
        # Add some visual elements
        cv2.rectangle(frame, (10, 10), (self.WIDTH-10, self.HEIGHT-10), (0, 255, 0), 2)
        cv2.putText(frame, "TEST", (20, self.HEIGHT//2),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        return frame

    async def stream_compressed_frames(self, websocket, parameters=None):
        """Stream compressed frames continuously"""
        print(f"[DRONE] 🎥 Starting compressed frame stream with parameters: {parameters}")
        self.streaming = True
        
        # Get image size from parameters if provided
        image_size = parameters.get("image_size") if parameters else None
        print(f"[DRONE] 📏 Using image size: {image_size}")
        
        frame_count = 0
        try:
            while self.running and self.streaming and self.connection_approved:
                success = await self.send_compressed_frame(websocket, image_size)
                if success:
                    frame_count += 1
                    if frame_count % 10 == 0:  # Log every 10 frames
                        print(f"[DRONE] 📊 Sent {frame_count} frames")
                else:
                    print("[DRONE] ⚠️ Failed to send frame, retrying...")
                    await asyncio.sleep(1)  # Wait a bit longer before retrying
                    continue
                
                await asyncio.sleep(0.1)  # 10 FPS
        except Exception as e:
            print(f"[DRONE] ⚠️ Error in streaming: {e}")
        finally:
            self.streaming = False
            print(f"[DRONE] 🛑 Streaming stopped after sending {frame_count} frames")

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
                                await websocket.send(json.dumps({
                                    "type": "connection_approved",
                                    "timestamp": time.time()
                                }))
                                self.connection_approved = True
                                
                                telemetry = self.sensors.get_telemetry()
                                await websocket.send(json.dumps({
                                    "type": "telemetry",
                                    **telemetry
                                }))
                                print(f"[DRONE] 📡 {time_str} Initial telemetry sent")

                            elif data["type"] == "start_streaming":
                                print(f"[DRONE] 🎥 {time_str} Starting compressed frame stream")
                                await self.stream_compressed_frames(websocket, data.get("parameters"))

                            elif data["type"] == "disconnect_request":
                                print(f"[DRONE] 🔌 {time_str} Disconnect request received")
                                self.connection_approved = False
                                self.streaming = False
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
                self.streaming = False
                if self.running:
                    print(f"[DRONE] ❌ {self.format_timestamp()} Connection error: {e}")
                    print(f"[DRONE] 🔄 {self.format_timestamp()} Reconnecting in {reconnect_delay} seconds...")
                    await asyncio.sleep(reconnect_delay)
                    
                    # Exponential backoff with maximum of 30 seconds
                    reconnect_delay = min(reconnect_delay * 2, 30)
            
            except Exception as e:
                self.connected = False
                self.connection_approved = False
                self.streaming = False
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