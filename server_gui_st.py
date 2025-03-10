import streamlit as st
import cv2
import numpy as np
import socket
import torch
import pickle
import struct
from time import time
from ImageCompressor import ImageCompressor
from Streamer import Streamer
from Models import NetE, AttrProxy
from MaskGenerator import MaskGenerator

# Constants
INTERVAL_FRAMES = 10
SAMPLE_RATE = 0.2
LAMBDA_PARAM_MASK = 0.3
DEFAULT_HEIGHT = 32
DEFAULT_WIDTH = 32

# ✅ Initialize Streamlit session state variables
if "logs" not in st.session_state:
    st.session_state.logs = ""
if "height" not in st.session_state:
    st.session_state.height = DEFAULT_HEIGHT
if "width" not in st.session_state:
    st.session_state.width = DEFAULT_WIDTH
if "server_running" not in st.session_state:
    st.session_state.server_running = False
if "conn" not in st.session_state:
    st.session_state.conn = None  # Connection object
if "client_ip" not in st.session_state:
    st.session_state.client_ip = None  # Store connected client IP
if "uncompressed_image_count" not in st.session_state:
    st.session_state.uncompressed_image_count = 0


# Function to generate a random mask
def generate_random_mask(height=32, width=32, sampling_rate=0.5):
    mask = np.ones((height, width), dtype=np.uint8) * 255
    mask[1::2, 1::2] = 0
    mask[2::2, 2::2] = 0
    return mask

# Function to start the server
def start_server():
    if st.session_state.server_running:
        st.warning("Server is already running!")
        return

    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(('0.0.0.0', 5001))
        server_socket.listen(1)

        st.session_state.logs += "Server listening on port 5001...\n"
        st.session_state.server_socket = server_socket
        st.session_state.server_running = True

        st.rerun()  # Move to waiting for client

    except Exception as e:
        st.session_state.logs += f"Error starting server: {str(e)}\n"
        st.rerun()

# Function to connect to the client (only once)
def connect_client():
    if not st.session_state.server_running or st.session_state.conn:
        return  # Already connected or server not started

    try:
        print("Waiting for client...")
        conn, addr = st.session_state.server_socket.accept()
        st.session_state.logs += f"Connected to {addr[0]}:{addr[1]}\n"
        st.session_state.conn = conn  # Save connection
        st.session_state.client_ip = addr[0]  # Store client IP

        # Send initial mask
        mask = generate_random_mask(st.session_state.height, st.session_state.width)
        mhw_data = pickle.dumps((mask, st.session_state.height, st.session_state.width))
        message_size = struct.pack("Q", len(mhw_data))
        conn.sendall(message_size + mhw_data)

        # Initialize image processing components
        comp = ImageCompressor(mask)
        st.session_state.mask_generator = MaskGenerator(nb_images_mask=128, sample_rate=SAMPLE_RATE, lambda_param=LAMBDA_PARAM_MASK, height=st.session_state.height, width=st.session_state.width)
        st.session_state.image_streamer = Streamer(comp, st.session_state.mask_generator, st.session_state.height, st.session_state.width)
        st.session_state.frame_count = 0
        st.session_state.data = b""

        st.rerun()  # Move to frame processing

    except Exception as e:
        st.session_state.logs += f"Error connecting to client or Initializing Processing: {str(e)}\n"
        st.rerun()

# Function to process one frame per rerun (only when streaming is active)
def process_frame():
    if not st.session_state.server_running or not st.session_state.conn:
        return  # No server running, no connection, or streaming is stopped

    try:
        conn = st.session_state.conn
        data = st.session_state.data

        # Receive command
        while len(data) < 1:
            data += conn.recv(4096)

        command = data[:1].decode()
        data = data[1:]  # Remove command from buffer
        #st.session_state.logs += f"Received command: {command}\n"

        if command == "C":
            data = st.session_state.image_streamer.stream_image(conn, data)
            if data is None:
                st.session_state.logs += "Connection closed\n"
                st.session_state.conn = None
                st.rerun()
                return

        elif command == "U":
            st.session_state.uncompressed_image_count += 1
            st.session_state.frame_count += 1
            st.session_state.logs += f"Received Full Image - Count: {st.session_state.uncompressed_image_count}\n"
            data = st.session_state.image_streamer.stream_full_image(conn, data)

        # Send a new mask every INTERVAL_FRAMES frames
        if st.session_state.frame_count >= INTERVAL_FRAMES:
            st.session_state.frame_count = 0  # Reset counter
            new_mask = st.session_state.mask_generator.get_average_mask()
            st.session_state.image_streamer.comp.add_mask_update_indices(new_mask)
            mask_data = pickle.dumps(new_mask)
            message_size = struct.pack("Q", len(mask_data))
            conn.sendall(b"M" + message_size + mask_data)
            st.session_state.logs += "Sent new mask to client.\n"

        st.session_state.data = data

        st.rerun()  # Process the next frame on rerun

    except Exception as e:
        st.session_state.logs += f"Error processing frame: {str(e)}\n"
        st.rerun()

# Function to stop the server
def stop_server():
    if not st.session_state.server_running:
        st.warning("Server is not running!")
        return

    st.session_state.server_running = False
    st.session_state.client_ip = None  # Reset client IP

    if st.session_state.conn:
        st.session_state.conn.close()
        st.session_state.conn = None
    if st.session_state.server_socket:
        st.session_state.server_socket.close()
        st.session_state.server_socket = None

    st.session_state.logs += "Server stopped.\n"
    st.rerun()


    st.rerun()

# Streamlit UI
st.title("Image Streamer Server")

st.sidebar.header("Server Configuration")
st.session_state.height = int(st.sidebar.text_input("Height:", str(DEFAULT_HEIGHT)))
st.session_state.width = int(st.sidebar.text_input("Width:", str(DEFAULT_WIDTH)))

# Server Control Buttons
if st.sidebar.button("Start Server"):
    start_server()
if st.sidebar.button("Stop Server"):
    stop_server()


# Show Connected Client IP
if st.session_state.client_ip:
    st.sidebar.markdown(f"**Connected to:** `{st.session_state.client_ip}`")

st.sidebar.markdown(f"**Uncompressed Images Count:** `{st.session_state.uncompressed_image_count}`")

st.text_area("Logs:", value=st.session_state.logs, height=300)


# Section 1: Sampled & Reconstructed Image (Main Content)
st.header("Sampled & Reconstructed Image")
col11, col12 = st.columns(2)

with col12:
    if "reconstructed_image" in st.session_state and st.session_state.reconstructed_image is not None:
        st.image(st.session_state.reconstructed_image, caption="Reconstructed Image", use_container_width=True)
    else:
        st.warning("No reconstructed image received yet.")

with col11:
    if "sampled_image" in st.session_state and st.session_state.sampled_image is not None:
        st.image(st.session_state.sampled_image, caption="Sampled Image", use_container_width=True)
    else:
        st.warning("No sampled image received yet.")

# Section 2: Full Image & Mask (Sidebar)
st.header("Full Image & Mask")
col21, col22 = st.columns(2)

with col21:
    if "full_image" in st.session_state and st.session_state.full_image is not None:
        st.image(st.session_state.full_image, caption="Full Image", use_container_width=True)
    else:
        st.warning("No full image received yet.")

with col22:
    if "mask_image" in st.session_state and st.session_state.mask_image is not None:
        st.image(st.session_state.mask_image, caption="Mask", use_container_width=True)
    else:
        st.warning("No mask received yet.")





# **Server Logic Execution**
if st.session_state.server_running:
    connect_client()  # Connect once (only if not connected)

process_frame()  # Process one frame per rerun
