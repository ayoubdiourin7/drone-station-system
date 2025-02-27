import cv2
import base64
import time
import asyncio
import numpy as np

class CameraSimulator:
    def __init__(self, camera_id=0, target_fps=30):
        self.camera_id = camera_id
        self.target_fps = target_fps
        self.frame_interval = 1.0 / target_fps
        self.cap = None
        self.is_running = False
        
        # For test pattern generation
        self.frame_count = 0
        self.use_test_pattern = False
    
    async def start(self):
        """Start the camera capture"""
        if not self.use_test_pattern:
            self.cap = cv2.VideoCapture(self.camera_id)
            if not self.cap.isOpened():
                print(f"Could not open camera {self.camera_id}, falling back to test pattern")
                self.use_test_pattern = True
        
        self.is_running = True
    
    def stop(self):
        """Stop the camera capture"""
        self.is_running = False
        if self.cap:
            self.cap.release()
            self.cap = None
    
    def generate_test_pattern(self):
        """Generate a test pattern frame"""
        # Create a 640x480 frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Add moving elements
        t = time.time()
        x = int(320 + 200 * np.cos(t))
        y = int(240 + 200 * np.sin(t))
        
        # Draw a circle that moves in a circular pattern
        cv2.circle(frame, (x, y), 20, (0, 255, 0), -1)
        
        # Add frame counter and timestamp
        cv2.putText(frame, f"Frame: {self.frame_count}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, time.strftime("%H:%M:%S"), (10, 70),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        return frame
    
    async def get_frame(self) -> str:
        """Get the next frame as base64 encoded JPEG"""
        if not self.is_running:
            return None
        
        try:
            if self.use_test_pattern:
                frame = self.generate_test_pattern()
            else:
                ret, frame = self.cap.read()
                if not ret:
                    print("Failed to capture frame, falling back to test pattern")
                    self.use_test_pattern = True
                    frame = self.generate_test_pattern()
            
            # Convert frame to JPEG
            _, buffer = cv2.imencode('.jpg', frame)
            # Convert to base64
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            
            self.frame_count += 1
            
            # Maintain target FPS
            await asyncio.sleep(self.frame_interval)
            
            return jpg_as_text
            
        except Exception as e:
            print(f"Error capturing frame: {e}")
            return None

async def test_camera():
    """Test the camera simulator"""
    camera = CameraSimulator()
    await camera.start()
    
    try:
        for _ in range(100):  # Capture 100 frames
            frame = await camera.get_frame()
            if frame:
                print(f"Captured frame, size: {len(frame)} bytes")
            await asyncio.sleep(0.033)  # ~30 FPS
    finally:
        camera.stop()

if __name__ == "__main__":
    asyncio.run(test_camera()) 