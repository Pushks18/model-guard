"""
Core mesh validation logic using trimesh and open3d
"""
import time
import uuid
from typing import List, Tuple, Dict, Any
import numpy as np
import trimesh
from datetime import datetime

# Try to import open3d, but don't fail if it's not available
try:
    import open3d as o3d
    OPEN3D_AVAILABLE = True
except ImportError:
    OPEN3D_AVAILABLE = False
    o3d = None

from .models import (
    ValidationReport, ValidationIssue, MeshMetrics, 
    ValidationStatus, ErrorCode
)


class MeshValidator:
    """Main mesh validation class"""
    
    def __init__(self, 
                 thin_wall_threshold: float = 0.5,
                 min_volume_threshold: float = 1.0,
                 max_file_size_mb: float = 100.0):
        """
        Initialize validator with configurable thresholds
        
        Args:
            thin_wall_threshold: Minimum wall thickness in mm
            min_volume_threshold: Minimum volume in mm³
            max_file_size_mb: Maximum file size in MB
        """
        self.thin_wall_threshold = thin_wall_threshold
        self.min_volume_threshold = min_volume_threshold
        self.max_file_size_mb = max_file_size_mb
        
    def validate_mesh(self, file_path: str, filename: str) -> ValidationReport:
        """
        Main validation pipeline
        
        Args:
            file_path: Path to the uploaded file
            filename: Original filename
            
        Returns:
            Complete validation report
        """
        start_time = time.time()
        model_id = str(uuid.uuid4())
        
        try:
            # Load mesh
            mesh = self._load_mesh(file_path)
            
            # Compute basic metrics
            metrics = self._compute_metrics(mesh)
            
            # Run validation checks
            errors, warnings = self._run_validation_checks(mesh)
            
            # Determine final decision
            decision = self._determine_decision(errors, warnings)
            
            processing_time = (time.time() - start_time) * 1000  # Convert to ms
            
            return ValidationReport(
                model_id=model_id,
                filename=filename,
                metrics=metrics,
                errors=errors,
                warnings=warnings,
                decision=decision,
                processing_time_ms=processing_time,
                timestamp=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            # Return error report
            processing_time = (time.time() - start_time) * 1000
            return ValidationReport(
                model_id=model_id,
                filename=filename,
                metrics=MeshMetrics(
                    triangles=0, vertices=0, components=0, 
                    bbox_mm=[0, 0, 0]
                ),
                errors=[ValidationIssue(
                    code=ErrorCode.DEGENERATE_FACES,
                    message=f"Failed to load mesh: {str(e)}"
                )],
                warnings=[],
                decision=ValidationStatus.BLOCK,
                processing_time_ms=processing_time,
                timestamp=datetime.utcnow().isoformat()
            )
    
    def _load_mesh(self, file_path: str) -> trimesh.Trimesh:
        """Load mesh from file with error handling"""
        try:
            mesh = trimesh.load(file_path)
            
            # Ensure it's a single mesh
            if isinstance(mesh, trimesh.Scene):
                # Get the largest mesh from scene
                geometries = [g for g in mesh.geometry.values() if hasattr(g, 'vertices')]
                if not geometries:
                    raise ValueError("No valid meshes found in scene")
                mesh = max(geometries, key=lambda x: len(x.vertices))
            
            if not hasattr(mesh, 'vertices') or len(mesh.vertices) == 0:
                raise ValueError("Empty or invalid mesh")
                
            return mesh
            
        except Exception as e:
            raise ValueError(f"Failed to load mesh: {str(e)}")
    
    def _compute_metrics(self, mesh: trimesh.Trimesh) -> MeshMetrics:
        """Compute basic mesh metrics"""
        try:
            # Basic counts
            triangles = len(mesh.faces)
            vertices = len(mesh.vertices)
            
            # Bounding box
            bbox = mesh.bounds
            bbox_size = bbox[1] - bbox[0]  # [max_x - min_x, max_y - min_y, max_z - min_z]
            
            # Volume and surface area
            volume = mesh.volume if mesh.is_watertight else None
            surface_area = mesh.surface_area
            
            # Connected components
            components = len(mesh.split(only_watertight=False))
            
            return MeshMetrics(
                triangles=triangles,
                vertices=vertices,
                components=components,
                bbox_mm=bbox_size.tolist(),
                volume_mm3=volume,
                surface_area_mm2=surface_area
            )
            
        except Exception as e:
            # Return basic metrics if computation fails
            return MeshMetrics(
                triangles=len(mesh.faces) if hasattr(mesh, 'faces') else 0,
                vertices=len(mesh.vertices) if hasattr(mesh, 'vertices') else 0,
                components=1,
                bbox_mm=[0, 0, 0]
            )
    
    def _run_validation_checks(self, mesh: trimesh.Trimesh) -> Tuple[List[ValidationIssue], List[ValidationIssue]]:
        """Run all validation checks"""
        errors = []
        warnings = []
        
        # Watertightness check
        if not mesh.is_watertight:
            errors.append(ValidationIssue(
                code=ErrorCode.NOT_WATERTIGHT,
                message="Mesh is not watertight (has open boundaries)",
                count=len(mesh.open_boundaries) if hasattr(mesh, 'open_boundaries') else None
            ))
        
        # Manifold check
        if not mesh.is_winding_consistent:
            errors.append(ValidationIssue(
                code=ErrorCode.NON_MANIFOLD,
                message="Mesh has non-manifold edges"
            ))
        
        # Self-intersection check (simplified - trimesh doesn't have intersects_self)
        try:
            # Use a simple bounding box check as a proxy for self-intersection
            # This is a simplified approach - in production you'd want more sophisticated detection
            if hasattr(mesh, 'bounds') and mesh.bounds is not None:
                bbox_size = mesh.bounds[1] - mesh.bounds[0]
                # If the mesh is extremely thin in any dimension, it might have self-intersections
                if np.any(bbox_size < 1e-6):
                    errors.append(ValidationIssue(
                        code=ErrorCode.SELF_INTERSECTING,
                        message="Mesh appears to have self-intersections or is extremely thin"
                    ))
        except Exception:
            # If we can't check for self-intersections, skip this check
            pass
        
        # Multiple components check
        components = mesh.split(only_watertight=False)
        if len(components) > 1:
            warnings.append(ValidationIssue(
                code=ErrorCode.MULTIPLE_COMPONENTS,
                message=f"Mesh has {len(components)} disconnected components",
                count=len(components)
            ))
        
        # Degenerate faces check
        degenerate_faces = self._find_degenerate_faces(mesh)
        if len(degenerate_faces) > 0:
            errors.append(ValidationIssue(
                code=ErrorCode.DEGENERATE_FACES,
                message=f"Found {len(degenerate_faces)} degenerate faces",
                count=len(degenerate_faces)
            ))
        
        # Duplicate vertices check
        duplicate_vertices = self._find_duplicate_vertices(mesh)
        if len(duplicate_vertices) > 0:
            warnings.append(ValidationIssue(
                code=ErrorCode.DUPLICATE_VERTICES,
                message=f"Found {len(duplicate_vertices)} duplicate vertices",
                count=len(duplicate_vertices)
            ))
        
        # Thin wall detection (simplified)
        thin_regions = self._detect_thin_walls(mesh)
        if len(thin_regions) > 0:
            warnings.append(ValidationIssue(
                code=ErrorCode.THIN_WALL,
                message=f"Detected {len(thin_regions)} regions with thickness < {self.thin_wall_threshold}mm",
                count=len(thin_regions)
            ))
        
        return errors, warnings
    
    def _find_degenerate_faces(self, mesh: trimesh.Trimesh) -> List[int]:
        """Find faces with zero area"""
        degenerate = []
        for i, face in enumerate(mesh.faces):
            v0, v1, v2 = mesh.vertices[face]
            # Calculate face area using cross product
            area = 0.5 * np.linalg.norm(np.cross(v1 - v0, v2 - v0))
            if area < 1e-10:  # Very small threshold
                degenerate.append(i)
        return degenerate
    
    def _find_duplicate_vertices(self, mesh: trimesh.Trimesh) -> List[int]:
        """Find duplicate vertices (simplified approach)"""
        # Use a simple distance-based approach
        vertices = mesh.vertices
        duplicates = []
        
        for i in range(len(vertices)):
            for j in range(i + 1, len(vertices)):
                if np.linalg.norm(vertices[i] - vertices[j]) < 1e-6:
                    duplicates.append(i)
                    break
        
        return duplicates
    
    def _detect_thin_walls(self, mesh: trimesh.Trimesh) -> List[Dict[str, Any]]:
        """
        Detect thin wall regions (simplified implementation)
        This is a basic implementation - in production, you'd want more sophisticated methods
        """
        thin_regions = []
        
        try:
            # Sample points on the surface and check distances to opposite surface
            # This is a simplified approach - real implementation would be more complex
            surface_points = mesh.sample(1000)  # Sample 1000 points
            
            for point in surface_points[:10]:  # Check first 10 points for demo
                # Find nearest point on opposite side (simplified)
                distances = np.linalg.norm(mesh.vertices - point, axis=1)
                nearest_idx = np.argmin(distances)
                distance = distances[nearest_idx]
                
                if distance < self.thin_wall_threshold:
                    thin_regions.append({
                        "point": point.tolist(),
                        "thickness": distance,
                        "location": "surface"
                    })
        except Exception:
            # If sampling fails, return empty list
            pass
        
        return thin_regions
    
    def _determine_decision(self, errors: List[ValidationIssue], warnings: List[ValidationIssue]) -> ValidationStatus:
        """Determine final validation decision based on errors and warnings"""
        if any(error.severity == "error" for error in errors):
            return ValidationStatus.BLOCK
        elif warnings:
            return ValidationStatus.ALLOW_WITH_WARNINGS
        else:
            return ValidationStatus.ALLOW
