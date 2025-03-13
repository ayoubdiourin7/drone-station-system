import torch
import numpy as np
from Models import NetE, AttrProxy

class Reconstructor:
    def __init__(self, model_path="model_best02.pth"):
        # Safely load the model using the NetE class
        #torch.serialization.add_safe_globals([NetE])
        #self.model = torch.load(model_path, weights_only=False)
        self.model = torch.load(model_path)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = self.model.to(self.device)
        
        print("Model loaded")

    def preprocess(self, canvas):
        """Preprocess the input image (canvas) to tensor format."""
        canvas = (canvas.astype(np.float32) / 255.0)*2.0 -1.0
        canvas_tensor = torch.tensor(canvas).permute(2, 0, 1).unsqueeze(0)
        return canvas_tensor.to(self.device)

    def reconstruct(self, canvas):
        """Reconstruct the image using the model."""
        canvas_tensor = self.preprocess(canvas)

        self.model.eval()
        with torch.no_grad():
            predicted_tensor = self.model(canvas_tensor)
            predicted_numpy = predicted_tensor.squeeze(0).permute(1, 2, 0).cpu().numpy()  # Convert back to (H, W, C)
            predicted_numpy = (predicted_numpy + 1.0) / 2.0  # Scale back to [0,1]

        return predicted_numpy



