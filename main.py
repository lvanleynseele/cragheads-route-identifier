from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import images, visualization

app = FastAPI(
    title="Image Processing Service",
    description="A service for processing images using computer vision",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(images.router, prefix="/api/v1", tags=["images"])
app.include_router(visualization.router, prefix="/api/v1", tags=["visualization"])

@app.get("/")
async def root():
    return {"message": "Welcome to the Image Processing Service"} 