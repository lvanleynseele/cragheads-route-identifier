from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Request, BackgroundTasks
from typing import Dict, List, Optional, Any
from services.image_processor import ImageProcessor
from utils.logger import logger
import io
import platform
import psutil
import os
from datetime import datetime
import asyncio
import time

router = APIRouter()
image_processor = ImageProcessor()

@router.post("/upload")
async def upload_image(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
) -> Dict[str, str]:
    """
    Upload an image file.
    
    Args:
        request: FastAPI request object for cancellation handling
        background_tasks: BackgroundTasks for cleanup
        file: The image file to upload
        
    Returns:
        Dict containing the filename and a success message
    """
    start_time = time.time()
    logger.info(f"Received image upload request: {file.filename}")
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
        
        # Process the upload with cancellation check
        async def process_with_cancel():
            try:
                # Check if already disconnected
                if await request.is_disconnected():
                    duration = time.time() - start_time
                    logger.info(f"Client already disconnected after {duration:.2f} seconds")
                    cancel_token.set()
                    raise HTTPException(status_code=499, detail="Client disconnected")
                
                # TODO: Implement image processing logic
                duration = time.time() - start_time
                logger.info(f"Successfully processed image: {file.filename} in {duration:.2f} seconds")
                return {
                    "filename": file.filename,
                    "message": "Image uploaded successfully"
                }
                
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
        logger.error(f"Error processing upload after {duration:.2f} seconds: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing upload: {str(e)}")

@router.post("/identify-route")
async def identify_route(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    color: str = Form(...)
) -> Dict[str, Any]:
    """
    Identify climbing holds of a specific color in the uploaded image.
    
    Args:
        request: FastAPI request object for cancellation handling
        background_tasks: BackgroundTasks for cleanup
        file: The image file to process
        color: The color of holds to identify
        
    Returns:
        Dict containing the identified holds and their positions
    """
    start_time = time.time()
    logger.info(f"Received route identification request - Color: {color}, File: {file.filename}")
    
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
                
                result = await image_processor.get_route_by_color(contents, color.lower(), cancel_token)
                
                if await request.is_disconnected():
                    duration = time.time() - start_time
                    logger.info(f"Client disconnected during processing after {duration:.2f} seconds")
                    cancel_token.set()
                    raise HTTPException(status_code=499, detail="Client disconnected")
                
                duration = time.time() - start_time
                logger.info(f"Successfully identified {len(result.get('holds', []))} holds of color {color} in {duration:.2f} seconds")
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
        logger.error(f"Error processing image after {duration:.2f} seconds: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

@router.post("/identify-all-routes")
async def identify_all_routes(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Identify all climbing holds in the image, grouped by color.
    
    Args:
        request: FastAPI request object for cancellation handling
        background_tasks: BackgroundTasks for cleanup
        file: The image file to process
        
    Returns:
        Dictionary containing all identified holds grouped by color
    """
    start_time = time.time()
    logger.info(f"Received all-routes identification request - File: {file.filename}")
    
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
                
                results = await image_processor.identify_all_routes(contents, cancel_token)
                
                if await request.is_disconnected():
                    duration = time.time() - start_time
                    logger.info(f"Client disconnected during processing after {duration:.2f} seconds")
                    cancel_token.set()
                    raise HTTPException(status_code=499, detail="Client disconnected")
                
                # Log the number of holds found for each color
                duration = time.time() - start_time
                for color, holds in results.items():
                    logger.info(f"Identified {len(holds)} holds of color {color} in {duration:.2f} seconds")
                
                return results
                
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
        logger.error(f"Error processing image after {duration:.2f} seconds: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint that provides system information and service status.
    
    Returns:
        Dict containing system information and service status
    """
    start_time = time.time()
    logger.info("Health check request received")
    
    # Get system information
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Get process information
    process = psutil.Process(os.getpid())
    
    duration = time.time() - start_time
    logger.info(f"Health check completed in {duration:.2f} seconds")
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "duration": f"{duration:.2f}s",
        "system": {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_percent": cpu_percent,
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            }
        },
        "service": {
            "pid": process.pid,
            "memory_percent": process.memory_percent(),
            "cpu_percent": process.cpu_percent(),
            "threads": process.num_threads()
        }
    } 