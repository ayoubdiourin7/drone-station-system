import numpy as np
import struct
import pickle

class ImageCompressor:
    def __init__(self, mask):
        self.indices = np.argwhere(mask == 255)
        self.mask = mask
        self.height = mask.shape[0]
        self.width = mask.shape[1]

    def compress(self, sampled_pixels):
        """Serializes sampled pixels."""
        return pickle.dumps(sampled_pixels)

    def decompress(self, serialized_data):
        """Deserializes and reconstructs a partial image."""
        sampled_pixels = pickle.loads(serialized_data)
        image = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        for (y, x), pixel in zip(self.indices, sampled_pixels):
            image[y, x] = pixel
        return image

    def pack_message(self, data):
        """Packs the data with its size."""
        message_size = struct.pack("Q", len(data))
        return message_size + data

    def unpack_message(self, packed_data):
        """Unpacks the data from the packed message."""
        payload_size = struct.calcsize("Q")
        message_size = struct.unpack("Q", packed_data[:payload_size])[0]
        data = packed_data[payload_size:]
        return data, message_size
    
    def sample_pixels(self, frame):
        """Samples pixels from the frame based on the mask."""
        sampled_pixels = frame[self.mask == 255]
        return sampled_pixels
