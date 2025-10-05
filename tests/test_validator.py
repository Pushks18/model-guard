"""
Tests for ModelGuard validator
"""
import pytest
import numpy as np
import trimesh
import tempfile
import os
from backend.validator import MeshValidator
from backend.models import ValidationStatus, ErrorCode


class TestMeshValidator:
    """Test cases for MeshValidator"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.validator = MeshValidator()
    
    def create_test_cube(self, watertight=True):
        """Create a test cube mesh"""
        if watertight:
            return trimesh.creation.box(extents=[10, 10, 10])
        else:
            # Create a non-watertight cube by removing one face
            cube = trimesh.creation.box(extents=[10, 10, 10])
            # Remove the last face to make it non-watertight
            cube.faces = cube.faces[:-1]
            return cube
    
    def test_watertight_cube_validation(self):
        """Test validation of a watertight cube"""
        cube = self.create_test_cube(watertight=True)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as tmp:
            cube.export(tmp.name)
            
            try:
                report = self.validator.validate_mesh(tmp.name, 'test_cube.stl')
                
                # Should have no errors
                assert len(report.errors) == 0
                assert report.decision == ValidationStatus.ALLOW
                assert report.metrics.triangles == 12  # Cube has 12 triangles
                assert report.metrics.vertices == 8   # Cube has 8 vertices
                
            finally:
                os.unlink(tmp.name)
    
    def test_non_watertight_cube_validation(self):
        """Test validation of a non-watertight cube"""
        cube = self.create_test_cube(watertight=False)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as tmp:
            cube.export(tmp.name)
            
            try:
                report = self.validator.validate_mesh(tmp.name, 'test_cube.stl')
                
                # Should have watertight error
                assert len(report.errors) > 0
                assert any(error.code == ErrorCode.NOT_WATERTIGHT for error in report.errors)
                assert report.decision == ValidationStatus.BLOCK
                
            finally:
                os.unlink(tmp.name)
    
    def test_metrics_computation(self):
        """Test that metrics are computed correctly"""
        cube = self.create_test_cube(watertight=True)
        
        with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as tmp:
            cube.export(tmp.name)
            
            try:
                report = self.validator.validate_mesh(tmp.name, 'test_cube.stl')
                
                metrics = report.metrics
                assert metrics.triangles == 12
                assert metrics.vertices == 8
                assert metrics.components == 1
                assert len(metrics.bbox_mm) == 3
                assert all(dim > 0 for dim in metrics.bbox_mm)
                
            finally:
                os.unlink(tmp.name)
    
    def test_invalid_file_handling(self):
        """Test handling of invalid files"""
        # Create a temporary file with invalid content
        with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as tmp:
            tmp.write(b"Invalid STL content")
            tmp.flush()
            
            try:
                report = self.validator.validate_mesh(tmp.name, 'invalid.stl')
                
                # Should have errors and be blocked
                assert len(report.errors) > 0
                assert report.decision == ValidationStatus.BLOCK
                
            finally:
                os.unlink(tmp.name)
    
    def test_decision_logic(self):
        """Test decision logic based on errors and warnings"""
        # Test with errors
        errors = [{"code": ErrorCode.NOT_WATERTIGHT, "message": "Test error", "severity": "error"}]
        warnings = []
        decision = self.validator._determine_decision(
            [type('obj', (), error) for error in errors],
            [type('obj', (), warning) for warning in warnings]
        )
        assert decision == ValidationStatus.BLOCK
        
        # Test with warnings only
        errors = []
        warnings = [{"code": ErrorCode.THIN_WALL, "message": "Test warning", "severity": "warning"}]
        decision = self.validator._determine_decision(
            [type('obj', (), error) for error in errors],
            [type('obj', (), warning) for warning in warnings]
        )
        assert decision == ValidationStatus.ALLOW_WITH_WARNINGS
        
        # Test with no issues
        errors = []
        warnings = []
        decision = self.validator._determine_decision(
            [type('obj', (), error) for error in errors],
            [type('obj', (), warning) for warning in warnings]
        )
        assert decision == ValidationStatus.ALLOW


if __name__ == "__main__":
    pytest.main([__file__])
