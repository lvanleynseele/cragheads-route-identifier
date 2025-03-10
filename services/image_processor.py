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
        
        # Pre-create kernels for morphological operations
        self.noise_kernel = np.ones((5,5), np.uint8)
        self.connect_kernel = np.ones((7,7), np.uint8)
        self.dilate_kernel = np.ones((15,15), np.uint8)  # For expanding hold area to find nearby chalk
        
        # Define chalk detection parameters (bright white)
        self.chalk_threshold = 100  # Brightness threshold for chalk
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
        chalk_mask = cv2.inRange(hsv, (0, 0, self.chalk_threshold), (180, self.chalk_saturation_threshold, 255))
        
        results = {}
        
        for color, (lower, upper) in self.color_ranges.items():
            if cancel_token and cancel_token.is_set():
                return {}
                
            # Create mask for current color
            color_mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
            
            # Apply morphological operations to reduce noise
            color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_OPEN, self.noise_kernel)
            color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_CLOSE, self.noise_kernel)
            
            # Find initial contours for the colored areas
            initial_contours, _ = cv2.findContours(color_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Create a mask of the hold areas slightly expanded
            hold_area_mask = np.zeros_like(color_mask)
            for contour in initial_contours:
                if cv2.contourArea(contour) < 100:  # Filter small contours
                    continue
                cv2.drawContours(hold_area_mask, [contour], -1, 255, -1)
            
            # Dilate the hold area mask to include nearby chalk
            dilated_hold_mask = cv2.dilate(hold_area_mask, self.dilate_kernel, iterations=1)
            
            # Only keep chalk that's on or near holds
            valid_chalk_mask = cv2.bitwise_and(chalk_mask, dilated_hold_mask)
            
            # Combine color mask with valid chalk
            combined_mask = cv2.bitwise_or(color_mask, valid_chalk_mask)
            
            # Connect chalk areas with holds
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, self.connect_kernel)
            
            # Find final contours
            contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            holds = []
            for contour in contours:
                if cancel_token and cancel_token.is_set():
                    return {}
                    
                # Filter out very small contours
                if cv2.contourArea(contour) < 100:  # Adjust threshold as needed
                    continue
                
                # Create a mask for this specific contour
                contour_mask = np.zeros_like(color_mask, dtype=np.uint8)
                cv2.drawContours(contour_mask, [contour], -1, 255, -1)
                
                # Get the average color from the non-chalk areas
                non_chalk_mask = cv2.bitwise_and(contour_mask, cv2.bitwise_not(chalk_mask))
                
                # If there are non-chalk pixels, use their color, otherwise use the predefined color
                if cv2.countNonZero(non_chalk_mask) > 0:
                    mean_color = cv2.mean(img, mask=non_chalk_mask)[:3]
                else:
                    mean_color = self.visualization_colors[color]
                
                # Get bounding box and center point
                x, y, w, h = cv2.boundingRect(contour)
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
                    },
                    "contour": contour.reshape(-1, 2).tolist(),
                    "color": [int(c) for c in mean_color]
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