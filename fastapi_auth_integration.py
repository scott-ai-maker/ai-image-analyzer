"""
🎯 FastAPI Authentication Integration - Hands-on Implementation

This file integrates your JWT + RBAC authentication system with FastAPI.
YOU'LL replace the simple API key auth with enterprise-grade JWT + RBAC.

Key concepts you'll implement:
1. FastAPI dependency injection for authentication
2. JWT token extraction from Authorization headers
3. Role-based endpoint protection
4. Error handling for authentication failures
5. Integration with existing FastAPI routes

This shows how real production APIs handle authentication!
"""

import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Annotated
from uuid import uuid4

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import jwt

# Import your authentication classes from the hands-on implementation
# (In production, these would be separate modules)
from auth_hands_on import JWTManager, RBACManager, UserRole, Permission


# ============================================================================
# 🔧 FASTAPI AUTHENTICATION MODELS
# ============================================================================

class TokenResponse(BaseModel):
    """Response model for token endpoints."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class LoginRequest(BaseModel):
    """Login request payload."""
    username: str
    password: str


class RefreshRequest(BaseModel):
    """Token refresh request payload."""
    refresh_token: str


class UserInfo(BaseModel):
    """Current user information."""
    user_id: str
    username: str
    role: UserRole
    permissions: List[Permission]


# ============================================================================
# 🔐 AUTHENTICATION DEPENDENCIES 
# ============================================================================

# Initialize authentication managers
jwt_manager = JWTManager()
rbac_manager = RBACManager()

# FastAPI security scheme
security = HTTPBearer(auto_error=False)

# Mock user database (in production, use real database)
MOCK_USERS = {
    "john_doe": {
        "user_id": "123", 
        "password": "password123", 
        "role": UserRole.USER
    },
    "premium_user": {
        "user_id": "456", 
        "password": "premium123", 
        "role": UserRole.PREMIUM
    },
    "admin_user": {
        "user_id": "789", 
        "password": "admin123", 
        "role": UserRole.ADMIN
    }
}


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict:
    """
    YOUR TASK: Extract and verify JWT token from Authorization header
    
    This dependency will:
    1. Extract JWT token from Authorization header
    2. Verify and decode the token
    3. Return user information for downstream handlers
    4. Raise HTTPException for invalid tokens
    """
    # TODO: YOU implement JWT token extraction and verification
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = credentials.credentials
    
    # Verify the JWT token using your JWTManager
    try:
        # TODO: Use jwt_manager.verify_access_token() here
        payload = jwt_manager.verify_access_token(token)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


def require_permission(required_permission: Permission):
    """
    YOUR TASK: Create FastAPI dependency for permission checking
    
    This returns a FastAPI dependency that:
    1. Gets current user from JWT token
    2. Checks if user has required permission
    3. Allows or denies access to endpoint
    """
    def permission_dependency(
        current_user: Dict = Depends(get_current_user)
    ) -> Dict:
        # TODO: YOU implement permission checking
        user_role = UserRole(current_user.get("role"))
        
        # Check permission using RBAC manager
        if not rbac_manager.has_permission(user_role, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Insufficient permissions",
                    "required": required_permission.value,
                    "user_role": user_role.value,
                    "user_id": current_user.get("user_id"),
                }
            )
        
        return current_user
    
    return permission_dependency


def require_role(required_role: UserRole):
    """
    YOUR TASK: Create FastAPI dependency for role checking
    
    Alternative to permission-based checking - direct role requirement.
    """
    def role_dependency(
        current_user: Dict = Depends(get_current_user)
    ) -> Dict:
        # TODO: YOU implement role checking
        user_role = UserRole(current_user.get("role"))
        
        # Check if user has required role or higher
        role_hierarchy = {
            UserRole.USER: 1,
            UserRole.PREMIUM: 2, 
            UserRole.ADMIN: 3
        }
        
        if role_hierarchy[user_role] < role_hierarchy[required_role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Insufficient role",
                    "required": required_role.value,
                    "user_role": user_role.value,
                    "user_id": current_user.get("user_id"),
                }
            )
        
        return current_user
    
    return role_dependency


# ============================================================================
# 🚀 FASTAPI APPLICATION WITH AUTHENTICATION
# ============================================================================

app = FastAPI(
    title="AI Image Analyzer with JWT Authentication",
    description="Enterprise-grade image analyzer with JWT + RBAC authentication",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# 🔑 AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    """
    YOUR TASK: Implement login endpoint
    
    This endpoint will:
    1. Validate username/password against mock database
    2. Create JWT access and refresh tokens
    3. Return tokens to client
    """
    # TODO: YOU implement login logic
    
    # Check if user exists and password is correct
    user = MOCK_USERS.get(request.username)
    if not user or user["password"] != request.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Get user permissions based on role
    user_permissions = rbac_manager.role_permissions.get(user["role"], [])
    permission_strings = [perm.value for perm in user_permissions]
    
    # Create JWT tokens using your JWTManager
    access_token = jwt_manager.create_access_token(
        user_id=user["user_id"],
        role=user["role"],
        permissions=permission_strings
    )
    
    refresh_token = jwt_manager.create_refresh_token(user["user_id"])
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=15 * 60  # 15 minutes
    )


@app.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest) -> TokenResponse:
    """
    YOUR TASK: Implement token refresh endpoint
    
    This endpoint will:
    1. Verify the refresh token
    2. Generate new access and refresh tokens
    3. Return new tokens to client
    """
    # TODO: YOU implement token refresh logic
    try:
        result = jwt_manager.refresh_tokens(request.refresh_token)
        if result is None:
            raise ValueError("Token refresh failed")
        
        return TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            expires_in=15 * 60  # 15 minutes
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}"
        )


@app.get("/auth/me", response_model=UserInfo)
async def get_current_user_info(
    current_user: Dict = Depends(get_current_user)
) -> UserInfo:
    """Get current authenticated user information."""
    user_role = UserRole(current_user["role"])
    user_permissions = rbac_manager.role_permissions.get(user_role, [])
    
    # Find username from user_id (in production, query database)
    username = None
    for uname, udata in MOCK_USERS.items():
        if udata["user_id"] == current_user["user_id"]:
            username = uname
            break
    
    return UserInfo(
        user_id=current_user["user_id"],
        username=username or "unknown",
        role=user_role,
        permissions=user_permissions
    )


# ============================================================================
# 🖼️ PROTECTED IMAGE ANALYSIS ENDPOINTS
# ============================================================================

@app.post("/api/v1/analyze/basic")
async def analyze_image_basic(
    image_url: str,
    current_user: Dict = Depends(require_permission(Permission.ANALYZE_IMAGE))
):
    """
    Basic image analysis - requires ANALYZE_IMAGE permission.
    Available to: USER, PREMIUM, ADMIN
    """
    return {
        "message": "Image analysis completed",
        "image_url": image_url,
        "analysis": ["car", "person", "building"],
        "confidence": 0.95,
        "processed_by": current_user["user_id"],
        "user_role": current_user["role"]
    }


@app.get("/api/v1/analytics/dashboard")
async def get_analytics_dashboard(
    current_user: Dict = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """
    Analytics dashboard - requires VIEW_ANALYTICS permission.
    Available to: PREMIUM, ADMIN only
    """
    return {
        "message": "Analytics dashboard data",
        "total_analyses": 1234,
        "success_rate": 0.98,
        "avg_processing_time": 1.2,
        "accessed_by": current_user["user_id"],
        "user_role": current_user["role"]
    }


@app.delete("/api/v1/admin/cleanup")
async def admin_cleanup(
    current_user: Dict = Depends(require_role(UserRole.ADMIN))
):
    """
    Admin cleanup operation - requires ADMIN role.
    Available to: ADMIN only
    """
    return {
        "message": "Admin cleanup completed",
        "cleaned_records": 42,
        "executed_by": current_user["user_id"],
        "user_role": current_user["role"]
    }


@app.get("/api/v1/premium/advanced-analysis")
async def premium_analysis(
    current_user: Dict = Depends(require_role(UserRole.PREMIUM))
):
    """
    Premium analysis features - requires PREMIUM role or higher.
    Available to: PREMIUM, ADMIN
    """
    return {
        "message": "Premium analysis features",
        "advanced_features": ["facial_recognition", "scene_understanding", "ocr"],
        "processing_priority": "high",
        "accessed_by": current_user["user_id"],
        "user_role": current_user["role"]
    }


# ============================================================================
# 🏥 HEALTH CHECK (PUBLIC)  
# ============================================================================

@app.get("/health")
async def health_check():
    """Public health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "AI Image Analyzer with JWT Auth",
        "version": "2.0.0"
    }


