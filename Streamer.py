import numpy as np
import struct
import pickle
import cv2
from Reconstructor import Reconstructor
import supervision as sv
from PIL import Image, ImageTk
import tkinter as tk
from MaskGenerator import MaskGenerator
import streamlit as st
import time


class Streamer:
    def __init__(self, comp, mask_generator, HEIGHT=500, WIDTH=500):
        self.fps_monitor = sv.FPSMonitor()
        self.rec = Reconstructor()
        self.payload_size = struct.calcsize("Q")  # Size of packed data length
        self.height = HEIGHT
        self.width = WIDTH
        self.comp = comp
        self.mask_generator = mask_generator


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
        
        sampled_pixels,mask_id = pickle.loads(frame_data)

        # Decompress the sampled image
        image = self.comp.decompress(sampled_pixels, mask_id)

        resized_image = cv2.resize(image, None, fx=20, fy=20, interpolation=cv2.INTER_NEAREST)
        resized_image_rgb = cv2.cvtColor(resized_image, cv2.COLOR_BGR2RGB)
        resized_image_rgb = (resized_image_rgb * 255).astype(np.uint8) if resized_image_rgb.dtype == np.float32 else resized_image_rgb
        pil_image = Image.fromarray(resized_image_rgb)
        st.session_state.sampled_image = pil_image

        # Resize without interpolation (just pixel replication)
        '''cv2.imshow("Sampled Image", cv2.resize(image, None, fx=20, fy=20, interpolation=cv2.INTER_NEAREST))'''

        # Reconstruct the image
        reconstructed_image = image #self.rec.reconstruct(image)
        time.sleep(0.1)

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

        '''# Show the received reconstructed image
        cv2.imshow("Reconstructed Sampled Image", reconstructed_image)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            return None'''
        
        # Convert OpenCV BGR to RGB
        resized_image_rgb = cv2.cvtColor(resized_image, cv2.COLOR_BGR2RGB)

        # ✅ Ensure dtype is uint8 (convert float32 to uint8)
        resized_image_rgb = (resized_image_rgb * 255).astype(np.uint8) if resized_image_rgb.dtype == np.float32 else resized_image_rgb

        # Convert to PIL Image
        pil_image = Image.fromarray(resized_image_rgb)


        # Store the image in Streamlit session state
        st.session_state.reconstructed_image = pil_image

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

        mask = self.mask_generator.generate_and_store_mask(full_image)
        resized_mask = cv2.resize(mask, None, fx=20, fy=20, interpolation=cv2.INTER_NEAREST)
        resized_mask = (resized_mask * 255).astype(np.uint8) if resized_mask.dtype == np.float32 else resized_mask
        pil_mask = Image.fromarray(resized_mask)
        st.session_state.mask_image = pil_mask

        '''cv2.imshow("Mask", cv2.resize(mask, None, fx=20, fy=20, interpolation=cv2.INTER_NEAREST))'''

        
        

        # Resize without interpolation (just pixel replication)
        full_image = cv2.resize(full_image, None, fx=20, fy=20, interpolation=cv2.INTER_NEAREST)
        
        # Show the received reconstructed image
        '''cv2.imshow("Full Image", full_image)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            return None'''
        
        # Convert OpenCV BGR to RGB
        full_image_rgb = cv2.cvtColor(full_image, cv2.COLOR_BGR2RGB)
        full_image_rgb = (full_image_rgb * 255).astype(np.uint8) if full_image_rgb.dtype == np.float32 else full_image_rgb
        pil_image = Image.fromarray(full_image_rgb)
        st.session_state.full_image = pil_image


        return data
    
    def update_comp(self, comp):
        self.comp = comp