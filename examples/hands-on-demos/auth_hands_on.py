"""
Authentication & Authorization - YOUR Hands-On Implementation

YOU will implement these 3 critical patterns step by step:
1. JWT Token Management (access + refresh tokens)
2. Role-Based Access Control (RBAC)
3. API Key Authentication (service-to-service)

I'll guide, YOU code!
"""

import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

import jwt

# Required packages: PyJWT cryptography


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


class UserRole(str, Enum):
    USER = "user"
    PREMIUM = "premium"
    ADMIN = "admin"


class JWTManager:
    """
    PATTERN 1: JWT Token Management - YOU IMPLEMENT THIS

    Interview Question: "Implement JWT authentication with refresh tokens"

    YOUR TASK: Implement the methods below
    """

    def __init__(self):
        self.access_secret = "your-access-secret-key"
        self.refresh_secret = "your-refresh-secret-key"
        self.access_token_expire = 15  # minutes
        self.refresh_token_expire = 7 * 24 * 60  # 7 days in minutes
        self.algorithm = "HS256"

    def create_access_token(
        self, user_id: str, role: UserRole, permissions: list[str]
    ) -> str:
        """
        YOUR TASK: Create JWT access token

        Should contain:
        - user_id, role, permissions
        - Short expiration (15 minutes)
        - Token type
        """
        print(f"🔑 Creating access token for user {user_id}")
        now = datetime.utcnow()
        payload = {
            "user_id": user_id,
            "role": role.value,
            "permissions": permissions,
            "token_type": TokenType.ACCESS.value,
            "iat": now,  # issued at
            "exp": now + timedelta(minutes=self.access_token_expire),
        }

        token = jwt.encode(payload, self.access_secret, algorithm=self.algorithm)
        print(
            f"   ✅ Access token created (expires in {self.access_token_expire} mins)"
        )
        return token

    def create_refresh_token(self, user_id: str) -> str:
        now = datetime.utcnow()
        payload = {
            "user_id": user_id,
            "token_type": TokenType.REFRESH.value,
            "iat": now,  # issued at
            "exp": now + timedelta(minutes=self.refresh_token_expire),
        }

        token = jwt.encode(payload, self.refresh_secret, algorithm=self.algorithm)
        print(
            f"   ✅ Refresh token created (expires in {self.refresh_token_expire//60//24} days)"
        )
        return token

    def verify_access_token(self, token: str) -> Optional[dict[str, Any]]:
        """
        YOUR TASK: Verify and decode access token

        Steps:
        1. Use jwt.decode() with access_secret
        2. Check token_type is ACCESS
        3. Return payload if valid, None if invalid
        """
        print("🔍 Verifying access token...")

        try:
            payload = jwt.decode(token, self.access_secret, algorithms=[self.algorithm])
            if payload.get("token_type") != TokenType.ACCESS.value:
                raise ValueError("Invalid token type")

            print("   ✅ Access token verified successfully")
            return payload

        except Exception as e:
            print(f"   ❌ Token verification failed: {e}")
            return None

    def verify_refresh_token(self, token: str) -> Optional[str]:
        """
        YOUR TASK: Verify refresh token and return user_id
        """
        print("🔄 Verifying refresh token...")

        try:
            payload = jwt.decode(
                token, self.refresh_secret, algorithms=[self.algorithm]
            )

            # Validate token type
            if payload.get("token_type") != TokenType.REFRESH.value:
                raise ValueError("Invalid token type")

            user_id = payload.get("user_id")
            print(f"   ✅ Refresh token verified for user {user_id}")
            return user_id

        except Exception as e:
            print(f"   ❌ Refresh token verification failed: {e}")
            return None

    def refresh_tokens(self, refresh_token: str) -> Optional[dict[str, str]]:
        """
        YOUR TASK: Exchange refresh token for new tokens

        Flow:
        1. Verify refresh token
        2. Get user info
        3. Create new access + refresh tokens
        4. Return both
        """
        print("🔄 Refreshing tokens...")

        # Step 1: Verify refresh token
        user_id = self.verify_refresh_token(refresh_token)
        if not user_id:
            return None

        # Step 2: Get user info (from database)
        user_store = UserStore()
        user = user_store.get_user(user_id)
        if not user:
            return None

        # Step 3: Create new tokens (token rotation)
        new_access_token = self.create_access_token(
            user_id, user["role"], user["permissions"]
        )
        new_refresh_token = self.create_refresh_token(user_id)

        print("   ✅ Tokens refreshed successfully")

        return {"access_token": new_access_token, "refresh_token": new_refresh_token}


# Mock user database for testing
class UserStore:
    def __init__(self):
        self.users = {
            "123": {
                "id": "123",
                "username": "john_doe",
                "role": UserRole.USER,
                "permissions": ["read", "write"],
            }
        }

    def get_user(self, user_id: str) -> Optional[dict[str, Any]]:
        return self.users.get(user_id)


