import numpy as np
import struct
import pickle

class ImageCompressor:
    def __init__(self,mask):
        self.indices_list = [np.argwhere(mask == 255)]
        self.height = mask.shape[0]
        self.width = mask.shape[1]
    
    def dataImage(self, frame):
        mask_id = len(self.indices_list) - 1
        indices = self.indices_list[mask_id]
        sampled_pixels = frame[indices[:, 0], indices[:, 1]]
        data = pickle.dumps((sampled_pixels,mask_id))
        message_size = struct.pack("Q", len(data))
        return message_size + data
        
    def decompress(self, sampled_pixels, mask_id):
        indices = self.indices_list[mask_id]
        image = np.ones((self.height, self.width,3), dtype=np.uint8)*128
        for (y, x), pixel in zip(indices, sampled_pixels):
            image[y, x] = pixel
        return image

    def add_mask_update_indices(self, mask):
        self.indices_list.append(np.argwhere(mask == 255))