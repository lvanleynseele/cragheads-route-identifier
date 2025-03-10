from fastapi import APIRouter, UploadFile, File, HTTPException, Request, BackgroundTasks
from services.background_removal_service import BackgroundRemovalService
from utils.logger import logger
import asyncio
from typing import Dict
import time

router = APIRouter()
background_service = BackgroundRemovalService()

@router.post("/remove-background")
async def remove_background(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
) -> Dict[str, str]:
    """
    Remove the background from an uploaded image.
    
    Args:
        request: FastAPI request object for cancellation handling
        background_tasks: BackgroundTasks for cleanup
        file: The image file to process
        
    Returns:
        Dictionary containing the base64 encoded image and the saved file path
    """
    start_time = time.time()
    logger.info(f"Received background removal request - File: {file.filename}")
    
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
                
                # Process the image
                result = await background_service.remove_background(contents, file.filename, cancel_token)
                
                # Check again after processing
                if await request.is_disconnected():
                    duration = time.time() - start_time
                    logger.info(f"Client disconnected during processing after {duration:.2f} seconds")
                    cancel_token.set()
                    raise HTTPException(status_code=499, detail="Client disconnected")
                
                duration = time.time() - start_time
                logger.info(f"Successfully removed background from image: {file.filename} in {duration:.2f} seconds")
                logger.info(f"Saved processed image to: {result['file_path']}")
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
        logger.error(f"Error removing background after {duration:.2f} seconds: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error removing background: {str(e)}") 