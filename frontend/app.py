"""
Streamlit frontend for ModelGuard
"""
import streamlit as st
import requests
import json
import time
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, Any
import pandas as pd

# Configuration
API_BASE_URL = "http://localhost:8000"
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

# Page configuration
st.set_page_config(
    page_title="ModelGuard - 3D Model Validation",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 3rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .error-card {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .warning-card {
        background-color: #fff3e0;
        border-left: 4px solid #ff9800;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .success-card {
        background-color: #e8f5e8;
        border-left: 4px solid #4caf50;
        padding: 1rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


def check_api_health() -> bool:
    """Check if the API is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def upload_and_validate(file) -> Dict[str, Any]:
    """Upload file and get validation results"""
    try:
        files = {"file": (file.name, file, file.type)}
        response = requests.post(f"{API_BASE_URL}/validate", files=files, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"API Error: {response.status_code} - {response.text}"}
    except requests.exceptions.Timeout:
        return {"error": "Request timed out. The file might be too large or complex."}
    except Exception as e:
        return {"error": f"Upload failed: {str(e)}"}


def display_validation_results(report: Dict[str, Any]):
    """Display validation results in a nice format"""
    
    # Header with decision
    decision = report.get("decision", "UNKNOWN")
    decision_colors = {
        "ALLOW": "🟢",
        "ALLOW_WITH_WARNINGS": "🟡", 
        "BLOCK": "🔴"
    }
    
    decision_icons = {
        "ALLOW": "✅",
        "ALLOW_WITH_WARNINGS": "⚠️",
        "BLOCK": "❌"
    }
    
    st.markdown(f"""
    <div class="metric-card">
        <h2>{decision_icons.get(decision, "❓")} Validation Decision: {decision.replace('_', ' ').title()}</h2>
        <p><strong>Model ID:</strong> {report.get('model_id', 'N/A')}</p>
        <p><strong>Processing Time:</strong> {report.get('processing_time_ms', 0):.2f} ms</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Metrics
    metrics = report.get("metrics", {})
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Triangles", f"{metrics.get('triangles', 0):,}")
    with col2:
        st.metric("Vertices", f"{metrics.get('vertices', 0):,}")
    with col3:
        st.metric("Components", metrics.get('components', 0))
    with col4:
        bbox = metrics.get('bbox_mm', [0, 0, 0])
        st.metric("Size (mm)", f"{bbox[0]:.1f}×{bbox[1]:.1f}×{bbox[2]:.1f}")
    
    # Errors
    errors = report.get("errors", [])
    if errors:
        st.markdown("### ❌ Errors")
        for error in errors:
            st.markdown(f"""
            <div class="error-card">
                <strong>{error.get('code', 'UNKNOWN')}</strong><br>
                {error.get('message', 'No message')}
                {f"<br><em>Count: {error.get('count', 'N/A')}</em>" if error.get('count') else ""}
            </div>
            """, unsafe_allow_html=True)
    
    # Warnings
    warnings = report.get("warnings", [])
    if warnings:
        st.markdown("### ⚠️ Warnings")
        for warning in warnings:
            st.markdown(f"""
            <div class="warning-card">
                <strong>{warning.get('code', 'UNKNOWN')}</strong><br>
                {warning.get('message', 'No message')}
                {f"<br><em>Count: {warning.get('count', 'N/A')}</em>" if warning.get('count') else ""}
            </div>
            """, unsafe_allow_html=True)
    
    # Success message if no errors
    if not errors and not warnings:
        st.markdown("""
        <div class="success-card">
            <h3>🎉 Model is Valid!</h3>
            <p>No errors or warnings detected. The model is ready for 3D printing.</p>
        </div>
        """, unsafe_allow_html=True)


def display_metrics_chart(metrics: Dict[str, Any]):
    """Display metrics in a chart"""
    if not metrics:
        return
    
    # Create a simple bar chart for key metrics
    metric_names = ['Triangles', 'Vertices', 'Components']
    metric_values = [
        metrics.get('triangles', 0),
        metrics.get('vertices', 0), 
        metrics.get('components', 0)
    ]
    
    fig = go.Figure(data=[
        go.Bar(x=metric_names, y=metric_values, marker_color=['#1f77b4', '#ff7f0e', '#2ca02c'])
    ])
    
    fig.update_layout(
        title="Model Metrics",
        xaxis_title="Metric",
        yaxis_title="Count",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)


def main():
    """Main Streamlit app"""
    
    # Header
    st.markdown('<h1 class="main-header">🦷 ModelGuard</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">3D Model Validation Service for Dental Models</p>', unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Choose a page", ["Upload & Validate", "View Reports", "API Status"])
    
    # Check API health
    api_healthy = check_api_health()
    
    if not api_healthy:
        st.error("⚠️ API is not running. Please start the backend server with: `python -m backend.main`")
        st.stop()
    
    if page == "Upload & Validate":
        st.header("📁 Upload 3D Model")
        
        # File upload
        uploaded_file = st.file_uploader(
            "Choose a 3D model file",
            type=['stl', 'obj', 'ply'],
            help="Supported formats: STL, OBJ, PLY (Max size: 100MB)"
        )
        
        if uploaded_file is not None:
            # Display file info
            st.info(f"📄 **File:** {uploaded_file.name} ({uploaded_file.size:,} bytes)")
            
            # Validate button
            if st.button("🔍 Validate Model", type="primary"):
                with st.spinner("Validating model... This may take a few seconds."):
                    result = upload_and_validate(uploaded_file)
                
                if "error" in result:
                    st.error(f"❌ {result['error']}")
                else:
                    st.success("✅ Validation completed!")
                    
                    # Display results
                    display_validation_results(result)
                    
                    # Display metrics chart
                    if result.get("metrics"):
                        st.header("📊 Model Metrics")
                        display_metrics_chart(result["metrics"])
    
    elif page == "View Reports":
        st.header("📋 Validation Reports")
        
        try:
            response = requests.get(f"{API_BASE_URL}/reports")
            if response.status_code == 200:
                reports_data = response.json()
                reports = reports_data.get("reports", [])
                
                if reports:
                    # Create DataFrame for display
                    df = pd.DataFrame(reports)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df = df.sort_values('timestamp', ascending=False)
                    
                    st.dataframe(
                        df[['model_id', 'filename', 'decision', 'timestamp']],
                        use_container_width=True
                    )
                    
                    # Allow viewing individual reports
                    selected_id = st.selectbox("Select a report to view details:", df['model_id'])
                    if st.button("View Details"):
                        try:
                            detail_response = requests.get(f"{API_BASE_URL}/report/{selected_id}")
                            if detail_response.status_code == 200:
                                detail_report = detail_response.json()
                                display_validation_results(detail_report)
                            else:
                                st.error("Failed to load report details")
                        except Exception as e:
                            st.error(f"Error loading report: {str(e)}")
                else:
                    st.info("No validation reports found.")
            else:
                st.error("Failed to load reports")
        except Exception as e:
            st.error(f"Error connecting to API: {str(e)}")
    
    elif page == "API Status":
        st.header("🔧 API Status")
        
        if api_healthy:
            st.success("✅ API is running and healthy")
            
            try:
                health_response = requests.get(f"{API_BASE_URL}/health")
                if health_response.status_code == 200:
                    health_data = health_response.json()
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Status", health_data.get("status", "unknown"))
                    with col2:
                        st.metric("Version", health_data.get("version", "unknown"))
                    with col3:
                        uptime = health_data.get("uptime_seconds", 0)
                        st.metric("Uptime", f"{uptime:.1f}s")
            except Exception as e:
                st.warning(f"Could not fetch detailed health info: {str(e)}")
        else:
            st.error("❌ API is not responding")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; margin-top: 2rem;">
        <p>ModelGuard v1.0.0 | Built with FastAPI & Streamlit</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
