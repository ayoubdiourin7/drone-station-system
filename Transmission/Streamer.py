import numpy as np
import struct
import pickle
import cv2
from Reconstructor import Reconstructor
import supervision as sv
from PIL import Image, ImageTk
import tkinter as tk




def stream_image(conn, comp, HEIGHT=500, WIDTH=500):
    fps_monitor = sv.FPSMonitor()
    rec = Reconstructor()
    
    
    data = b""
    payload_size = struct.calcsize("Q")  # Size of packed data length
    
    while True:
        while len(data) < payload_size:
            packet = conn.recv(4096)
            if not packet:
                break
            data += packet
        
        packed_msg_size = data[:payload_size]
        data = data[payload_size:]
        msg_size = struct.unpack("Q", packed_msg_size)[0]
        
        while len(data) < msg_size:
            data += conn.recv(4096)
        
        frame_data = data[:msg_size]
        data = data[msg_size:]
        
        sampled_pixels = pickle.loads(frame_data)

        # Decompress the sampled image
        image = comp.decompress(sampled_pixels)

        # Reconstruct the image
        reconstructed_image = rec.reconstruct(image)

        fps_monitor.tick()
        fps = fps_monitor.fps


        reconstructed_image = cv2.resize(reconstructed_image, (500, 500))
        reconstructed_image = sv.draw_text(
            scene=reconstructed_image,
            text=f"{fps:.1f}",
            text_anchor=sv.Point(40, 30),
            background_color=sv.Color.from_hex("#A351FB"),
            text_color=sv.Color.from_hex("#000000"),
        )

        # Show the received reconstructed image
        cv2.imshow("Reconstructed Sampled Image", reconstructed_image)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break