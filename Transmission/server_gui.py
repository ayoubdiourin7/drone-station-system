import cv2
import numpy as np
import socket
import torch
import tkinter as tk
from tkinter import messagebox
from ImageCompressor import ImageCompressor
from Streamer import stream_image
from Models import NetE, AttrProxy
from PIL import Image, ImageTk

torch.serialization.add_safe_globals([NetE])


def generate_defined_mask(height=64, width=64):
    mask = np.ones((height, width), dtype=np.uint8) * 255
    mask[1::2, 1::2] = 0
    return mask


def receive_data(height, width, host='0.0.0.0', port=5001,):
    mask = generate_defined_mask(height, width)
    comp = ImageCompressor(mask)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)

    print(f"Server listening on {host}:{port}...")

    conn, addr = server_socket.accept()
    print(f"Connected to {addr}")

    stream_image(conn, comp, height, width)

    conn.close()
    server_socket.close()
    cv2.destroyAllWindows()


def start_server():
    try:
        height = int(height_entry.get())
        width = int(width_entry.get())
        
        if height <= 0 or width <= 0:
            raise ValueError("Height and Width must be positive integers.")
        
        receive_data(height, width)
    except ValueError as e:
        messagebox.showerror("Invalid Input", str(e))


# GUI Setup
root = tk.Tk()
root.title("Image Streamer Server")
root.geometry("400x300")

tk.Label(root, text="Height:").pack(pady=5)
height_entry = tk.Entry(root)
height_entry.pack(pady=5)


tk.Label(root, text="Width:").pack(pady=5)
width_entry = tk.Entry(root)
width_entry.pack(pady=5)

start_button = tk.Button(root, text="Start Server", command=start_server)
start_button.pack(pady=20)

root.mainloop()