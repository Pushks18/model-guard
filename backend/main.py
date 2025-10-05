"""
FastAPI backend for ModelGuard
"""
import os
import tempfile
import time
from typing import Dict
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models import ValidationReport, HealthResponse
from .validator import MeshValidator

# Initialize FastAPI app
app = FastAPI(
    title="ModelGuard API",
    description="3D Model Validation Service for Dental Models",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize validator
validator = MeshValidator()

# In-memory storage for reports (use database in production)
reports_storage: Dict[str, ValidationReport] = {}

# Track uptime
start_time = time.time()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        uptime_seconds=time.time() - start_time
    )


@app.post("/validate", response_model=ValidationReport)
async def validate_model(file: UploadFile = File(...)):
    """
    Validate a 3D model file
    
    Args:
        file: Uploaded 3D model file (STL, OBJ, PLY)
        
    Returns:
        Validation report with errors, warnings, and decision
    """
    # Validate file type
    allowed_extensions = {'.stl', '.obj', '.ply'}
    file_extension = os.path.splitext(file.filename)[1].lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Check file size (100MB limit)
    max_size = 100 * 1024 * 1024  # 100MB
    if file.size and file.size > max_size:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum size: 100MB"
        )
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_file_path = tmp_file.name
    
    try:
        # Validate the mesh
        report = validator.validate_mesh(tmp_file_path, file.filename)
        
        # Store report in memory
        reports_storage[report.model_id] = report
        
        return report
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Validation failed: {str(e)}"
        )
    
    finally:
        # Clean up temporary file
        try:
            os.unlink(tmp_file_path)
        except OSError:
            pass


@app.get("/report/{model_id}", response_model=ValidationReport)
async def get_report(model_id: str):
    """
    Retrieve a validation report by model ID
    
    Args:
        model_id: Unique model identifier
        
    Returns:
        Validation report
    """
    if model_id not in reports_storage:
        raise HTTPException(
            status_code=404,
            detail="Report not found"
        )
    
    return reports_storage[model_id]


@app.get("/reports")
async def list_reports():
    """List all validation reports"""
    return {
        "reports": [
            {
                "model_id": report.model_id,
                "filename": report.filename,
                "decision": report.decision,
                "timestamp": report.timestamp
            }
            for report in reports_storage.values()
        ]
    }


@app.delete("/report/{model_id}")
async def delete_report(model_id: str):
    """Delete a validation report"""
    if model_id not in reports_storage:
        raise HTTPException(
            status_code=404,
            detail="Report not found"
        )
    
    del reports_storage[model_id]
    return {"message": "Report deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    import os
    
    # Get port from environment (GCP Cloud Run sets PORT env var)
    port = int(os.environ.get("PORT", 8000))
    
    uvicorn.run(app, host="0.0.0.0", port=port)
