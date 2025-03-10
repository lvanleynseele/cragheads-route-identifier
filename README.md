# Image Processing Service

A Python service for processing images using computer vision, specifically designed for identifying climbing routes in climbing gyms.

## Setup

### Option 1: Using Startup Scripts (Recommended)

#### On Unix-like systems (Linux, macOS):

```bash
chmod +x start.sh
./start.sh
```

#### On Windows:

```bash
start.bat
```

The startup scripts will:

1. Check if Python is installed
2. Create a virtual environment if it doesn't exist
3. Install/upgrade pip
4. Install all required dependencies
5. Create necessary directories
6. Start the service

### Option 2: Manual Setup

1. Create a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the Service

### Using Startup Scripts

Just run the appropriate startup script for your operating system as described in the Setup section.

### Manual Start

To run the service on port 3020:

```bash
uvicorn main:app --host 0.0.0.0 --port 3020 --reload
```

The service will be available at `http://localhost:3020`

## Logging

The service includes comprehensive logging:

- Logs are stored in the `logs` directory
- Each session creates a new log file with timestamp
- Logs include:
  - API request details
  - Image processing information
  - Error messages
  - Health check requests

Log files are named in the format: `app_YYYYMMDD_HHMMSS.log`

## API Endpoints

### Image Processing Endpoints
- `GET /`: Welcome message
- `GET /api/v1/health`: Health check endpoint with system information
- `POST /api/v1/upload`: Upload an image file
- `POST /api/v1/identify-route`: Identify climbing holds of a specific color in an image
- `POST /api/v1/identify-all-routes`: Identify all climbing holds in an image, grouped by color

### Visualization Endpoints
- `POST /api/v1/visualize-route`: Identify and visualize holds of a specific color
- `POST /api/v1/visualize-all-routes`: Identify and visualize all holds

## Health Check

The `/api/v1/health` endpoint provides comprehensive system and service information:

```json
{
  "status": "healthy",
  "timestamp": "2024-02-20T14:30:22.123456",
  "system": {
    "platform": "macOS-13.4-arm64-arm-64bit",
    "python_version": "3.9.7",
    "cpu_percent": 25.6,
    "memory": {
      "total": 17179869184,
      "available": 8589934592,
      "percent": 50.0
    },
    "disk": {
      "total": 500000000000,
      "used": 250000000000,
      "free": 250000000000,
      "percent": 50.0
    }
  },
  "service": {
    "pid": 12345,
    "memory_percent": 1.2,
    "cpu_percent": 0.5,
    "threads": 4
  }
}
```

## Route Identification

### Basic Route Identification
The `/api/v1/identify-route` endpoint accepts:
- An image file
- A color parameter (supported colors: red, blue, green, yellow, purple, orange, pink, white, black)

The endpoint returns:
- The identified color
- A list of holds with their positions (x, y coordinates) and sizes

Example response:
```json
{
  "color": "red",
  "holds": [
    {
      "position": {
        "x": 100,
        "y": 200
      },
      "size": {
        "width": 30,
        "height": 30
      }
    }
  ]
}
```

### All Routes Identification
The `/api/v1/identify-all-routes` endpoint accepts:
- An image file

The endpoint returns:
- A dictionary of all identified holds, grouped by color

Example response:
```json
{
  "holds": {
    "red": [
      {
        "position": {
          "x": 100,
          "y": 200
        },
        "size": {
          "width": 30,
          "height": 30
        }
      }
    ],
    "blue": [
      {
        "position": {
          "x": 150,
          "y": 250
        },
        "size": {
          "width": 25,
          "height": 25
        }
      }
    ]
  }
}
```

## Route Visualization

### Single Color Route Visualization
The `/api/v1/visualize-route` endpoint accepts:
- An image file
- A color parameter (supported colors: red, blue, green, yellow, purple, orange, pink, white, black)
- An overlay parameter (boolean, defaults to false)

The endpoint returns:
- The identified color
- A list of holds with their positions and sizes
- A base64-encoded visualization of the holds

Example response:
```json
{
  "color": "red",
  "holds": [
    {
      "position": {
        "x": 100,
        "y": 200
      },
      "size": {
        "width": 30,
        "height": 30
      }
    }
  ],
  "visualization": "base64_encoded_image_data..."
}
```

### All Routes Visualization
The `/api/v1/visualize-all-routes` endpoint accepts:
- An image file
- An overlay parameter (boolean, defaults to false)

The endpoint returns:
- A dictionary of all identified holds, grouped by color
- A base64-encoded visualization of all holds

Example response:
```json
{
  "holds": {
    "red": [
      {
        "position": {
          "x": 100,
          "y": 200
        },
        "size": {
          "width": 30,
          "height": 30
        }
      }
    ],
    "blue": [
      {
        "position": {
          "x": 150,
          "y": 250
        },
        "size": {
          "width": 25,
          "height": 25
        }
      }
    ]
  },
  "visualization": "base64_encoded_image_data..."
}
```

## Visualization Options

The visualization endpoints support two visualization styles:

1. Hold-only visualization (default):
   - Black background
   - Colored rectangles for each hold
   - White outlines around holds
   - Maintains original image dimensions

2. Overlay visualization (when overlay=true):
   - Original image as background
   - Semi-transparent colored rectangles for holds
   - Solid colored outlines around holds
   - Perfect alignment with original image

To view the visualization:
1. Decode the base64 string from the response
2. Save it as a PNG file
3. Open it with any image viewer

Example Python code to save the visualization:
```python
import base64

# Assuming 'response' is the API response
visualization_data = response['visualization']
with open('visualization.png', 'wb') as f:
    f.write(base64.b64decode(visualization_data))
```

## Making API Calls with Postman

### Basic Route Identification
1. Create a new POST request to `http://localhost:3020/api/v1/identify-route`
2. In the request body:
   - Select "form-data"
   - Add two key-value pairs:
     - Key: `file` (Important: Click the dropdown on the right of the key field and select "File")
       - Value: Select your image file
     - Key: `color`
       - Value: Enter the color you want to identify (e.g., "red", "blue", etc.)

### All Routes Identification
1. Create a new POST request to `http://localhost:3020/api/v1/identify-all-routes`
2. In the request body:
   - Select "form-data"
   - Add one key-value pair:
     - Key: `file` (Important: Click the dropdown on the right of the key field and select "File")
       - Value: Select your image file

### Route Visualization
1. Create a new POST request to `http://localhost:3020/api/v1/visualize-route`
2. In the request body:
   - Select "form-data"
   - Add three key-value pairs:
     - Key: `file` (Important: Click the dropdown on the right of the key field and select "File")
       - Value: Select your image file
     - Key: `color`
       - Value: Enter the color you want to identify
     - Key: `overlay`
       - Value: true or false (optional, defaults to false)

### All Routes Visualization
1. Create a new POST request to `http://localhost:3020/api/v1/visualize-all-routes`
2. In the request body:
   - Select "form-data"
   - Add two key-value pairs:
     - Key: `file` (Important: Click the dropdown on the right of the key field and select "File")
       - Value: Select your image file
     - Key: `overlay`
       - Value: true or false (optional, defaults to false)

## API Documentation

Once the service is running, you can access:

- Swagger UI documentation at `http://localhost:3020/docs`
- ReDoc documentation at `http://localhost:3020/redoc`