# ============================================================================
# 🧪 TESTING INSTRUCTIONS
# ============================================================================

if __name__ == "__main__":
    print("""
🎯 FastAPI + JWT Authentication Integration Ready!
===============================================

YOUR TASKS TO COMPLETE:
1. ✅ get_current_user() - Extract JWT from headers
2. ✅ require_permission() - Check user permissions  
3. ✅ require_role() - Check user roles
4. ✅ login endpoint - Create JWT tokens
5. ✅ refresh endpoint - Rotate tokens

TESTING COMMANDS:
==================

1. Start the server:
   uvicorn fastapi_auth_integration:app --reload --port 8001

2. Test login:
   curl -X POST "http://localhost:8001/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "john_doe", "password": "password123"}'

3. Test protected endpoint (use token from login):
   curl -X POST "http://localhost:8001/api/v1/analyze/basic?image_url=test.jpg" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"

4. Test permission-based access:
   - USER: Can access /analyze/basic
   - PREMIUM: Can access /analytics/dashboard  
   - ADMIN: Can access /admin/cleanup

5. Test different user roles:
   - Username: john_doe (USER role)
   - Username: premium_user (PREMIUM role) 
   - Username: admin_user (ADMIN role)

🚀 This shows how production APIs integrate JWT + RBAC!
    """)