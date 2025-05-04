import pytest
import json
import os
from io import BytesIO


class TestFileEndpoints:
    def test_file_upload(self, client):
        """Test uploading files through the API"""
        # Create a test file
        data = {
            'file': (BytesIO(b'{"text": "This is a test document"}'), 'test.json')
        }

        response = client.post(
            '/api/files/upload',
            data=data,
            content_type='multipart/form-data'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'task_id' in data
        assert data['status'] == 'queued'
        assert data['files'] == 1

    def test_task_status(self, client):
        """Test checking task status"""
        response = client.get('/api/files/status/12345')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'task_id' in data
        assert 'queue_stats' in data


class TestSearchEndpoints:
    def test_search(self, client):
        """Test searching for similar items"""
        query_data = {
            'q': 'test query',
            'k': 3
        }

        response = client.post(
            '/api/search',
            data=json.dumps(query_data),
            content_type='application/json'
        )

        assert response.status_code == 200

    def test_search_validation(self, client):
        """Test search input validation"""
        # Missing query
        query_data = {'k': 3}

        response = client.post(
            '/api/search',
            data=json.dumps(query_data),
            content_type='application/json'
        )

        assert response.status_code == 400

        # Invalid k parameter
        query_data = {
            'q': 'test query',
            'k': 'invalid'
        }

        response = client.post(
            '/api/search',
            data=json.dumps(query_data),
            content_type='application/json'
        )

        assert response.status_code == 400

    def test_visualization(self, client):
        """Test visualization data endpoint"""
        response = client.get('/api/search/visualization')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'clusters' in data
        assert 'projection' in data


class TestModelEndpoints:
    def test_list_models(self, client):
        """Test listing available models"""
        response = client.get('/api/models/list')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'models' in data
        assert 'active_model' in data
        assert len(data['models']) > 0

    def test_switch_model(self, client):
        """Test switching the active model"""
        # Switch to a valid model
        response = client.get('/api/models/switch/v1')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['status'] == 'success'
        assert data['active_model'] == 'v1'

        # Switch to an invalid model
        response = client.get('/api/models/switch/invalid_model')

        assert response.status_code == 400


class TestHealthEndpoint:
    def test_health_check(self, client):
        """Test the health check endpoint"""
        response = client.get('/api/health')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'status' in data
        assert data['status'] == 'healthy'
