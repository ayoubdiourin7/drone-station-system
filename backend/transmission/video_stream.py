import cv2
import base64
import numpy as np
from typing import Optional, Dict
import asyncio
import time

class VideoStreamManager:
    def __init__(self):
        self.drone_streams: Dict[str, 'DroneStream'] = {}
    
    def add_drone_stream(self, drone_id: str) -> 'DroneStream':
        """Create a new stream for a drone"""
        if drone_id not in self.drone_streams:
            self.drone_streams[drone_id] = DroneStream(drone_id)
        return self.drone_streams[drone_id]
    
    def remove_drone_stream(self, drone_id: str):
        """Remove a drone's stream"""
        if drone_id in self.drone_streams:
            self.drone_streams[drone_id].stop()
            del self.drone_streams[drone_id]
    
    def get_stream(self, drone_id: str) -> Optional['DroneStream']:
        """Get a drone's stream if it exists"""
        return self.drone_streams.get(drone_id)

class DroneStream:
    def __init__(self, drone_id: str):
        self.drone_id = drone_id
        self.current_frame = None
        self.last_frame_time = 0
        self.is_streaming = False
        self.fps = 0
        self.frame_count = 0
        self.start_time = time.time()
    
    def update_frame(self, frame_data: str):
        """Update the current frame with new frame data"""
        try:
            # Decode base64 image
            
            img_bytes = base64.b64decode(frame_data)
            img_arr = np.frombuffer(img_bytes, dtype=np.uint8)
            frame = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
            
            # Update frame and metrics
            self.current_frame =  frame
            self.last_frame_time =  time.time()
            self.frame_count +=  1
            self.fps = self.frame_count  /  ( self.last_frame_time - self.start_time )
            
            return True
        except Exception as e:
            print(f"Error updating frame: {e}")
            return False
    
    def get_current_frame(self) -> Optional[str]:
        """Get the current frame as base64 encoded JPEG"""
        if self.current_frame is None:
            return None
        
        try:
            # Convert frame to JPEG and then to base64
            _, buffer = cv2.imencode('.jpg', self.current_frame)
            return base64.b64encode(buffer).decode('utf-8')
        except Exception as e:
            print(f"Error encoding frame: {e}")
            return None
    
    def start(self):
        """Start streaming"""
        self.is_streaming = True
        self.start_time = time.time()
        self.frame_count = 0
    
    def stop(self):
        """Stop streaming"""
        self.is_streaming = False
        self.current_frame = None
        self.fps = 0
    
    def get_stats(self) -> dict:
        """Get stream statistics"""
        return {
            "drone_id": self.drone_id,
            "is_streaming": self.is_streaming,
            "fps": round(self.fps, 2),
            "frame_count": self.frame_count,
            "uptime": round(time.time() - self.start_time, 2) if self.is_streaming else 0
        } 