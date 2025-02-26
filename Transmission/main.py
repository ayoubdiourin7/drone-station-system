#from PiCamera import PiCamera
import cv2
from ImageCompressor import ImageCompressor
import socket
from server import generate_defined_mask
# Setup Camera
#cam = PiCamera(256,256)
# Get a mask for image sampling
#mask = get_random_mask(width=256,height=256)
mask = generate_defined_mask(64,64)
# Image Compressor using mask and preparing data to send using socket
comp = ImageCompressor(mask)

# Server IP and port (change to your PC's IP)
SERVER_IP = "127.0.0.1"  # Replace with your PC's IP address
SERVER_PORT = 5001

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((SERVER_IP, SERVER_PORT))
print("Connected to server")

while True:
    #frame = cam.get_frame()
    frame = cv2.imread("test.png")
    frame = cv2.resize(frame,(64,64))
    data = comp.dataImage(frame) # Frame sampled and ready to be sent
    client_socket.sendall(data)
    
    frame= cv2.bitwise_and(frame,frame,mask=mask)
    cv2.imshow("Pi Camera", cv2.resize(frame,(500,500)))
    key = cv2.waitKey(1)
    if  key == ord("q"):
        break
cv2.destroyAllWindows()
#cam.close()
client_socket.close()