import cv2
import numpy as np
import socket
from ImageCompressor import ImageCompressor
from Streamer import Streamer
from Models import NetE, AttrProxy
import torch


def generate_defined_mask(height=64, width=64):
    mask = np.ones((height, width), dtype=np.uint8)*255
    mask[1::2, 1::2] = 0
    return mask

HEIGHT = 32
WIDTH = 32

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

    image_streamer = Streamer(comp, HEIGHT, WIDTH)
    data = b""
    while True:
        # Receive command type (mask request or image transmission)
        # Ensure we have at least 1 byte to read the command
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
            print("Received Full Image")

    conn.close()
    server_socket.close()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    receive_data()



