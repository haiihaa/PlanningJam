# Framework-generated: 0%
# Human-written: 80%
# AI-generated: 20%

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from datetime import datetime
from unittest.mock import patch, MagicMock
from bson import ObjectId

pytestmark = pytest.mark.django_db

client = APIClient()

class TestRSVPAPI:
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Setup test data before each test method"""
        # Create test user
        self.user = User.objects.create_user(username="testuser", password="testpwd1234")
        client.force_authenticate(user=self.user)
        
        # Mock plan ID for testing
        self.plan_id = str(ObjectId())

    @patch('api.views.rsvp.rsvp_collection')
    def test_create_rsvp_success(self, mock_collection):
        """Test successful RSVP creation"""
        # Mock the insert_one method
        mock_result = MagicMock()
        mock_result.inserted_id = ObjectId()
        mock_collection.insert_one.return_value = mock_result
        # Mock find_one to return None (no existing RSVP)
        mock_collection.find_one.return_value = None
        
        url = reverse("create-rsvp")
        
        data = {
            "plan_id": self.plan_id
        }
        
        response = client.post(url, data, format="json")
        
        assert response.status_code == 201
        assert "id" in response.data
        assert response.data["message"] == "RSVP created"
        assert response.data["data"]["plan_id"] == self.plan_id
        assert response.data["data"]["user_id"] == str(self.user.id)
        assert "created_at" in response.data["data"]

    def test_create_rsvp_missing_plan_id(self):
        """Test RSVP creation with missing plan_id"""
        url = reverse("create-rsvp")
        
        data = {}
        
        response = client.post(url, data, format="json")
        
        assert response.status_code == 400
        assert "plan_id" in response.data

    @patch('api.views.rsvp.rsvp_collection')
    def test_create_rsvp_invalid_plan_id(self, mock_collection):
        """Test RSVP creation with invalid plan_id format"""
        # Mock the insert_one method
        mock_result = MagicMock()
        mock_result.inserted_id = ObjectId()
        mock_collection.insert_one.return_value = mock_result
        # Mock find_one to return None (no existing RSVP)
        mock_collection.find_one.return_value = None
        
        url = reverse("create-rsvp")
        
        data = {
            "plan_id": "invalid_id"
        }
        
        response = client.post(url, data, format="json")
        
        # Should still create RSVP as we're not validating plan_id format in serializer
        assert response.status_code == 201

    @patch('api.views.rsvp.rsvp_collection')
    def test_get_rsvp_by_plan_id_success(self, mock_collection):
        """Test successful retrieval of RSVPs by plan_id"""
        # Mock the find method to return a list
        mock_rsvps = [
            {
                "_id": ObjectId(),
                "plan_id": self.plan_id,
                "user_id": str(self.user.id),
                "created_at": datetime.now().isoformat()
            },
            {
                "_id": ObjectId(),
                "plan_id": self.plan_id,
                "user_id": "456",
                "created_at": datetime.now().isoformat()
            }
        ]
        mock_collection.find.return_value = mock_rsvps
        
        url = reverse("get-rsvp-by-plan-id", kwargs={"plan_id": self.plan_id})
        response = client.get(url)
        
        assert response.status_code == 200
        assert "data" in response.data
        assert len(response.data["data"]) == 2
        assert response.data["data"][0]["plan_id"] == self.plan_id
        assert response.data["data"][0]["user_id"] == str(self.user.id)
        assert response.data["data"][1]["user_id"] == "456"

    @patch('api.views.rsvp.rsvp_collection')
    def test_get_rsvp_by_plan_id_not_found(self, mock_collection):
        """Test retrieval of non-existent RSVP by plan_id"""
        # Mock the find method to return empty list
        mock_collection.find.return_value = []
        
        url = reverse("get-rsvp-by-plan-id", kwargs={"plan_id": self.plan_id})
        response = client.get(url)
        
        assert response.status_code == 200
        assert response.data["data"] == []

    @patch('api.views.rsvp.rsvp_collection')
    def test_get_rsvp_by_user_id_success(self, mock_collection):
        """Test successful retrieval of RSVPs by user_id"""
        # Mock the find method to return a list
        mock_rsvps = [
            {
                "_id": ObjectId(),
                "plan_id": self.plan_id,
                "user_id": str(self.user.id),
                "created_at": datetime.now().isoformat()
            },
            {
                "_id": ObjectId(),
                "plan_id": "another_plan_id",
                "user_id": str(self.user.id),
                "created_at": datetime.now().isoformat()
            }
        ]
        mock_collection.find.return_value = mock_rsvps
        
        url = reverse("get-rsvp-by-user-id")
        response = client.get(url)
        
        assert response.status_code == 200
        assert "data" in response.data
        assert len(response.data["data"]) == 2
        assert response.data["data"][0]["plan_id"] == self.plan_id
        assert response.data["data"][0]["user_id"] == str(self.user.id)
        assert response.data["data"][1]["plan_id"] == "another_plan_id"

    @patch('api.views.rsvp.rsvp_collection')
    def test_get_rsvp_by_user_id_not_found(self, mock_collection):
        """Test retrieval of non-existent RSVP by user_id"""
        # Mock the find method to return empty list
        mock_collection.find.return_value = []
        
        url = reverse("get-rsvp-by-user-id")
        response = client.get(url)
        
        assert response.status_code == 200
        assert response.data["data"] == []

    @patch('api.views.rsvp.rsvp_collection')
    def test_delete_rsvp_by_id_success(self, mock_collection):
        """Test successful deletion of RSVP by ID"""
        rsvp_id = str(ObjectId())
        
        # Mock find_one to return RSVP owned by the current user
        mock_rsvp = {
            "_id": ObjectId(rsvp_id),
            "plan_id": self.plan_id,
            "user_id": str(self.user.id),
            "created_at": datetime.now().isoformat()
        }
        mock_collection.find_one.return_value = mock_rsvp
        
        # Mock the delete_one method
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        mock_collection.delete_one.return_value = mock_result
        
        url = reverse("delete-rsvp-by-id", kwargs={"rsvp_id": rsvp_id})
        response = client.delete(url)
        
        assert response.status_code == 200
        assert f"RSVP {rsvp_id} deleted successfully" in response.data["message"]

    @patch('api.views.rsvp.rsvp_collection')
    def test_delete_rsvp_by_id_not_found(self, mock_collection):
        """Test deletion of non-existent RSVP by ID"""
        # Mock find_one to return None (RSVP not found)
        mock_collection.find_one.return_value = None
        
        # Mock delete_one to return 0 deleted count
        mock_result = MagicMock()
        mock_result.deleted_count = 0
        mock_collection.delete_one.return_value = mock_result
        
        fake_id = str(ObjectId())
        url = reverse("delete-rsvp-by-id", kwargs={"rsvp_id": fake_id})
        response = client.delete(url)
        
        assert response.status_code == 404
        assert response.data["error"] == "RSVP not found"
    
    @patch('api.views.rsvp.rsvp_collection')
    def test_delete_rsvp_by_id_unauthorized(self, mock_collection):
        """Test deletion of RSVP by another user (unauthorized)"""
        rsvp_id = str(ObjectId())
        
        # Mock find_one to return RSVP owned by a different user
        mock_rsvp = {
            "_id": ObjectId(rsvp_id),
            "plan_id": self.plan_id,
            "user_id": "different_user_id",
            "created_at": datetime.now().isoformat()
        }
        mock_collection.find_one.return_value = mock_rsvp
        
        url = reverse("delete-rsvp-by-id", kwargs={"rsvp_id": rsvp_id})
        response = client.delete(url)
        
        assert response.status_code == 403
        assert response.data["error"] == "Not authorized"

    def test_delete_rsvp_by_id_invalid_id(self):
        """Test deletion with invalid RSVP ID format"""
        url = reverse("delete-rsvp-by-id", kwargs={"rsvp_id": "invalid_id"})
        response = client.delete(url)
        
        assert response.status_code == 400
        assert response.data["error"] == "Invalid ID"

    @patch('api.views.rsvp.rsvp_collection')
    def test_delete_rsvp_by_plan_id_success(self, mock_collection):
        """Test successful deletion of RSVP by plan_id"""
        # Mock the delete_one method
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        mock_collection.delete_one.return_value = mock_result
        
        # Use a valid ObjectId string for plan_id
        valid_plan_id = str(ObjectId())
        url = reverse("delete-rsvp-by-plan-id", kwargs={"plan_id": valid_plan_id})
        response = client.delete(url)
        
        assert response.status_code == 200
        assert f"RSVP for plan {valid_plan_id} deleted successfully" in response.data["message"]

    @patch('api.views.rsvp.rsvp_collection')
    def test_delete_rsvp_by_plan_id_not_found(self, mock_collection):
        """Test deletion of non-existent RSVP by plan_id"""
        # Mock the delete_one method
        mock_result = MagicMock()
        mock_result.deleted_count = 0
        mock_collection.delete_one.return_value = mock_result
        
        # Use a valid ObjectId string for plan_id
        valid_plan_id = str(ObjectId())
        url = reverse("delete-rsvp-by-plan-id", kwargs={"plan_id": valid_plan_id})
        response = client.delete(url)
        
        assert response.status_code == 404
        assert response.data["error"] == "RSVP not found"

    def test_delete_rsvp_by_plan_id_invalid_id(self):
        """Test deletion with invalid plan ID format"""
        url = reverse("delete-rsvp-by-plan-id", kwargs={"plan_id": "invalid_id"})
        response = client.delete(url)
        
        assert response.status_code == 400
        assert response.data["error"] == "Invalid ID"

    def test_rsvp_authentication_required(self):
        """Test that RSVP endpoints require authentication"""
        # Remove authentication
        client.force_authenticate(user=None)
        
        # Test create RSVP without authentication
        url = reverse("create-rsvp")
        data = {
            "plan_id": self.plan_id
        }
        response = client.post(url, data, format="json")
        assert response.status_code == 401
        
        # Test get RSVP by plan ID without authentication
        url = reverse("get-rsvp-by-plan-id", kwargs={"plan_id": self.plan_id})
        response = client.get(url)
        assert response.status_code == 401
        
        # Test get RSVP by user ID without authentication
        url = reverse("get-rsvp-by-user-id")
        response = client.get(url)
        assert response.status_code == 401
        
        # Test delete RSVP by ID without authentication
        rsvp_id = str(ObjectId())
        url = reverse("delete-rsvp-by-id", kwargs={"rsvp_id": rsvp_id})
        response = client.delete(url)
        assert response.status_code == 401
        
        # Test delete RSVP by plan ID without authentication
        url = reverse("delete-rsvp-by-plan-id", kwargs={"plan_id": self.plan_id})
        response = client.delete(url)
        assert response.status_code == 401

    @patch('api.views.rsvp.rsvp_collection')
    def test_multiple_rsvps_same_plan(self, mock_collection):
        """Test that multiple users can RSVP to the same plan"""
        # Mock the insert_one method
        mock_result = MagicMock()
        mock_result.inserted_id = ObjectId()
        mock_collection.insert_one.return_value = mock_result
        
        # Mock find_one to return None (no existing RSVP)
        mock_collection.find_one.return_value = None
        
        # Create another user
        user2 = User.objects.create_user(username="testuser2", password="testpwd1234")
        
        # Create RSVP for first user
        url = reverse("create-rsvp")
        data = {
            "plan_id": self.plan_id
        }
        response1 = client.post(url, data, format="json")
        assert response1.status_code == 201
        
        # Create RSVP for second user
        client.force_authenticate(user=user2)
        response2 = client.post(url, data, format="json")
        assert response2.status_code == 201

    @patch('api.views.rsvp.rsvp_collection')
    def test_duplicate_rsvp_prevention(self, mock_collection):
        """Test that users cannot RSVP to the same plan multiple times"""
        # Mock find_one to return existing RSVP
        existing_rsvp = {
            "_id": ObjectId(),
            "plan_id": self.plan_id,
            "user_id": str(self.user.id),
            "created_at": datetime.now().isoformat()
        }
        mock_collection.find_one.return_value = existing_rsvp
        
        url = reverse("create-rsvp")
        data = {
            "plan_id": self.plan_id
        }
        
        response = client.post(url, data, format="json")
        
        assert response.status_code == 400
        assert "already RSVP'd" in response.data["error"]
        # Ensure insert_one was not called
        mock_collection.insert_one.assert_not_called()

    @patch('api.views.rsvp.rsvp_collection')
    def test_create_rsvp_duplicate_prevention(self, mock_collection):
        """Test that duplicate RSVP creation is prevented"""
        # Mock find_one to return existing RSVP (duplicate)
        existing_rsvp = {
            "_id": ObjectId(),
            "plan_id": self.plan_id,
            "user_id": str(self.user.id),
            "created_at": datetime.now().isoformat()
        }
        mock_collection.find_one.return_value = existing_rsvp
        
        url = reverse("create-rsvp")
        data = {
            "plan_id": self.plan_id
        }
        
        response = client.post(url, data, format="json")
        
        assert response.status_code == 400
        assert "already RSVP'd" in response.data["error"]
        # Ensure insert_one was not called
        mock_collection.insert_one.assert_not_called()

    @patch('api.views.rsvp.rsvp_collection')
    def test_rsvp_data_integrity(self, mock_collection):
        """Test that RSVP data is stored correctly"""
        # Mock the insert_one method
        mock_result = MagicMock()
        mock_result.inserted_id = ObjectId()
        mock_collection.insert_one.return_value = mock_result
        # Mock find_one to return None (no existing RSVP)
        mock_collection.find_one.return_value = None
        
        url = reverse("create-rsvp")
        
        data = {
            "plan_id": self.plan_id
        }
        
        response = client.post(url, data, format="json")
        assert response.status_code == 201
        
        # Verify the data was passed to insert_one correctly
        mock_collection.insert_one.assert_called_once()
        call_args = mock_collection.insert_one.call_args[0][0]
        assert call_args["plan_id"] == self.plan_id
        assert call_args["user_id"] == str(self.user.id)
        assert "created_at" in call_args
