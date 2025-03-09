import cv2
import numpy as np
from typing import List, Tuple, Dict
import io

class ImageProcessor:
    def __init__(self):
        # Define color ranges for common climbing hold colors
        # These are example ranges and should be adjusted based on actual hold colors
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

    def process_image(self, image_data: bytes) -> Dict[str, List[Dict[str, any]]]:
        """
        Process the uploaded image to identify climbing holds by color.
        
        Args:
            image_data: Raw image data in bytes
            
        Returns:
            Dictionary containing identified holds grouped by color
        """
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Convert to HSV color space for better color detection
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        results = {}
        
        for color, (lower, upper) in self.color_ranges.items():
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
                # Filter out very small contours
                if cv2.contourArea(contour) < 100:  # Adjust threshold as needed
                    continue
                    
                # Get bounding box
                x, y, w, h = cv2.boundingRect(contour)
                
                # Calculate center point
                center_x = x + w // 2
                center_y = y + h // 2
                
                holds.append({
                    "position": {
                        "x": int(center_x),
                        "y": int(center_y)
                    },
                    "size": {
                        "width": int(w),
                        "height": int(h)
                    }
                })
            
            if holds:
                results[color] = holds
        
        return results

    def get_route_by_color(self, image_data: bytes, target_color: str) -> Dict[str, any]:
        """
        Get all holds of a specific color from the image.
        
        Args:
            image_data: Raw image data in bytes
            target_color: Color to identify (must be one of the predefined colors)
            
        Returns:
            Dictionary containing the identified holds of the specified color
        """
        if target_color not in self.color_ranges:
            raise ValueError(f"Unsupported color: {target_color}")
            
        results = self.process_image(image_data)
        return {
            "color": target_color,
            "holds": results.get(target_color, [])
        } 