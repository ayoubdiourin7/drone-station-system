import numpy as np
import struct
import pickle

class ImageCompressor:
    def __init__(self,mask):
        self.indices = np.argwhere(mask==255)
        self.mask = mask
        self.height = mask.shape[0]
        self.width = mask.shape[1]
    
    def dataImage(self, frame):
        sampled_pixels = frame[self.mask==255]
        data = pickle.dumps(sampled_pixels)
        message_size = struct.pack("Q", len(data))
        return message_size + data
        
    def decompress(self, sampled_pixels):
        image = np.zeros((self.height, self.width,3), dtype=np.uint8)
        for (y, x), pixel in zip(self.indices, sampled_pixels):
            image[y, x] = pixel
        return image