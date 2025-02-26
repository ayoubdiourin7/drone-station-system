import cv2
import numpy as np
import socket
from ImageCompressor import ImageCompressor
from Streamer import stream_image
from Models import NetE, AttrProxy
import torch


def generate_defined_mask(height=64, width=64):
    mask = np.ones((height, width), dtype=np.uint8)*255
    mask[1::5, 1::5] = 0
    return mask

HEIGHT = 64
WIDTH = 64

HOST = '0.0.0.0'  # Listen on all interfaces
PORT = 5001  # Port

mask = generate_defined_mask(HEIGHT, WIDTH)
comp = ImageCompressor(mask)

# def receive_data(HEIGHT=64, WIDTH=64, HOST='0.0.0.0', PORT=5001, comp, model, "dkchi d stream"):
def receive_data():
    """Receives the sampled image and reconstructs it."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(1)
    
    print(f"Server listening on {HOST}:{PORT}...")
    
    conn, addr = server_socket.accept()
    print(f"Connected to {addr}")

    stream_image(conn, comp, HEIGHT, WIDTH)

    conn.close()
    server_socket.close()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    receive_data()



