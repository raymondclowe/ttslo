"""
Tests for new dashboard endpoints: /health, /backup, /openapi.json
"""
import pytest
import os
import json
import zipfile
import io
from dashboard import app


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_health_endpoint(client):
    """Test the /health endpoint returns proper structure."""
    response = client.get('/health')
    assert response.status_code in [200, 503]  # Either healthy or unhealthy
    
    data = response.get_json()
    assert 'status' in data
    assert data['status'] in ['healthy', 'unhealthy']
    assert 'timestamp' in data
    assert 'checks' in data
    assert 'config_file' in data['checks']
    assert 'kraken_api' in data['checks']


def test_health_endpoint_returns_503_when_unhealthy(client, monkeypatch):
    """Test that /health returns 503 when system is unhealthy."""
    # Mock config file not existing
    monkeypatch.setattr('dashboard.CONFIG_FILE', '/nonexistent/config.csv')
    
    response = client.get('/health')
    
    # Should return 503 because config file doesn't exist
    assert response.status_code == 503
    data = response.get_json()
    assert data['status'] == 'unhealthy'
    assert data['checks']['config_file'] is False


def test_openapi_json_endpoint(client):
    """Test the /openapi.json endpoint returns valid OpenAPI spec."""
    response = client.get('/openapi.json')
    assert response.status_code == 200
    
    data = response.get_json()
    
    # Verify it's a valid OpenAPI spec
    assert 'openapi' in data
    assert data['openapi'] == '3.0.0'
    assert 'info' in data
    assert 'title' in data['info']
    assert 'paths' in data
    
    # Verify our new endpoints are documented
    assert '/health' in data['paths']
    assert '/backup' in data['paths']
    assert '/openapi.json' in data['paths']
    
    # Verify existing endpoints are documented
    assert '/api/status' in data['paths']
    assert '/api/pending' in data['paths']
    assert '/api/active' in data['paths']
    assert '/api/completed' in data['paths']


def test_backup_endpoint_returns_zip(client):
    """Test the /backup endpoint returns a zip file."""
    response = client.get('/backup')
    assert response.status_code == 200
    assert response.mimetype == 'application/zip'
    
    # Check Content-Disposition header
    assert 'attachment' in response.headers.get('Content-Disposition', '')
    assert 'ttslo-backup-' in response.headers.get('Content-Disposition', '')


def test_backup_zip_contains_manifest(client):
    """Test that the backup zip contains a manifest file."""
    response = client.get('/backup')
    assert response.status_code == 200
    
    # Parse the zip file from response data
    zip_buffer = io.BytesIO(response.data)
    with zipfile.ZipFile(zip_buffer, 'r') as zf:
        # Check that manifest exists
        assert 'backup_manifest.json' in zf.namelist()
        
        # Read and parse manifest
        manifest_data = zf.read('backup_manifest.json')
        manifest = json.loads(manifest_data)
        
        # Verify manifest structure
        assert 'backup_time' in manifest
        assert 'files_included' in manifest
        assert isinstance(manifest['files_included'], list)


def test_backup_includes_config_if_exists(client, tmp_path, monkeypatch):
    """Test that backup includes config file if it exists."""
    # Create a temporary config file
    config_file = tmp_path / "config.csv"
    config_file.write_text("id,pair,threshold_price\ntest,XXBTZUSD,50000\n")
    
    # Mock the CONFIG_FILE path
    monkeypatch.setattr('dashboard.CONFIG_FILE', str(config_file))
    
    response = client.get('/backup')
    assert response.status_code == 200
    
    # Parse zip and check for config file
    zip_buffer = io.BytesIO(response.data)
    with zipfile.ZipFile(zip_buffer, 'r') as zf:
        assert 'config.csv' in zf.namelist()
        # Verify content
        config_content = zf.read('config.csv').decode('utf-8')
        assert 'test,XXBTZUSD,50000' in config_content


def test_backup_includes_state_if_exists(client, tmp_path, monkeypatch):
    """Test that backup includes state file if it exists."""
    # Create a temporary state file
    state_file = tmp_path / "state.csv"
    state_file.write_text("id,triggered\ntest,false\n")
    
    # Mock the STATE_FILE path
    monkeypatch.setattr('dashboard.STATE_FILE', str(state_file))
    
    response = client.get('/backup')
    assert response.status_code == 200
    
    # Parse zip and check for state file
    zip_buffer = io.BytesIO(response.data)
    with zipfile.ZipFile(zip_buffer, 'r') as zf:
        assert 'state.csv' in zf.namelist()


def test_openapi_spec_matches_actual_endpoints(client):
    """Test that OpenAPI spec documents all actual endpoints."""
    response = client.get('/openapi.json')
    spec = response.get_json()
    
    documented_paths = set(spec['paths'].keys())
    
    # All these endpoints should be documented
    expected_paths = {
        '/',
        '/api/status',
        '/api/pending',
        '/api/active',
        '/api/completed',
        '/health',
        '/backup',
        '/openapi.json'
    }
    
    assert expected_paths.issubset(documented_paths), \
        f"Missing paths in OpenAPI spec: {expected_paths - documented_paths}"


def test_openapi_spec_has_proper_schemas(client):
    """Test that OpenAPI spec has proper schema definitions."""
    response = client.get('/openapi.json')
    spec = response.get_json()
    
    # Check that components/schemas exists
    assert 'components' in spec
    assert 'schemas' in spec['components']
    
    schemas = spec['components']['schemas']
    
    # Verify key schemas are defined
    expected_schemas = [
        'SystemStatus',
        'HealthResponse',
        'PendingOrder',
        'ActiveOrder',
        'CompletedOrder'
    ]
    
    for schema_name in expected_schemas:
        assert schema_name in schemas, f"Missing schema: {schema_name}"
        assert 'properties' in schemas[schema_name], \
            f"Schema {schema_name} has no properties"


def test_health_response_matches_openapi_schema(client):
    """Test that /health response matches OpenAPI schema."""
    # Get the response
    response = client.get('/health')
    data = response.get_json()
    
    # Get the schema
    spec_response = client.get('/openapi.json')
    spec = spec_response.get_json()
    health_schema = spec['components']['schemas']['HealthResponse']
    
    # Verify all required properties are present
    for prop in health_schema['properties'].keys():
        assert prop in data, f"Missing property: {prop}"


def test_status_response_matches_openapi_schema(client):
    """Test that /api/status response matches OpenAPI schema."""
    # Get the response
    response = client.get('/api/status')
    data = response.get_json()
    
    # Get the schema
    spec_response = client.get('/openapi.json')
    spec = spec_response.get_json()
    status_schema = spec['components']['schemas']['SystemStatus']
    
    # Verify all required properties are present
    for prop in status_schema['properties'].keys():
        assert prop in data, f"Missing property: {prop}"


def test_health_details_page(client):
    """Test that /health-details page loads correctly."""
    response = client.get('/health-details')
    assert response.status_code == 200
    assert b'Health Status' in response.data
    assert b'System Health and Configuration Details' in response.data
