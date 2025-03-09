import cv2
import numpy as np
from typing import List, Dict, Any
import base64

class VisualizationService:
    def __init__(self):
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

    def create_hold_visualization(self, image_data: bytes, holds_by_color: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Create a visualization of the identified holds.
        
        Args:
            image_data: Original image data
            holds_by_color: Dictionary of holds grouped by color
            
        Returns:
            Base64 encoded image of the visualization
        """
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Create a black background
        height, width = img.shape[:2]
        visualization = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Draw each hold in its identified color
        for color, holds in holds_by_color.items():
            for hold in holds:
                # Use the hold's actual color if available, otherwise use the predefined color
                hold_color = tuple(int(c) for c in hold.get('color', self.visualization_colors[color]))
                
                # Get the contour points
                contour = np.array(hold['contour'], dtype=np.int32)
                
                # Create a mask for the contour
                mask = np.zeros((height, width), dtype=np.uint8)
                cv2.drawContours(mask, [contour], -1, 255, -1)
                
                # Fill the contour with the hold's color
                visualization[mask == 255] = hold_color
                
                # Draw outline
                cv2.drawContours(visualization, [contour], -1, (255, 255, 255), 2)
        
        # Convert the visualization to base64
        _, buffer = cv2.imencode('.png', visualization)
        return base64.b64encode(buffer).decode('utf-8')

    def create_overlay_visualization(self, image_data: bytes, holds_by_color: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Create a visualization of the identified holds overlaid on the original image.
        
        Args:
            image_data: Original image data
            holds_by_color: Dictionary of holds grouped by color
            
        Returns:
            Base64 encoded image of the visualization
        """
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Create a copy of the original image
        visualization = img.copy()
        
        # Draw each hold in its identified color
        for color, holds in holds_by_color.items():
            for hold in holds:
                # Use the hold's actual color if available, otherwise use the predefined color
                hold_color = tuple(int(c) for c in hold.get('color', self.visualization_colors[color]))
                
                # Get the contour points
                contour = np.array(hold['contour'], dtype=np.int32)
                
                # Create a mask for the contour
                mask = np.zeros_like(visualization)
                cv2.drawContours(mask, [contour], -1, hold_color, -1)
                
                # Apply transparency
                cv2.addWeighted(mask, 0.3, visualization, 0.7, 0, visualization)
                
                # Draw outline
                cv2.drawContours(visualization, [contour], -1, hold_color, 2)
        
        # Convert the visualization to base64
        _, buffer = cv2.imencode('.png', visualization)
        return base64.b64encode(buffer).decode('utf-8') 