async def test_jwt_tokens():
    """Test YOUR JWT implementation."""
    print("🧪 Testing YOUR JWT Implementation")
    print("=" * 50)

    jwt_manager = JWTManager()
    user_store = UserStore()

    user_id = "123"
    user = user_store.get_user(user_id)

    if not user:
        print("❌ User not found")
        return

    print(f"Testing with user: {user['username']}")
    print()

    # Test token creation
    print("1. Creating tokens...")
    access_token = jwt_manager.create_access_token(
        user_id, user["role"], user["permissions"]
    )
    refresh_token = jwt_manager.create_refresh_token(user_id)
    print(f"   Access token: {access_token}")
    print(f"   Refresh token: {refresh_token}")
    print()

    # Test verification
    print("2. Verifying access token...")
    payload = jwt_manager.verify_access_token(access_token)
    print(f"   Result: {payload}")
    print()

    # Test refresh
    print("3. Refreshing tokens...")
    new_tokens = jwt_manager.refresh_tokens(refresh_token)
    print(f"   Result: {new_tokens}")
    print()


class Permission(str, Enum):
    """Granular permissions for fine-grained access control."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ANALYZE_IMAGE = "analyze_image"
    VIEW_ANALYTICS = "view_analytics"
    MANAGE_USERS = "manage_users"


class RBACManager:
    """
    PATTERN 2: Role-Based Access Control (RBAC) - YOU IMPLEMENT THIS

    Interview Question: "How do you implement role-based permissions?"

    YOUR TASK: Implement permission checking and decorators
    """

    def __init__(self):
        # Define role permissions (normally stored in database)
        self.role_permissions = {
            UserRole.USER: [
                Permission.READ,
                Permission.ANALYZE_IMAGE,
            ],
            UserRole.PREMIUM: [
                Permission.READ,
                Permission.WRITE,
                Permission.ANALYZE_IMAGE,
                Permission.VIEW_ANALYTICS,
            ],
            UserRole.ADMIN: [
                Permission.READ,
                Permission.WRITE,
                Permission.DELETE,
                Permission.ANALYZE_IMAGE,
                Permission.VIEW_ANALYTICS,
                Permission.MANAGE_USERS,
            ],
        }

        pass

    def has_permission(
        self, user_role: UserRole, required_permission: Permission
    ) -> bool:
        """
        YOUR TASK: Check if user role has required permission

        This is the core RBAC logic!
        """
        print(
            f"🔐 Checking if role {user_role} has permission {required_permission}..."
        )

        # Get permissions for the role
        user_permissions = self.role_permissions.get(user_role, [])

        # Check if permission exists
        has_perm = required_permission in user_permissions

        if has_perm:
            print("   ✅ Access granted")
        else:
            print("   ❌ Access denied")

        return has_perm

    def require_permission(self, required_permission: Permission):
        """
        YOUR TASK: Create decorator to protect functions

        This decorator will:
        1. Check if user has required permission
        2. Allow or deny access to the function
        """

        def decorator(func):
            def wrapper(*args, **kwargs):
                # TODO: YOU implement permission checking decorator
                # Get user role from function arguments
                user_role = kwargs.get("user_role", UserRole.USER)

                # Check if user has required permission
                if not self.has_permission(user_role, required_permission):
                    return {
                        "error": "Permission denied",
                        "required": required_permission.value,
                        "user_role": user_role.value,
                    }

                # Permissin granted - call the original function
                return func(*args, **kwargs)

            return wrapper

        return decorator


# Protected endpoint examples (YOU'LL implement the decorator logic)
rbac = RBACManager()


@rbac.require_permission(Permission.ANALYZE_IMAGE)
def analyze_image_endpoint(image_data: bytes, user_role: UserRole = UserRole.USER):
    """Protected endpoint - requires analyze_image permission."""
    return {
        "analysis": ["car", "person", "building"],
        "confidence": 0.95,
        "processed_by": user_role.value,
    }


@rbac.require_permission(Permission.VIEW_ANALYTICS)
def view_analytics_endpoint(user_role: UserRole = UserRole.USER):
    """Premium feature - requires view_analytics permission."""
    return {"total_analyses": 1234, "success_rate": 0.98, "avg_processing_time": 1.2}


async def test_rbac_system():
    """Test YOUR RBAC implementation."""
    print("🧪 Testing YOUR RBAC Implementation")
    print("=" * 50)

    # Test different user roles
    test_users = [
        ("Regular User", UserRole.USER),
        ("Premium User", UserRole.PREMIUM),
        ("Admin User", UserRole.ADMIN),
    ]

    for user_name, user_role in test_users:
        print(f"\n👤 Testing as {user_name} (role: {user_role.value})")
        print("-" * 40)

        # Test image analysis access
        print("1. Accessing image analysis endpoint:")
        result1 = analyze_image_endpoint(b"fake_image", user_role=user_role)
        print(f"   Result: {result1}")

        # Test analytics access
        print("2. Accessing analytics endpoint:")
        result2 = view_analytics_endpoint(user_role=user_role)
        print(f"   Result: {result2}")

        print()


if __name__ == "__main__":
    print("🎯 Authentication & Authorization - YOUR Complete Implementation")
    print("=" * 70)

    # Test JWT system
    asyncio.run(test_jwt_tokens())

    print("\n" + "=" * 70 + "\n")

    # Test RBAC system
    asyncio.run(test_rbac_system())
