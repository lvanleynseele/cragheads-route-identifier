import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
import io
import asyncio
from concurrent.futures import ThreadPoolExecutor

class ImageProcessor:
    def __init__(self):
        # Define color ranges for common climbing hold colors
        self.color_ranges = {
            'red': [(0, 100, 100), (10, 255, 255)],
            'blue': [(100, 100, 100), (130, 255, 255)],
            'green': [(40, 100, 100), (80, 255, 255)],
            'yellow': [(20, 100, 100), (30, 255, 255)],
            'purple': [(130, 100, 100), (160, 255, 255)],
            'orange': [(10, 100, 100), (20, 255, 255)],
            'pink': [(150, 100, 100), (170, 255, 255)],
            'white': [(0, 0, 200), (180, 30, 255)],
            'black': [(0, 0, 0), (180, 255, 30)]
        }
        
        # Define BGR colors for visualization (OpenCV uses BGR)
        self.visualization_colors = {
            'red': (0, 0, 255),
            'blue': (255, 0, 0),
            'green': (0, 255, 0),
            'yellow': (0, 255, 255),
            'purple': (255, 0, 255),
            'orange': (0, 165, 255),
            'pink': (255, 192, 203),
            'white': (255, 255, 255),
            'black': (0, 0, 0)
        }
        
        # Define chalk detection parameters (bright white)
        self.chalk_threshold = 200  # Brightness threshold for chalk
        self.chalk_saturation_threshold = 50  # Low saturation threshold for chalk
        self._executor = ThreadPoolExecutor(max_workers=1)

    async def process_image(self, image_data: bytes, cancel_token: Optional[asyncio.Event] = None) -> Dict[str, List[Dict[str, any]]]:
        """
        Process the uploaded image to identify climbing holds by color.
        
        Args:
            image_data: Raw image data in bytes
            cancel_token: Optional event for cancellation
            
        Returns:
            Dictionary containing identified holds grouped by color
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self._process_image_sync, image_data, cancel_token)

    def _process_image_sync(self, image_data: bytes, cancel_token: Optional[asyncio.Event] = None) -> Dict[str, List[Dict[str, any]]]:
        """Synchronous version of process_image for thread pool execution."""
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Convert to HSV color space for better color detection
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Create chalk mask (bright white areas)
        chalk_mask = (hsv[:,:,2] > self.chalk_threshold) & (hsv[:,:,1] < self.chalk_saturation_threshold)
        
        results = {}
        
        for color, (lower, upper) in self.color_ranges.items():
            if cancel_token and cancel_token.is_set():
                return {}
                
            # Create mask for current color
            lower = np.array(lower)
            upper = np.array(upper)
            mask = cv2.inRange(hsv, lower, upper)
            
            # Apply morphological operations to reduce noise
            kernel = np.ones((5,5), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            
            # Find contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            holds = []
            for contour in contours:
                if cancel_token and cancel_token.is_set():
                    return {}
                    
                # Filter out very small contours
                if cv2.contourArea(contour) < 100:  # Adjust threshold as needed
                    continue
                
                # Create a mask for this specific contour
                contour_mask = np.zeros_like(mask, dtype=np.uint8)
                cv2.drawContours(contour_mask, [contour], -1, 255, -1)
                
                # Get the average color within the contour (excluding chalk)
                valid_pixels = contour_mask > 0
                valid_pixels[chalk_mask] = 0
                
                if np.any(valid_pixels):
                    mean_color = cv2.mean(img, mask=valid_pixels.astype(np.uint8))[:3]
                else:
                    # If all pixels are chalk, use the predefined color
                    mean_color = self.visualization_colors.get(color, (0, 0, 0))
                
                # Get bounding box
                x, y, w, h = cv2.boundingRect(contour)
                
                # Calculate center point
                center_x = x + w // 2
                center_y = y + h // 2
                
                # Convert contour to list of points for JSON serialization
                contour_points = contour.reshape(-1, 2).tolist()
                
                holds.append({
                    "position": {
                        "x": int(center_x),
                        "y": int(center_y)
                    },
                    "size": {
                        "width": int(w),
                        "height": int(h)
                    },
                    "contour": contour_points,
                    "color": [int(c) for c in mean_color]  # Store the average color
                })
            
            if holds:
                results[color] = holds
        
        return results

    async def get_route_by_color(self, image_data: bytes, target_color: str, cancel_token: Optional[asyncio.Event] = None) -> Dict[str, any]:
        """
        Get all holds of a specific color from the image.
        
        Args:
            image_data: Raw image data in bytes
            target_color: Color to identify (must be one of the predefined colors)
            cancel_token: Optional event for cancellation
            
        Returns:
            Dictionary containing the identified holds of the specified color
        """
        if target_color not in self.color_ranges:
            raise ValueError(f"Unsupported color: {target_color}")
            
        results = await self.process_image(image_data, cancel_token)
        return {
            "color": target_color,
            "holds": results.get(target_color, [])
        }

    async def identify_all_routes(self, image_data: bytes, cancel_token: Optional[asyncio.Event] = None) -> Dict[str, List[Dict[str, any]]]:
        """
        Identify all climbing holds in the image, grouped by color.
        
        Args:
            image_data: Raw image data in bytes
            cancel_token: Optional event for cancellation
            
        Returns:
            Dictionary containing all identified holds grouped by color
        """
        return await self.process_image(image_data, cancel_token) 