from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import Dict, List, Optional, Any
from services.image_processor import ImageProcessor
from utils.logger import logger
import io
import platform
import psutil
import os
from datetime import datetime

router = APIRouter()
image_processor = ImageProcessor()

@router.post("/upload")
async def upload_image(file: UploadFile = File(...)) -> Dict[str, str]:
    """
    Upload an image file.
    
    Args:
        file: The image file to upload
        
    Returns:
        Dict containing the filename and a success message
    """
    logger.info(f"Received image upload request: {file.filename}")
    if not file.content_type.startswith('image/'):
        logger.error(f"Invalid file type received: {file.content_type}")
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # TODO: Implement image processing logic
    logger.info(f"Successfully processed image: {file.filename}")
    return {
        "filename": file.filename,
        "message": "Image uploaded successfully"
    }

@router.post("/identify-route")
async def identify_route(
    file: UploadFile = File(...),
    color: str = Form(...)
) -> Dict[str, Any]:
    """
    Identify climbing holds of a specific color in the uploaded image.
    
    Args:
        file: The image file to process
        color: The color of holds to identify
        
    Returns:
        Dict containing the identified holds and their positions
    """
    logger.info(f"Received route identification request - Color: {color}, File: {file.filename}")
    
    if not file.content_type.startswith('image/'):
        logger.error(f"Invalid file type received: {file.content_type}")
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Read the image data
        contents = await file.read()
        result = image_processor.get_route_by_color(contents, color.lower())
        logger.info(f"Successfully identified {len(result.get('holds', []))} holds of color {color}")
        return result
    except ValueError as e:
        logger.error(f"Invalid color parameter: {color}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint that provides system information and service status.
    
    Returns:
        Dict containing system information and service status
    """
    logger.info("Health check request received")
    
    # Get system information
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Get process information
    process = psutil.Process(os.getpid())
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
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