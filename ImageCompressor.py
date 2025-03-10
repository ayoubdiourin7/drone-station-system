import numpy as np
import struct
import pickle

class ImageCompressor:
    def __init__(self,mask):
        self.indices = np.argwhere(mask == 255)
        self.height = mask.shape[0]
        self.width = mask.shape[1]
        self.masks = [mask]
    
    def dataImage(self, frame):
        mask_id = len(self.masks) - 1
        sampled_pixels = frame[self.indices[:, 0], self.indices[:, 1]]
        data = pickle.dumps((sampled_pixels,mask_id))
        message_size = struct.pack("Q", len(data))
        return message_size + data
        
    def decompress(self, sampled_pixels, mask_id):
        image = np.ones((self.height, self.width,3), dtype=np.uint8)*128
        for (y, x), pixel in zip(self.indices, sampled_pixels):
            image[y, x] = pixel
        return image

    def add_mask_update_indices(self, mask):
        self.masks.append(mask)
        self.indices = np.argwhere(mask == 255)