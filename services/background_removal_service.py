import cv2
import numpy as np
import base64
from typing import Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
from datetime import datetime

class BackgroundRemovalService:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=1)
        # Parameters for background removal
        self.rect_margin = 10  # Margin from image edges
        self.iterations = 5  # Number of GrabCut iterations
        # Create Images directory if it doesn't exist
        os.makedirs("Images", exist_ok=True)

    async def remove_background(self, image_data: bytes, filename: str, cancel_token: Optional[asyncio.Event] = None) -> dict:
        """
        Remove the background from an image while preserving the original image appearance.
        
        Args:
            image_data: Raw image data in bytes
            filename: Original filename
            cancel_token: Optional event for cancellation
            
        Returns:
            Dictionary containing the base64 string and saved file path
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self._remove_background_sync, image_data, filename, cancel_token)

    def _remove_background_sync(self, image_data: bytes, filename: str, cancel_token: Optional[asyncio.Event] = None) -> dict:
        """Synchronous version of background removal for thread pool execution."""
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if cancel_token and cancel_token.is_set():
            return {"base64_image": "", "file_path": ""}

        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Create initial mask for climbing wall area
        height, width = img.shape[:2]
        mask = np.zeros(img.shape[:2], np.uint8) + 2  # Initialize with probable background (2)
        
        # Create rectangle for initial foreground area (climbing wall area)
        rect = (
            self.rect_margin,  # x
            self.rect_margin,  # y
            width - 2*self.rect_margin,  # width
            height - 2*self.rect_margin  # height
        )
        
        if cancel_token and cancel_token.is_set():
            return {"base64_image": "", "file_path": ""}

        # Initialize temporary arrays for GrabCut
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)
        
        # Run GrabCut algorithm multiple times with different parameters
        cv2.grabCut(img, mask, rect, bgd_model, fgd_model, self.iterations, cv2.GC_INIT_WITH_RECT)
        
        if cancel_token and cancel_token.is_set():
            return {"base64_image": "", "file_path": ""}

        # Create mask for foreground
        mask_foreground = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
        
        # Clean up the mask using morphological operations
        kernel = np.ones((7,7), np.uint8)
        mask_foreground = cv2.morphologyEx(mask_foreground, cv2.MORPH_CLOSE, kernel)
        mask_foreground = cv2.morphologyEx(mask_foreground, cv2.MORPH_OPEN, kernel)
        
        # Create RGBA image (4 channels - RGB + Alpha)
        rgba = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
        
        # Set alpha channel based on mask (255 for foreground, 0 for background)
        rgba[:, :, 3] = mask_foreground * 255
        
        # Generate timestamp for unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = os.path.splitext(filename)[0]
        new_filename = f"{base_filename}_nobg_{timestamp}.png"
        file_path = os.path.join("Images", new_filename)
        
        # Save the image with transparency
        cv2.imwrite(file_path, rgba)
        
        # Convert the result to base64
        _, buffer = cv2.imencode('.png', rgba)
        base64_string = base64.b64encode(buffer).decode('utf-8')
        
        return {
            "base64_image": base64_string,
            "file_path": file_path
        } 