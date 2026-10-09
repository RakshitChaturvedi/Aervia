"""
Unit and Integration tests for Phase 3:
- JWT Authentication & 4-Tier RBAC
- Enterprise Security Headers & CORS
- Distributed Caching & Rate Limiting
- System Diagnostics (/api/health)
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth import create_access_token, decode_access_token, hash_password, verify_password
from app.redis_client import set_cache, get_cache, check_rate_limit, get_cache_status
from app.routers.auth import seed_default_users

seed_default_users()
client = TestClient(app)


def test_password_hashing():
    raw_pwd = "SecurePassword2026!"
    hashed = hash_password(raw_pwd)
    assert hashed != raw_pwd
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_encode_decode():
    data = {"sub": "999", "email": "test@aervia.gov.in", "role": "city_officer"}
    token = create_access_token(data)
    decoded = decode_access_token(token)
    assert decoded["sub"] == "999"
    assert decoded["email"] == "test@aervia.gov.in"
    assert decoded["role"] == "city_officer"


def test_health_endpoint():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "database" in data
    assert "cache" in data
    assert data["data_sovereignty"]["hosting_region"] == "ap-south-1 (Mumbai, India)"


def test_security_headers():
    resp = client.get("/")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["x-data-sovereignty-region"] == "ap-south-1 (Mumbai, India)"


def test_rbac_login_flow():
    # Login as GHMC officer
    login_resp = client.post("/api/auth/login", json={
        "email": "officer@ghmc.gov.in",
        "password": "Officer123!"
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    assert login_resp.json()["role"] == "city_officer"

    # Verify profile with token
    headers = {"Authorization": f"Bearer {token}"}
    me_resp = client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "officer@ghmc.gov.in"
    assert me_resp.json()["department"] == "GHMC Environmental Wing"

    # Test role verification endpoint
    role_check = client.get("/api/auth/verify-role/city_officer", headers=headers)
    assert role_check.status_code == 200
    assert role_check.json()["access_granted"] is True


def test_redis_cache_and_rate_limiter():
    # Test caching set & get
    set_cache("pytest_cache_key", {"aqi": 88, "status": "Moderate"}, ttl_seconds=60)
    cached = get_cache("pytest_cache_key")
    assert cached is not None
    assert cached["aqi"] == 88

    # Test sliding window rate limit
    ip = "192.168.1.100"
    allowed1, rem1, _ = check_rate_limit(ip, max_requests=2, window_seconds=60)
    assert allowed1 is True
    allowed2, rem2, _ = check_rate_limit(ip, max_requests=2, window_seconds=60)
    assert allowed2 is True
    allowed3, rem3, _ = check_rate_limit(ip, max_requests=2, window_seconds=60)
    assert allowed3 is False  # Limit exceeded
