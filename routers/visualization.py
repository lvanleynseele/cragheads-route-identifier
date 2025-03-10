from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Request, BackgroundTasks
from typing import Dict, List, Any
from services.image_processor import ImageProcessor
from services.visualization_service import VisualizationService
from utils.logger import logger
import base64
import os
from datetime import datetime
import asyncio
import time

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
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    color: str = Form(...)
) -> Dict[str, Any]:
    """
    Create a visualization of climbing holds of a specific color.
    
    Args:
        request: FastAPI request object for cancellation handling
        background_tasks: BackgroundTasks for cleanup
        file: The image file to process
        color: The color of holds to visualize
        
    Returns:
        Dict containing the identified holds and visualization
    """
    start_time = time.time()
    logger.info(f"Received route visualization request - Color: {color}, File: {file.filename}")
    
    if not file.content_type.startswith('image/'):
        logger.error(f"Invalid file type received: {file.content_type}")
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Create cancellation token
        cancel_token = asyncio.Event()
        
        # Add cleanup to background tasks
        async def cleanup():
            if not cancel_token.is_set():
                cancel_token.set()
                duration = time.time() - start_time
                logger.info(f"Request cancelled after {duration:.2f} seconds")
        
        background_tasks.add_task(cleanup)
        
        # Read the image data
        contents = await file.read()
        
        # Process the image with cancellation check
        async def process_with_cancel():
            try:
                # Check if already disconnected
                if await request.is_disconnected():
                    duration = time.time() - start_time
                    logger.info(f"Client already disconnected after {duration:.2f} seconds")
                    cancel_token.set()
                    raise HTTPException(status_code=499, detail="Client disconnected")
                
                # Identify holds
                holds_result = await image_processor.get_route_by_color(contents, color.lower(), cancel_token)
                
                if await request.is_disconnected():
                    duration = time.time() - start_time
                    logger.info(f"Client disconnected during processing after {duration:.2f} seconds")
                    cancel_token.set()
                    raise HTTPException(status_code=499, detail="Client disconnected")
                
                # Create visualization
                visualization = await visualization_service.create_hold_visualization(
                    contents,
                    holds_result['holds'],
                    color.lower(),
                    cancel_token
                )
                
                if await request.is_disconnected():
                    duration = time.time() - start_time
                    logger.info(f"Client disconnected during processing after {duration:.2f} seconds")
                    cancel_token.set()
                    raise HTTPException(status_code=499, detail="Client disconnected")
                
                # Create overlay visualization
                overlay = await visualization_service.create_overlay_visualization(
                    contents,
                    holds_result['holds'],
                    color.lower(),
                    cancel_token
                )
                
                result = {
                    **holds_result,
                    'visualization': visualization,
                    'overlay': overlay
                }
                
                duration = time.time() - start_time
                logger.info(f"Successfully created visualization for {len(holds_result['holds'])} holds of color {color} in {duration:.2f} seconds")
                return result
                
            except asyncio.CancelledError:
                duration = time.time() - start_time
                logger.info(f"Processing cancelled after {duration:.2f} seconds")
                cancel_token.set()
                raise HTTPException(status_code=499, detail="Request cancelled")
            except ValueError as e:
                duration = time.time() - start_time
                logger.error(f"Invalid color parameter after {duration:.2f} seconds: {color}")
                raise HTTPException(status_code=400, detail=str(e))
        
        return await process_with_cancel()
    
    except asyncio.CancelledError:
        duration = time.time() - start_time
        logger.info(f"Request cancelled after {duration:.2f} seconds")
        cancel_token.set()
        raise HTTPException(status_code=499, detail="Request cancelled")
    except ValueError as e:
        duration = time.time() - start_time
        logger.error(f"Invalid color parameter after {duration:.2f} seconds: {color}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Error creating visualization after {duration:.2f} seconds: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating visualization: {str(e)}")

@router.post("/visualize-all-routes")
async def visualize_all_routes(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
) -> Dict[str, Any]:
    """
    Create a visualization of all climbing holds in the image.
    
    Args:
        request: FastAPI request object for cancellation handling
        background_tasks: BackgroundTasks for cleanup
        file: The image file to process
        
    Returns:
        Dict containing all identified holds and visualizations
    """
    start_time = time.time()
    logger.info(f"Received all-routes visualization request - File: {file.filename}")
    
    if not file.content_type.startswith('image/'):
        logger.error(f"Invalid file type received: {file.content_type}")
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Create cancellation token
        cancel_token = asyncio.Event()
        
        # Add cleanup to background tasks
        async def cleanup():
            if not cancel_token.is_set():
                cancel_token.set()
                duration = time.time() - start_time
                logger.info(f"Request cancelled after {duration:.2f} seconds")
        
        background_tasks.add_task(cleanup)
        
        # Read the image data
        contents = await file.read()
        
        # Process the image with cancellation check
        async def process_with_cancel():
            try:
                # Check if already disconnected
                if await request.is_disconnected():
                    duration = time.time() - start_time
                    logger.info(f"Client already disconnected after {duration:.2f} seconds")
                    cancel_token.set()
                    raise HTTPException(status_code=499, detail="Client disconnected")
                
                # Identify all holds
                holds_by_color = await image_processor.identify_all_routes(contents, cancel_token)
                
                if await request.is_disconnected():
                    duration = time.time() - start_time
                    logger.info(f"Client disconnected during processing after {duration:.2f} seconds")
                    cancel_token.set()
                    raise HTTPException(status_code=499, detail="Client disconnected")
                
                # Create visualizations for each color
                visualizations = {}
                overlays = {}
                
                for color, holds in holds_by_color.items():
                    if await request.is_disconnected():
                        duration = time.time() - start_time
                        logger.info(f"Client disconnected during processing after {duration:.2f} seconds")
                        cancel_token.set()
                        raise HTTPException(status_code=499, detail="Client disconnected")
                    
                    visualizations[color] = await visualization_service.create_hold_visualization(
                        contents,
                        holds,
                        color,
                        cancel_token
                    )
                    
                    if await request.is_disconnected():
                        duration = time.time() - start_time
                        logger.info(f"Client disconnected during processing after {duration:.2f} seconds")
                        cancel_token.set()
                        raise HTTPException(status_code=499, detail="Client disconnected")
                    
                    overlays[color] = await visualization_service.create_overlay_visualization(
                        contents,
                        holds,
                        color,
                        cancel_token
                    )
                
                result = {
                    'holds': holds_by_color,
                    'visualizations': visualizations,
                    'overlays': overlays
                }
                
                # Log the number of holds found for each color
                duration = time.time() - start_time
                for color, holds in holds_by_color.items():
                    logger.info(f"Created visualization for {len(holds)} holds of color {color} in {duration:.2f} seconds")
                
                return result
                
            except asyncio.CancelledError:
                duration = time.time() - start_time
                logger.info(f"Processing cancelled after {duration:.2f} seconds")
                cancel_token.set()
                raise HTTPException(status_code=499, detail="Request cancelled")
        
        return await process_with_cancel()
    
    except asyncio.CancelledError:
        duration = time.time() - start_time
        logger.info(f"Request cancelled after {duration:.2f} seconds")
        cancel_token.set()
        raise HTTPException(status_code=499, detail="Request cancelled")
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Error creating visualization after {duration:.2f} seconds: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating visualization: {str(e)}") 