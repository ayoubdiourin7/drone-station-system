import numpy as np
from collections import deque
import torch
import cv2
from Models import NetME,NetE, AttrProxy

class MaskGenerator:
    def __init__(self, nb_images_mask=1, sample_rate=0.5,lambda_param=0.0, height=32, width=32):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.stored_masks = deque(maxlen=nb_images_mask)
        self.height = height
        self.width = width
        self.sample_rate = sample_rate
        self.lambda_param = lambda_param
        
        # Load model
        try:
            self.modelME = NetME(nef=64, NetE_name='model_best02.pth', sample_rate=sample_rate)
            self.modelME.load_state_dict(torch.load("model_bestM02.pth", map_location=self.device))
            self.modelME.to(self.device)
            self.modelME.eval()
            print("Model loaded successfully in MaskGenerator")
        except Exception as e:
            print(f"Error loading model in MaskGenerator: {str(e)}")
            self.modelME = None

    def preprocess_image(self, image):
        """Preprocess image to tensor format"""
        image_tensor = (torch.from_numpy(image).float() / 255.0)+2.0 - 1.0
        image_tensor = image_tensor.permute(2, 0, 1).unsqueeze(0)
        return image_tensor.to(self.device)
    
    def generate_random_mask(height=32, width=32, sampling_rate=0.5):
        """Generate a random mask."""
        #mask = np.random.choice([0, 255], size=(height, width), p=[1 - sampling_rate, sampling_rate]).astype(np.uint8)
        mask = np.ones((height, width), dtype=np.uint8) * 255
        mask[1::2, 1::2] = 0
        return mask

    def generate_and_store_mask(self, image):
        """Generate mask for new image and store it"""
        # generate mask using image gradient and keeping the best pixels according to sampling rate
         # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Compute image gradient using Sobel
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)

        # Normalize gradient magnitude to [0, 1]
        gradient_magnitude = (gradient_magnitude - gradient_magnitude.min()) / (gradient_magnitude.max() - gradient_magnitude.min())

        # Convert to tensor and move to device
        gradient_magnitude_tensor = torch.tensor(gradient_magnitude, dtype=torch.float32, device=self.device).unsqueeze(0).unsqueeze(0)

        #return gradient_magnitude
        #return mask

        if self.modelME is not None:
            with torch.no_grad():
                image_tensor = self.preprocess_image(image)
                mask_conti, _ = self.modelME(image_tensor)

         # Combine gradients with mask_conti using lambda
        combined_mask = self.lambda_param * gradient_magnitude_tensor + (1 - self.lambda_param) * mask_conti

        # Normalize the combined mask
        combined_mask = (combined_mask - combined_mask.min()) / (combined_mask.max() - combined_mask.min())

        # Store mask
        self.append_mask(combined_mask)

        return combined_mask.squeeze(0).squeeze(0).cpu().numpy()

        

    def append_mask(self, mask):
        if len(self.stored_masks) == self.stored_masks.maxlen:
            self.stored_masks.popleft()
        self.stored_masks.append(mask)

    def get_average_mask(self):
        """Calculate pixel-wise average of stored masks"""
        if not self.stored_masks:
            print("No stored masks. Generating random mask...")
            return self.generate_random_mask()

        
        average_mask = torch.mean(torch.cat(list(self.stored_masks), dim=0), dim=0)
            
        '''masks_array = np.array(list(self.stored_masks))
        height, width = masks_array[0].shape
        average_mask = np.zeros((height, width), dtype=np.float32)
        
        # Calculate pixel-wise average
        for y in range(self.height):
            for x in range(self.width):
                pixel_values = masks_array[:, y, x]
                average_mask[y, x] = np.mean(pixel_values)'''
        
        # Convert to binary mask using threshold
        
        average_mask = average_mask.squeeze(0)
        average_mask_size = average_mask.size()
        average_mask_mean = torch.mean(average_mask, 0, True)
        average_mask_mean = torch.mean(average_mask_mean, 1, True)
        average_mask_mean = average_mask_mean.expand(average_mask_size[0], average_mask_size[1])
        average_mask_out = average_mask / average_mask_mean * self.sample_rate
        average_mask_out = torch.clamp(average_mask_out, 0, 1)

        binary_mask = average_mask_out.bernoulli().cpu().numpy()
        binary_mask = binary_mask.astype(np.uint8) * 255

        return binary_mask

   

    def clear_masks(self):
        """Clear stored masks"""
        self.stored_masks.clear()