import cv2
import numpy as np
import socket
import torch
import tkinter as tk
import threading
from tkinter import messagebox
from ImageCompressor import ImageCompressor
from Streamer import Streamer
from PIL import Image, ImageTk
from time import time
import pickle
import struct
from Models import NetE, AttrProxy
from MaskGenerator import MaskGenerator

#torch.serialization.add_safe_globals([NetE])
INTERVAL_TIME = 50 # seconds
INTERVAL_FRAMES = 10
SAMPLE_RATE = 1
LAMBDA_PARAM_MASK = 0.8

def generate_random_mask(height=32, width=32, sampling_rate=0.5):
    """Generate a random mask."""
    #mask = np.random.choice([0, 255], size=(height, width), p=[1 - sampling_rate, sampling_rate]).astype(np.uint8)
    mask = np.ones((height, width), dtype=np.uint8) * 255
    mask[1::2, 1::2] = 0
    mask[2::2, 2::2] = 0
    return mask


# Counter variables
uncompressed_image_count = 0  # Counter for received images
counter_var = None  # Tkinter variable for updating GUI



def receive_data(height, width,sample_rate, host='0.0.0.0', port=5001):
    """Receives image data from the client and updates the GUI counter."""
    global uncompressed_image_count

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)

    print(f"Server listening on {host}:{port}...")
    conn, addr = server_socket.accept()
    print(f"Connected to {addr}")

    

    # Send the initial mask and height/width to the client
    mask = generate_random_mask(height, width)
    mhw_data = pickle.dumps((mask, height, width))
    message_size = struct.pack("Q", len(mhw_data))
    conn.sendall(message_size + mhw_data)  # Prefix "M" to indicate a mask update
    
    comp = ImageCompressor(mask)
    mask_generator = MaskGenerator(nb_images_mask=128, sample_rate=sample_rate,lambda_param=LAMBDA_PARAM_MASK, height=height, width=width)
    image_streamer = Streamer(comp, mask_generator, height, width)
    last_sent_time = time()
    data = b""
    frame_count = 0
    while True:
        while len(data) < 1:
            data += conn.recv(4096)

        # Extract command
        command = data[:1].decode()
        data = data[1:]  # Remove command from buffer
        print(f"Received command: {command}")

        if command == "C":
            data = image_streamer.stream_image(conn, data)
            if data is None:
                print("Connection closed")
                break
        
        elif command == "U":
            # Increment counter
            uncompressed_image_count += 1
            frame_count += 1
            print(f"Received Full Image - Count: {uncompressed_image_count}")
            data = image_streamer.stream_full_image(conn, data)

            # Update GUI in the main Tkinter thread
            root.after(0, update_counter)

        # **Check if INTERVAL seconds have passed, then send a new mask**
        #if time() - last_sent_time >= INTERVAL:
        if frame_count == INTERVAL_FRAMES:
            frame_count = 0
            print("Sending new mask to client...")
            new_mask = mask_generator.get_average_mask()
            mask_data = pickle.dumps(new_mask)
            message_size = struct.pack("Q", len(mask_data))
            conn.sendall(b"M" + message_size + mask_data)  # Prefix "M" to indicate a mask update
            last_sent_time = time()

    conn.close()
    server_socket.close()
    cv2.destroyAllWindows()
    
def update_counter():
    """Update the GUI counter label in Tkinter."""
    counter_var.set(f"Uncompressed Images: {uncompressed_image_count}")


def start_server():
    """Start the server in a separate thread to avoid blocking Tkinter."""
    try:
        height = int(height_entry.get())
        width = int(width_entry.get())

        if height <= 0 or width <= 0:
            raise ValueError("Height and Width must be positive integers.")

        # Run the server in a new thread
        server_thread = threading.Thread(target=receive_data, args=(height, width, SAMPLE_RATE))
        server_thread.daemon = True  # Ensures it exits when the main program closes
        server_thread.start()

    except ValueError as e:
        messagebox.showerror("Invalid Input", str(e))


# Tkinter variables
height_entry = None
width_entry = None
counter_label = None
root = None


def main():
    """Setup the Tkinter GUI."""
    global height_entry, width_entry, counter_label, counter_var, root

    # Create the main window
    root = tk.Tk()
    root.title("Image Streamer Server")
    root.geometry("400x350")

    tk.Label(root, text="Height:").pack(pady=5)
    height_entry = tk.Entry(root)
    height_entry.insert(0, "32")
    height_entry.pack(pady=5)

    tk.Label(root, text="Width:").pack(pady=5)
    width_entry = tk.Entry(root)
    width_entry.insert(0, "32")
    width_entry.pack(pady=5)

    # Button to start the server
    start_button = tk.Button(root, text="Start Server", command=start_server)
    start_button.pack(pady=10)

    # Counter Label
    counter_var = tk.StringVar()
    counter_var.set("Uncompressed Images: 0")
    counter_label = tk.Label(root, textvariable=counter_var, font=("Arial", 14))
    counter_label.pack(pady=10)

    root.mainloop()


if __name__ == "__main__":
    main()
