from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import Dict, List, Any
from services.image_processor import ImageProcessor
from services.visualization_service import VisualizationService
from utils.logger import logger
import base64
import os
from datetime import datetime

router = APIRouter()
image_processor = ImageProcessor()
visualization_service = VisualizationService()

def save_visualization(base64_string: str, prefix: str = "visualization") -> str:
    """
    Save a base64-encoded image string to a PNG file with timestamp.
    
    Args:
        base64_string: The base64-encoded image string
        prefix: Prefix for the filename
        
    Returns:
        The path to the saved file
    """
    # Create visualizations directory if it doesn't exist
    os.makedirs("visualizations", exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"visualizations/{prefix}_{timestamp}.png"
    
    try:
        # Decode and save the image
        with open(filename, 'wb') as f:
            f.write(base64.b64decode(base64_string))
        logger.info(f"Visualization saved as '{filename}'")
        return filename
    except Exception as e:
        logger.error(f"Error saving visualization: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving visualization: {str(e)}")

@router.post("/visualize-route")
async def visualize_route(
    file: UploadFile = File(...),
    color: str = Form(...),
    overlay: bool = Form(False)
) -> str:
    """
    Identify and visualize climbing holds of a specific color in the uploaded image.
    
    Args:
        file: The image file to process
        color: The color of holds to identify
        overlay: Whether to overlay the holds on the original image
        
    Returns:
        Base64 encoded image string of the visualization
    """
    logger.info(f"Received route visualization request - Color: {color}, File: {file.filename}")
    
    if not file.content_type.startswith('image/'):
        logger.error(f"Invalid file type received: {file.content_type}")
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Read the image data
        contents = await file.read()
        result = image_processor.get_route_by_color(contents, color.lower())
        
        # Create visualization
        holds_by_color = {color: result.get('holds', [])}
        if overlay:
            visualization = visualization_service.create_overlay_visualization(contents, holds_by_color)
        else:
            visualization = visualization_service.create_hold_visualization(contents, holds_by_color)
        
        # Save the visualization
        filename = save_visualization(visualization, f"route_{color}")
        
        logger.info(f"Successfully identified and visualized {len(result.get('holds', []))} holds of color {color}")
        return visualization
    except ValueError as e:
        logger.error(f"Invalid color parameter: {color}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

@router.post("/visualize-all-routes")
async def visualize_all_routes(
    file: UploadFile = File(...),
    overlay: bool = Form(False)
) -> str:
    """
    Identify and visualize all climbing holds in the image, grouped by color.
    
    Args:
        file: The image file to process
        overlay: Whether to overlay the holds on the original image
        
    Returns:
        Base64 encoded image string of the visualization
    """
    logger.info(f"Received all-routes visualization request - File: {file.filename}")
    
    if not file.content_type.startswith('image/'):
        logger.error(f"Invalid file type received: {file.content_type}")
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Read the image data
        contents = await file.read()
        results = image_processor.identify_all_routes(contents)
        
        # Create visualization
        if overlay:
            visualization = visualization_service.create_overlay_visualization(contents, results)
        else:
            visualization = visualization_service.create_hold_visualization(contents, results)
        
        # Save the visualization
        filename = save_visualization(visualization, "all_routes")
        
        # Log the number of holds found for each color
        for color, holds in results.items():
            logger.info(f"Identified {len(holds)} holds of color {color}")
        
        return visualization
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}") 