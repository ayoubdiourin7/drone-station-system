#from PiCamera import PiCamera
import cv2
from ImageCompressor import ImageCompressor
import socket
import supervision as sv
from time import time
import pickle
import struct
import select  # Import select for non-blocking socket check

INTERVAL = 10  # seconds
# Setup Camera
#cam = PiCamera(256,256)
# Get a mask for image sampling
#mask = get_random_mask(width=256,height=256)
#mask = generate_defined_mask(HEIGHT,WIDTH)
# Image Compressor using mask and preparing data to send using socket
#comp = ImageCompressor(mask)

# Server IP and port (change to your PC's IP)
SERVER_IP = "127.0.0.1"  # Replace with your PC's IP address
SERVER_PORT = 5001



def receive_mask(client_socket):
     # Receive mask size
    payload_size = struct.calcsize("Q")
    packed_msg_size = client_socket.recv(payload_size)
    msg_size = struct.unpack("Q", packed_msg_size)[0]

    # Receive new mask
    mask_data = b""
    while len(mask_data) < msg_size:
        mask_data += client_socket.recv(4096)

    new_mask = pickle.loads(mask_data)
    print("Received new mask, updating compressor.")

    
    return new_mask

def receive_dimensions_mask(client_socket):
    """Receive height and width from the server."""
    # Receive size of the data
    payload_size = struct.calcsize("Q")
    packed_msg_size = client_socket.recv(payload_size)
    print(f"Received payload size: {len(packed_msg_size)}")
    msg_size = struct.unpack("Q", packed_msg_size)[0]

    # Receive the height and width data
    data = b""
    while len(data) < msg_size:
        data += client_socket.recv(4096)

    mask,height, width = pickle.loads(data)
    print(f"Received dimensions from server: HEIGHT={height}, WIDTH={width}")
    return mask,height, width

def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((SERVER_IP, SERVER_PORT))
    print("Connected to server")
    t_i = time()

    # Receive height and width from the server
    mask,HEIGHT, WIDTH = receive_dimensions_mask(client_socket)
    comp = ImageCompressor(mask)  # Initialize compressor with mask

    for frame in sv.get_video_frames_generator("video.mp4"):
        #frame = cam.get_frame()
        #frame = cv2.imread("test.png")
        frame = cv2.resize(frame,(HEIGHT,WIDTH))
        original_frame = frame.copy()
        data = comp.dataImage(frame) # Frame sampled and ready to be sent
        client_socket.sendall(b"C")  # Send command to server to receive image
        client_socket.sendall(data)
        frame[mask == 0] = (128, 128, 128)
        #frame = cv2.resize(frame,(500,500))
        cv2.imshow("Pi Camera", frame)
        key = cv2.waitKey(1)
        if  key == ord("q"):
            break

        # Check if there is incoming data on the socket
        readable, _, _ = select.select([client_socket], [], [], 0)  # Timeout = 0 (non-blocking)
        if readable:
            command = int.from_bytes(client_socket.recv(1), "big")
            if command == ord("M"):
                    mask = receive_mask(client_socket)
                    comp = ImageCompressor(mask)  # Update compressor
        t_f = time()
        if (t_f - t_i) > INTERVAL:
            client_socket.sendall(b"U")
            t_i = time()
            # Send full image
            pickle_data = pickle.dumps(original_frame)
            message_size = struct.pack("Q", len(pickle_data))
            client_socket.sendall(message_size + pickle_data) 
            print("Sent Image request")

    cv2.destroyAllWindows()
    #cam.close()
    client_socket.close()

if __name__ == "__main__":
    main()