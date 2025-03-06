import numpy as np
import struct
import pickle
import cv2
from Reconstructor import Reconstructor
import supervision as sv
from PIL import Image, ImageTk
import tkinter as tk



class Streamer:
    def __init__(self, comp, HEIGHT=500, WIDTH=500):
        self.fps_monitor = sv.FPSMonitor()
        self.rec = Reconstructor()
        self.payload_size = struct.calcsize("Q")  # Size of packed data length
        self.height = HEIGHT
        self.width = WIDTH
        self.comp = comp


    def stream_image(self, conn, data):
        
        while len(data) < self.payload_size:
            packet = conn.recv(4096)
            if not packet:
                break
            data += packet
        
        packed_msg_size = data[:self.payload_size]
        data = data[self.payload_size:]
        msg_size = struct.unpack("Q", packed_msg_size)[0]
        
        while len(data) < msg_size:
            data += conn.recv(4096)
        
        frame_data = data[:msg_size]
        data = data[msg_size:]
        
        sampled_pixels,indices = pickle.loads(frame_data)

        self.comp.update_indices(indices)

        # Decompress the sampled image
        image = self.comp.decompress(sampled_pixels)

        # Resize without interpolation (just pixel replication)
        cv2.imshow("Sampled Image", cv2.resize(image, None, fx=20, fy=20, interpolation=cv2.INTER_NEAREST))

        # Reconstruct the image
        reconstructed_image = self.rec.reconstruct(image)

        self.fps_monitor.tick()
        fps = self.fps_monitor.fps


        # Resize without interpolation (just pixel replication)
        resized_image = cv2.resize(reconstructed_image, None, fx=20, fy=20, interpolation=cv2.INTER_NEAREST)

        reconstructed_image = sv.draw_text(
            scene=resized_image,
            text=f"{fps:.1f}",
            text_anchor=sv.Point(40, 30),
            background_color=sv.Color.from_hex("#A351FB"),
            text_color=sv.Color.from_hex("#000000"),
        )

        # Show the received reconstructed image
        cv2.imshow("Reconstructed Sampled Image", reconstructed_image)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            return None

        return data
    
    def stream_full_image(self, conn, data):
        while len(data) < self.payload_size:
            packet = conn.recv(4096)
            if not packet:
                break
            data += packet
        
        packed_msg_size = data[:self.payload_size]
        data = data[self.payload_size:]
        msg_size = struct.unpack("Q", packed_msg_size)[0]
        
        while len(data) < msg_size:
            data += conn.recv(4096)
        
        frame_data = data[:msg_size]
        data = data[msg_size:]
        
        full_image = pickle.loads(frame_data)

        # Resize without interpolation (just pixel replication)
        full_image = cv2.resize(full_image, None, fx=20, fy=20, interpolation=cv2.INTER_NEAREST)

        # Show the received reconstructed image
        cv2.imshow("Full Image", full_image)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            return None

        return data
    
    def update_comp(self, comp):
        self.comp = comp