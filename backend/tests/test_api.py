"""
Backend API Tests for Career Assault Platform
Tests: Health, Auth, Profile, Analyses endpoints
"""
import pytest
import requests
import os
import io
import time
from datetime import datetime, timezone, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# ==================== HEALTH ENDPOINT ====================

class TestHealthEndpoint:
    """Health check endpoint tests."""
    
    def test_health_returns_200(self, api_client):
        """GET /api/ health endpoint returns 200."""
        response = api_client.get(f"{BASE_URL}/api/")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"
        print(f"✓ Health check passed: {data}")


# ==================== AUTH ENDPOINTS (UNAUTHENTICATED) ====================

class TestUnauthenticatedAccess:
    """Tests for unauthenticated access - should return 401."""
    
    def test_auth_me_unauthenticated_returns_401(self, api_client):
        """Unauthenticated GET /api/auth/me returns 401."""
        # Remove any auth headers
        headers = {"Content-Type": "application/json"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ /api/auth/me returns 401 for unauthenticated request")
    
    def test_profile_unauthenticated_returns_401(self, api_client):
        """Unauthenticated GET /api/profile returns 401."""
        headers = {"Content-Type": "application/json"}
        response = requests.get(f"{BASE_URL}/api/profile", headers=headers)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ /api/profile returns 401 for unauthenticated request")
    
    def test_analyses_post_unauthenticated_returns_401(self, api_client):
        """Unauthenticated POST /api/analyses returns 401."""
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            f"{BASE_URL}/api/analyses",
            headers=headers,
            json={"job_description": "Test job"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ POST /api/analyses returns 401 for unauthenticated request")


# ==================== AUTH ENDPOINTS (AUTHENTICATED) ====================

class TestAuthenticatedAccess:
    """Tests for authenticated access with valid session."""
    
    def test_auth_me_with_valid_session(self, api_client, test_user_and_session):
        """With valid session_token, GET /api/auth/me returns user data."""
        headers = {
            "Authorization": f"Bearer {test_user_and_session['session_token']}",
            "Content-Type": "application/json"
        }
        response = api_client.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Verify user data structure
        assert "user_id" in data
        assert "email" in data
        assert "name" in data
        assert data["user_id"] == test_user_and_session["user_id"]
        assert data["email"] == test_user_and_session["email"]
        
        # Verify no _id field leaked
        assert "_id" not in data, "MongoDB _id should not be in response"
        print(f"✓ /api/auth/me returns user data: {data['name']}")
    
    def test_expired_session_returns_401(self, api_client, expired_session):
        """An expired session_token returns 401."""
        headers = {
            "Authorization": f"Bearer {expired_session}",
            "Content-Type": "application/json"
        }
        response = api_client.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 401, f"Expected 401 for expired session, got {response.status_code}"
        print("✓ Expired session correctly returns 401")


# ==================== PROFILE ENDPOINTS ====================

class TestProfileEndpoints:
    """Profile CRUD tests."""
    
    def test_get_profile(self, api_client, test_user_and_session):
        """GET /api/profile returns user profile."""
        headers = {
            "Authorization": f"Bearer {test_user_and_session['session_token']}",
            "Content-Type": "application/json"
        }
        response = api_client.get(f"{BASE_URL}/api/profile", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "user_id" in data
        assert "headline" in data
        assert "skills" in data
        assert "experience" in data
        
        # Verify no _id field leaked
        assert "_id" not in data, "MongoDB _id should not be in response"
        print(f"✓ GET /api/profile returns profile with headline: {data.get('headline')}")
    
    def test_update_profile(self, api_client, test_user_and_session):
        """PUT /api/profile updates name/headline/skills/experience."""
        headers = {
            "Authorization": f"Bearer {test_user_and_session['session_token']}",
            "Content-Type": "application/json"
        }
        
        update_payload = {
            "name": "Updated Test User",
            "headline": "Lead Product Designer",
            "skills": ["React", "Figma", "Product Strategy", "UX Research"],
            "experience": [
                {
                    "role": "Lead Product Designer",
                    "company": "TechCorp",
                    "period": "2023 - Present",
                    "description": "Leading design initiatives"
                },
                {
                    "role": "Senior Designer",
                    "company": "StartupXYZ",
                    "period": "2020 - 2023",
                    "description": "Built design system from scratch"
                }
            ]
        }
        
        response = api_client.put(
            f"{BASE_URL}/api/profile",
            headers=headers,
            json=update_payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Verify updates
        assert data["name"] == "Updated Test User"
        assert data["headline"] == "Lead Product Designer"
        assert len(data["skills"]) == 4
        assert len(data["experience"]) == 2
        
        # Verify no _id field leaked
        assert "_id" not in data, "MongoDB _id should not be in response"
        
        # Verify persistence with GET
        get_response = api_client.get(f"{BASE_URL}/api/profile", headers=headers)
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["headline"] == "Lead Product Designer"
        print("✓ PUT /api/profile updates and persists profile data")


# ==================== ANALYSIS ENDPOINTS ====================

class TestAnalysisEndpoints:
    """Analysis CRUD tests with GPT-5.2 integration."""
    
    def test_create_analysis_returns_report(self, api_client, test_user_and_session):
        """POST /api/analyses with job_description returns generated markdown report."""
        headers = {
            "Authorization": f"Bearer {test_user_and_session['session_token']}",
            "Content-Type": "application/json"
        }
        
        job_description = """
        Senior Product Designer - TechCorp
        
        We're looking for a Senior Product Designer to join our team.
        
        Requirements:
        - 5+ years of product design experience
        - Proficiency in Figma and design systems
        - Experience with user research and usability testing
        - Strong communication skills
        - Experience working with cross-functional teams
        
        Nice to have:
        - Experience with React or frontend development
        - Background in B2B SaaS products
        """
        
        payload = {
            "job_description": job_description,
            "job_title": "Senior Product Designer at TechCorp"
        }
        
        # Allow up to 90s for LLM call
        response = api_client.post(
            f"{BASE_URL}/api/analyses",
            headers=headers,
            json=payload,
            timeout=90
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text[:500]}"
        
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert "user_id" in data
        assert "job_title" in data
        assert "job_description" in data
        assert "report_markdown" in data
        assert "created_at" in data
        
        # Verify no _id field leaked
        assert "_id" not in data, "MongoDB _id should not be in response"
        
        # Verify report contains required sections
        report = data["report_markdown"]
        required_sections = ["Radiografía", "Gap", "Optimización", "Insider", "Estrategia"]
        for section in required_sections:
            assert section.lower() in report.lower(), f"Report missing section: {section}"
        
        print(f"✓ POST /api/analyses created analysis with id: {data['id']}")
        print(f"  Report length: {len(report)} chars")
        
        # Store analysis_id for subsequent tests
        return data["id"]
    
    def test_list_analyses(self, api_client, test_user_and_session):
        """GET /api/analyses returns list of prior analyses."""
        headers = {
            "Authorization": f"Bearer {test_user_and_session['session_token']}",
            "Content-Type": "application/json"
        }
        
        response = api_client.get(f"{BASE_URL}/api/analyses", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list of analyses"
        
        # Verify no _id field in any item
        for item in data:
            assert "_id" not in item, "MongoDB _id should not be in response"
        
        print(f"✓ GET /api/analyses returns {len(data)} analyses")
    
    def test_get_single_analysis(self, api_client, test_user_and_session, db):
        """GET /api/analyses/{id} returns single analysis."""
        headers = {
            "Authorization": f"Bearer {test_user_and_session['session_token']}",
            "Content-Type": "application/json"
        }
        
        # First get list to find an analysis id
        list_response = api_client.get(f"{BASE_URL}/api/analyses", headers=headers)
        analyses = list_response.json()
        
        if not analyses:
            pytest.skip("No analyses found to test GET single")
        
        analysis_id = analyses[0]["id"]
        
        response = api_client.get(f"{BASE_URL}/api/analyses/{analysis_id}", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["id"] == analysis_id
        assert "_id" not in data, "MongoDB _id should not be in response"
        
        print(f"✓ GET /api/analyses/{analysis_id} returns analysis")
    
    def test_delete_analysis(self, api_client, test_user_and_session, db):
        """DELETE /api/analyses/{id} deletes the analysis."""
        headers = {
            "Authorization": f"Bearer {test_user_and_session['session_token']}",
            "Content-Type": "application/json"
        }
        
        # First create an analysis to delete
        payload = {
            "job_description": "Test job for deletion - Software Engineer role",
            "job_title": "Test Delete Analysis"
        }
        
        create_response = api_client.post(
            f"{BASE_URL}/api/analyses",
            headers=headers,
            json=payload,
            timeout=90
        )
        
        if create_response.status_code != 200:
            pytest.skip(f"Could not create analysis for delete test: {create_response.text[:200]}")
        
        analysis_id = create_response.json()["id"]
        
        # Delete the analysis
        delete_response = api_client.delete(
            f"{BASE_URL}/api/analyses/{analysis_id}",
            headers=headers
        )
        assert delete_response.status_code == 200, f"Expected 200, got {delete_response.status_code}"
        
        # Verify deletion with GET
        get_response = api_client.get(
            f"{BASE_URL}/api/analyses/{analysis_id}",
            headers=headers
        )
        assert get_response.status_code == 404, "Deleted analysis should return 404"
        
        print(f"✓ DELETE /api/analyses/{analysis_id} successfully deleted")


# ==================== CV UPLOAD ENDPOINT ====================

class TestCVUpload:
    """CV upload and parsing tests with GPT-5.2 integration."""
    
    def _create_test_pdf(self):
        """Create a minimal valid PDF with CV content."""
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        
        # Add CV content
        cv_text = """
        Juan Perez
        Senior Product Designer
        
        Skills: React, Figma, Product Strategy, User Research, Design Systems
        
        Experience:
        - Designer at Atlas (2022-2024): Led design system development
        - UX Designer at StartupXYZ (2020-2022): Built mobile app from scratch
        """
        
        # Write text to PDF
        text_object = c.beginText(50, 750)
        text_object.setFont("Helvetica", 12)
        for line in cv_text.strip().split('\n'):
            text_object.textLine(line.strip())
        c.drawText(text_object)
        c.save()
        
        buffer.seek(0)
        return buffer
    
    def test_upload_cv_parses_profile(self, api_client, test_user_and_session):
        """POST /api/profile/upload-cv with PDF returns updated profile with parsed fields."""
        headers = {
            "Authorization": f"Bearer {test_user_and_session['session_token']}"
        }
        
        # Create test PDF
        pdf_buffer = self._create_test_pdf()
        
        files = {
            "file": ("test_cv.pdf", pdf_buffer, "application/pdf")
        }
        
        # Allow up to 90s for LLM call
        response = requests.post(
            f"{BASE_URL}/api/profile/upload-cv",
            headers=headers,
            files=files,
            timeout=90
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text[:500]}"
        
        data = response.json()
        
        # Verify profile structure
        assert "user_id" in data
        assert "name" in data
        assert "headline" in data
        assert "skills" in data
        assert "experience" in data
        
        # Verify no _id field leaked
        assert "_id" not in data, "MongoDB _id should not be in response"
        
        # Verify some parsing happened (skills should be populated)
        assert isinstance(data["skills"], list)
        
        print(f"✓ POST /api/profile/upload-cv parsed CV successfully")
        print(f"  Name: {data.get('name')}")
        print(f"  Headline: {data.get('headline')}")
        print(f"  Skills: {data.get('skills')[:5]}...")


# ==================== LOGOUT ENDPOINT ====================

class TestLogout:
    """Logout endpoint tests."""
    
    def test_logout_deletes_session(self, api_client, db, test_user_and_session):
        """POST /api/auth/logout with valid session deletes session server-side."""
        # Create a separate session for logout test
        timestamp = int(datetime.now().timestamp() * 1000)
        logout_token = f"TEST_logout_session_{timestamp}"
        
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        session_doc = {
            "user_id": test_user_and_session["user_id"],
            "session_token": logout_token,
            "expires_at": expires_at.isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        db.user_sessions.insert_one(session_doc)
        
        # Verify session exists
        session = db.user_sessions.find_one({"session_token": logout_token})
        assert session is not None, "Session should exist before logout"
        
        # Logout
        headers = {
            "Authorization": f"Bearer {logout_token}",
            "Content-Type": "application/json"
        }
        response = api_client.post(f"{BASE_URL}/api/auth/logout", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Verify session deleted
        session_after = db.user_sessions.find_one({"session_token": logout_token})
        assert session_after is None, "Session should be deleted after logout"
        
        print("✓ POST /api/auth/logout deletes session server-side")


# ==================== NO _ID LEAK VERIFICATION ====================

class TestNoMongoIdLeak:
    """Verify no response leaks MongoDB's _id field."""
    
    def test_auth_me_no_id_leak(self, api_client, test_user_and_session):
        """Verify /api/auth/me doesn't leak _id."""
        headers = {"Authorization": f"Bearer {test_user_and_session['session_token']}"}
        response = api_client.get(f"{BASE_URL}/api/auth/me", headers=headers)
        data = response.json()
        assert "_id" not in data
        print("✓ /api/auth/me does not leak _id")
    
    def test_profile_no_id_leak(self, api_client, test_user_and_session):
        """Verify /api/profile doesn't leak _id."""
        headers = {"Authorization": f"Bearer {test_user_and_session['session_token']}"}
        response = api_client.get(f"{BASE_URL}/api/profile", headers=headers)
        data = response.json()
        assert "_id" not in data
        print("✓ /api/profile does not leak _id")
    
    def test_analyses_list_no_id_leak(self, api_client, test_user_and_session):
        """Verify /api/analyses list doesn't leak _id."""
        headers = {"Authorization": f"Bearer {test_user_and_session['session_token']}"}
        response = api_client.get(f"{BASE_URL}/api/analyses", headers=headers)
        data = response.json()
        for item in data:
            assert "_id" not in item
        print("✓ /api/analyses list does not leak _id")
