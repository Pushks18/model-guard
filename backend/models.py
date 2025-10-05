"""
Pydantic models for ModelGuard API
"""
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum


class ValidationStatus(str, Enum):
    """Validation decision status"""
    ALLOW = "ALLOW"
    ALLOW_WITH_WARNINGS = "ALLOW_WITH_WARNINGS"
    BLOCK = "BLOCK"


class ErrorCode(str, Enum):
    """Error codes for validation issues"""
    NOT_WATERTIGHT = "NOT_WATERTIGHT"
    NON_MANIFOLD = "NON_MANIFOLD"
    SELF_INTERSECTING = "SELF_INTERSECTING"
    THIN_WALL = "THIN_WALL"
    DEGENERATE_FACES = "DEGENERATE_FACES"
    DUPLICATE_VERTICES = "DUPLICATE_VERTICES"
    INVERTED_NORMALS = "INVERTED_NORMALS"
    MULTIPLE_COMPONENTS = "MULTIPLE_COMPONENTS"


class ValidationIssue(BaseModel):
    """Individual validation issue"""
    code: ErrorCode
    message: str
    severity: Literal["error", "warning"] = "error"
    count: Optional[int] = None
    locations: Optional[List[Dict[str, Any]]] = None


class MeshMetrics(BaseModel):
    """Mesh geometry metrics"""
    triangles: int
    vertices: int
    components: int
    bbox_mm: List[float] = Field(..., description="Bounding box [x, y, z] in mm")
    volume_mm3: Optional[float] = None
    surface_area_mm2: Optional[float] = None
    units: str = "mm"


class ValidationReport(BaseModel):
    """Complete validation report"""
    model_id: str
    filename: str
    metrics: MeshMetrics
    errors: List[ValidationIssue] = []
    warnings: List[ValidationIssue] = []
    decision: ValidationStatus
    processing_time_ms: float
    timestamp: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = "healthy"
    version: str = "1.0.0"
    uptime_seconds: float
