import cv2
import numpy as np
import base64
from typing import Optional, List, Tuple
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
from datetime import datetime
from utils.logger import logger

class BackgroundRemovalService:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=1)
        
        # Parameters for edge detection
        self.edge_threshold1 = 20  # Lower threshold for edge detection (more sensitive)
        self.edge_threshold2 = 100  # Upper threshold for edge detection (more lenient)
        self.edge_kernel_size = 3  # Smaller kernel for more precise edges
        
        # Parameters for hold detection
        self.min_hold_size = 200   # Smaller minimum area for holds
        self.noise_kernel = np.ones((3,3), np.uint8)  # Smaller kernel for noise removal
        self.cleanup_kernel = np.ones((5,5), np.uint8)  # Smaller kernel for cleanup
        
        # Define color ranges for holds in HSV
        # Format: [(lower1, upper1), (lower2, upper2)] for each color
        # Multiple ranges per color to handle variations
        self.hold_colors = {
            'red': [
                (np.array([0, 50, 30]), np.array([15, 255, 255])),     # Red-red (wider hue range)
                (np.array([155, 50, 30]), np.array([180, 255, 255]))   # Purple-red (wider)
            ],
            'yellow': [
                (np.array([15, 50, 30]), np.array([40, 255, 255]))     # Yellow range (wider)
            ],
            'orange': [
                (np.array([5, 50, 30]), np.array([25, 255, 255]))      # Orange range (wider)
            ],
            'purple': [
                (np.array([125, 20, 20]), np.array([155, 255, 255]))   # Purple range (wider, lower mins)
            ],
            'green': [
                (np.array([30, 20, 20]), np.array([90, 255, 255]))     # Wide green range (even wider)
            ],
            'white': [
                (np.array([0, 0, 160]), np.array([180, 60, 255]))      # White/chalk range (more lenient saturation)
            ],
            'black': [
                (np.array([0, 0, 0]), np.array([180, 255, 60]))        # Dark/black range (higher value allowed)
            ],
            'pink': [
                (np.array([145, 20, 30]), np.array([175, 255, 255])),  # Pink range (wider)
                (np.array([0, 20, 30]), np.array([15, 180, 255]))      # Light pink range (wider)
            ]
        }
        
        # Create Images directory if it doesn't exist
        os.makedirs("Images", exist_ok=True)

    def _find_dominant_colors(self, img: np.ndarray, mask: Optional[np.ndarray] = None) -> Tuple[List[np.ndarray], List[float]]:
        """
        Find dominant colors in the image using k-means clustering.
        
        Args:
            img: Image in BGR format
            mask: Optional mask of pixels to consider (0 for ignore, 255 for include)
            
        Returns:
            Tuple of (colors, percentages)
        """
        # Convert to HSV
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Get pixels to consider
        if mask is not None:
            valid_pixels = hsv[mask > 0]
        else:
            valid_pixels = hsv.reshape(-1, 3)
        
        if len(valid_pixels) == 0:
            return [], []
        
        # Convert to float32
        pixels = np.float32(valid_pixels)
        
        # Define criteria and apply kmeans
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        _, labels, centers = cv2.kmeans(pixels, self.n_colors, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        
        # Convert centers back to uint8
        centers = np.uint8(centers)
        
        # Get the counts of each cluster
        unique_labels, counts = np.unique(labels, return_counts=True)
        percentages = counts / len(labels)
        
        # Sort colors by frequency
        sorted_indices = np.argsort(-counts)
        sorted_centers = centers[sorted_indices]
        sorted_percentages = percentages[sorted_indices]
        
        return sorted_centers, sorted_percentages

    def _is_chalk_color(self, color: np.ndarray) -> bool:
        """Check if a color is likely to be chalk (high value, low saturation)."""
        _, s, v = color
        return v > 200 and s < 50

    def _is_similar_color(self, color1: np.ndarray, color2: np.ndarray, threshold: int) -> bool:
        """Check if two colors are similar within the given threshold."""
        h1, s1, v1 = color1
        h2, s2, v2 = color2
        
        # If either color is chalk-like, be more lenient with matching
        if self._is_chalk_color(color1) or self._is_chalk_color(color2):
            # For chalk-like colors, focus more on value and saturation
            s_diff = abs(s1 - s2)
            v_diff = abs(v1 - v2)
            return s_diff < threshold * 2 and v_diff < threshold * 2
        
        # Handle hue wrap-around
        h_diff = min(abs(h1 - h2), 180 - abs(h1 - h2))
        s_diff = abs(s1 - s2)
        v_diff = abs(v1 - v2)
        
        return (h_diff < threshold and 
                s_diff < threshold and 
                v_diff < threshold)

    def _create_color_masks(self, hsv_img: np.ndarray) -> np.ndarray:
        """Create masks for all predefined hold colors."""
        height, width = hsv_img.shape[:2]
        combined_mask = np.zeros((height, width), dtype=np.uint8)
        
        # Create debug image to show color detection
        color_debug = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Process each color
        for color_name, ranges in self.hold_colors.items():
            color_mask = np.zeros((height, width), dtype=np.uint8)
            
            # Combine all ranges for this color
            for lower, upper in ranges:
                mask = cv2.inRange(hsv_img, lower, upper)
                color_mask = cv2.bitwise_or(color_mask, mask)
            
            # Clean up individual color mask
            color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_OPEN, self.noise_kernel)
            color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_CLOSE, self.cleanup_kernel)
            
            # Add to combined mask
            combined_mask = cv2.bitwise_or(combined_mask, color_mask)
            
            # Add color to debug image
            if color_name == 'red':
                color_debug[color_mask > 0] = [0, 0, 255]
            elif color_name == 'green':
                color_debug[color_mask > 0] = [0, 255, 0]
            elif color_name == 'blue':
                color_debug[color_mask > 0] = [255, 0, 0]
            elif color_name == 'yellow':
                color_debug[color_mask > 0] = [0, 255, 255]
            elif color_name == 'purple':
                color_debug[color_mask > 0] = [255, 0, 255]
            elif color_name == 'orange':
                color_debug[color_mask > 0] = [0, 165, 255]
            elif color_name == 'white':
                color_debug[color_mask > 0] = [255, 255, 255]
            elif color_name == 'black':
                color_debug[color_mask > 0] = [128, 128, 128]  # Gray for visibility
            elif color_name == 'pink':
                color_debug[color_mask > 0] = [147, 20, 255]
        
        return combined_mask, color_debug

    def _create_hold_mask(self, img: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Create hold mask using color ranges and edge detection."""
        # Convert to HSV for color detection
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Get color-based mask
        color_mask, color_debug = self._create_color_masks(hsv)
        
        # Get edge-based mask from the original image (not just color-matched regions)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.bilateralFilter(gray, 9, 75, 75)
        edges = cv2.Canny(blurred, self.edge_threshold1, self.edge_threshold2)
        
        # Dilate edges to connect nearby edges
        dilated = cv2.dilate(edges, self.noise_kernel, iterations=3)  # More dilation to connect edges
        
        # Find contours from edges
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Create edge mask
        edge_mask = np.zeros_like(gray)
        hold_regions = np.zeros_like(gray)  # Mask for entire hold regions
        
        # Filter and draw contours based on area and shape
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.min_hold_size:
                # Calculate contour properties
                perimeter = cv2.arcLength(contour, True)
                if perimeter > 0:
                    circularity = 4 * np.pi * area / (perimeter * perimeter)
                    
                    # More lenient circularity check
                    if 0.05 < circularity < 0.95:
                        # If the contour contains enough colored pixels, consider it a hold
                        contour_mask = np.zeros_like(gray)
                        cv2.drawContours(contour_mask, [contour], -1, 255, -1)
                        color_overlap = cv2.bitwise_and(contour_mask, color_mask)
                        if np.sum(color_overlap) > area * 0.1:  # Only 10% colored required
                            # Expand the contour slightly to catch edge pixels
                            expanded_contour = cv2.dilate(contour_mask, self.cleanup_kernel, iterations=1)
                            cv2.drawContours(edge_mask, [contour], -1, 255, -1)
                            cv2.drawContours(hold_regions, [contour], -1, 255, -1)
                            # Add the expanded area to hold regions
                            hold_regions = cv2.bitwise_or(hold_regions, expanded_contour)
        
        # Find white/bright areas within hold regions
        _, white_mask = cv2.threshold(hsv[..., 2], 180, 255, cv2.THRESH_BINARY)  # More lenient white threshold
        white_in_holds = cv2.bitwise_and(white_mask, hold_regions)
        
        # Combine color mask with hold regions
        color_in_holds = cv2.bitwise_and(color_mask, hold_regions)
        
        # Final mask combines colored areas and white areas within hold regions
        final_mask = cv2.bitwise_or(color_in_holds, white_in_holds)
        
        # Clean up the final mask
        final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_CLOSE, self.cleanup_kernel, iterations=2)
        final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_OPEN, self.noise_kernel)
        
        return final_mask, color_debug

    async def remove_background(self, image_data: bytes, filename: str, cancel_token: Optional[asyncio.Event] = None) -> dict:
        """
        Remove background while preserving colored holds using dominant color detection.
        
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
        """Synchronous version of background removal and hold isolation."""
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if cancel_token and cancel_token.is_set():
            return {"base64_image": "", "file_path": ""}

        # Create hold mask using color and edge detection
        hold_mask, color_debug = self._create_hold_mask(img)
        
        # Generate timestamp for unique filenames
        timestamp = datetime.now().strftime("%B-%d-%Y_%I-%M-%S%p")
        base_filename = os.path.splitext(filename)[0]
        
        # Save debug masks with timestamps
        debug_filename_holds = f"Images/debug_holds_{base_filename}_{timestamp}.png"
        debug_filename_colors = f"Images/debug_colors_{base_filename}_{timestamp}.png"
        debug_filename_edges = f"Images/debug_edges_{base_filename}_{timestamp}.png"
        
        # Create edge visualization
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.bilateralFilter(gray, 9, 75, 75)
        edges = cv2.Canny(blurred, self.edge_threshold1, self.edge_threshold2)
        
        cv2.imwrite(debug_filename_holds, hold_mask)
        cv2.imwrite(debug_filename_colors, color_debug)
        cv2.imwrite(debug_filename_edges, edges)
        
        logger.info(f"Saved debug files:\n"
                   f"Hold mask: {debug_filename_holds}\n"
                   f"Color detection: {debug_filename_colors}\n"
                   f"Edge detection: {debug_filename_edges}")
        
        if cancel_token and cancel_token.is_set():
            return {"base64_image": "", "file_path": ""}
        
        # Create RGBA image (4 channels - RGB + Alpha)
        rgba = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
        
        # Set alpha channel based on mask (255 for holds, 0 for everything else)
        rgba[:, :, 3] = hold_mask
        
        # Create final output filename with timestamp
        new_filename = f"{timestamp}_{base_filename}_holds.png"
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
