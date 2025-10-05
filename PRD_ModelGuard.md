# 🦷 ModelGuard – 3D Model Validation Service

## **1. Overview**

ModelGuard is an intelligent 3D model validation microservice designed to automatically detect and report geometry or printability issues in dental 3D models before they are processed for 3D printing. The goal is to ensure error-free prints, reduce failed jobs, and streamline SprintRay's digital workflow.

---

## **2. Problem Statement**

Dental technicians and clinicians upload STL or OBJ files from various CAD tools. These models often contain errors such as:

* Non-manifold edges
* Open boundaries (non-watertight meshes)
* Self-intersections
* Thin walls below print tolerance
* Unoriented normals or duplicate vertices

These issues lead to print failures, wasted material, and workflow interruptions. A lightweight validation service can catch and fix these errors automatically before printing.

---

## **3. Goals and Success Metrics**

### **Goals**

* Validate models automatically within seconds after upload.
* Detect and classify geometry and printability issues.
* Provide actionable feedback and visual error overlays.
* Generate a JSON validation report consumable by backend systems.
* Maintain modularity for integration with existing SprintRay services.

### **Success Metrics**

| Metric                        | Target                                   |
| ----------------------------- | ---------------------------------------- |
| Average validation time       | < 3 seconds per model                    |
| Accuracy of error detection   | ≥ 95% for watertight and manifold checks |
| False-positive rate           | ≤ 5%                                     |
| Uptime (service availability) | ≥ 99%                                    |
| Integration readiness         | RESTful API + optional Streamlit UI      |

---

## **4. Key Features**

### **Core Validation**

* Check watertightness and manifold integrity.
* Detect degenerate or duplicate faces.
* Measure bounding box and compute mesh metrics.
* Estimate wall thickness using voxel or sampling approach.
* Detect self-intersections using BVH.

### **Reporting**

* Generate detailed JSON report with errors, warnings, and metadata.
* Include human-readable messages and numeric stats.
* Return validation status: `BLOCK`, `ALLOW_WITH_WARNINGS`, or `ALLOW`.

### **Visualization**

* Streamlit UI for file uploads and validation previews.
* Color-coded highlights for thin regions or bad edges.
* Optional 3D visualization with Three.js for integration later.

### **Auto-Fix (Optional)**

* Merge near-duplicate vertices.
* Fill small holes.
* Flip inverted normals.

---

## **5. System Design**

### **Architecture**

**Frontend:**

* Streamlit (lightweight UI) or React + Three.js (future expansion).

**Backend:**

* FastAPI service exposing `/validate`, `/report/{id}`, `/health`.
* Implements geometry checks using `trimesh`, `open3d`, and `pymeshlab`.
* Generates and stores reports in memory (later: MongoDB or S3).

**Workflow:**

1. User uploads model → `FastAPI` receives file.
2. Validator loads mesh, computes metrics, and runs checks.
3. JSON report returned → UI displays structured feedback.
4. Optional repair suggestions applied automatically.

---

## **6. API Specification**

### **POST /validate**

Uploads and validates a 3D file.
**Request:**

* Form-data with field `file` (STL, OBJ, or PLY).

**Response:**

```json
{
  "model_id": "uuid",
  "filename": "dental_model.stl",
  "metrics": {
    "triangles": 132000,
    "vertices": 67000,
    "components": 1,
    "bbox_mm": [50.2, 35.7, 28.1],
    "units": "mm"
  },
  "errors": [
    {"code": "NOT_WATERTIGHT", "message": "Mesh has 12 open boundaries"}
  ],
  "warnings": [
    {"code": "THIN_WALL", "message": "Detected 0.7mm thickness in 3 regions"}
  ],
  "decision": "BLOCK"
}
```

### **GET /report/{model_id}**

Retrieves a previously generated report.

### **GET /health**

Simple health check endpoint.

---

## **7. Technical Stack**

| Component         | Technology                        |
| ----------------- | --------------------------------- |
| Backend Framework | FastAPI                           |
| Geometry Engine   | Trimesh, Open3D, PyMeshLab        |
| Frontend          | Streamlit                         |
| Data Store        | In-memory or MongoDB              |
| Deployment        | Docker + AWS EC2 or GCP Cloud Run |
| Version Control   | GitHub                            |

---

## **8. Validation Pipeline**

| Stage                   | Description                                    |
| ----------------------- | ---------------------------------------------- |
| **Pre-check**           | File parsing, format validation, size limits   |
| **Mesh Analysis**       | Triangle count, watertightness, manifold check |
| **Topology Check**      | Non-manifold edges, disconnected components    |
| **Geometric Integrity** | Self-intersections and zero-area faces         |
| **Printability**        | Wall thickness and cavity detection            |
| **Post-check**          | Decision logic and report generation           |

---

## **9. Future Enhancements**

* AI-based classification of error types.
* 3D overlay preview inside SprintRay's CAD web interface.
* Integration with cloud print queue API.
* Batch validation for multiple models.
* User analytics and telemetry dashboard.

---

## **10. Risks and Mitigation**

| Risk                                   | Mitigation                                        |
| -------------------------------------- | ------------------------------------------------- |
| Large model size slowing validation    | Implement streaming load and timeouts             |
| False positives in thin wall detection | Use adaptive sampling and configurable thresholds |
| Memory leaks in geometry libraries     | Sandbox mesh processing per request               |
| User privacy with model uploads        | Automatically delete files post-validation        |

---

## **11. Deliverables**

* Functional FastAPI service with validation endpoints.
* Streamlit-based frontend uploader.
* Sample reports and test cases.
* Documentation and setup guide.
* Optional demo video or notebook.

---

## **12. Timeline**

| Week   | Milestone                                                |
| ------ | -------------------------------------------------------- |
| Week 1 | Setup FastAPI skeleton, core mesh validation             |
| Week 2 | Add warning system, JSON report, and Streamlit UI        |
| Week 3 | Implement auto-fix routines and visualization overlay    |
| Week 4 | Optimize performance, finalize documentation, demo video |

---
