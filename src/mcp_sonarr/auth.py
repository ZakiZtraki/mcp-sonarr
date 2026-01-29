"""OAuth 2.0 Authentication for MCP Server.

This module implements OAuth 2.0 Authorization Code flow for ChatGPT and other
OAuth-compatible clients. It provides:

- Authorization endpoint for user authentication
- Token endpoint for code-to-token exchange
- JWT-based access tokens
- Authentication middleware for protected endpoints

Environment Variables:
    OAUTH_CLIENT_ID: OAuth client ID (required for OAuth)
    OAUTH_CLIENT_SECRET: OAuth client secret (required for OAuth)
    OAUTH_JWT_SECRET: Secret key for signing JWTs (auto-generated if not set)
    OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES: Token expiry in minutes (default: 60)
    OAUTH_AUTH_PASSWORD: Password for the authorization form (required for OAuth)
"""

import html
import os
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

from jose import jwt, JWTError
from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class OAuthConfig:
    """OAuth 2.0 Configuration."""

    def __init__(self):
        self.client_id = os.getenv("OAUTH_CLIENT_ID")
        self.client_secret = os.getenv("OAUTH_CLIENT_SECRET")
        self.jwt_secret = os.getenv("OAUTH_JWT_SECRET") or secrets.token_urlsafe(32)
        self.jwt_algorithm = "HS256"
        self.access_token_expire_minutes = int(os.getenv("OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
        self.auth_password = os.getenv("OAUTH_AUTH_PASSWORD")

        # Fallback to simple Bearer token for backward compatibility
        self.simple_auth_token = os.getenv("MCP_AUTH_TOKEN")

    @property
    def oauth_enabled(self) -> bool:
        """Check if OAuth is properly configured."""
        return bool(self.client_id and self.client_secret and self.auth_password)

    @property
    def auth_enabled(self) -> bool:
        """Check if any authentication is enabled."""
        return self.oauth_enabled or bool(self.simple_auth_token)


# Global config instance
oauth_config = OAuthConfig()

# In-memory storage for authorization codes (use Redis/DB in production)
# Format: {code: {"client_id": str, "redirect_uri": str, "expires_at": datetime, "used": bool}}
_authorization_codes: dict[str, dict] = {}


def generate_authorization_code(client_id: str, redirect_uri: str) -> str:
    """Generate a new authorization code."""
    code = secrets.token_urlsafe(32)
    _authorization_codes[code] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
        "used": False,
    }
    # Clean up expired codes
    _cleanup_expired_codes()
    return code


def validate_authorization_code(code: str, client_id: str, redirect_uri: str) -> bool:
    """Validate an authorization code."""
    if code not in _authorization_codes:
        return False

    code_data = _authorization_codes[code]

    # Check if code is expired
    if datetime.now(timezone.utc) > code_data["expires_at"]:
        del _authorization_codes[code]
        return False

    # Check if code was already used
    if code_data["used"]:
        del _authorization_codes[code]
        return False

    # Validate client_id and redirect_uri
    if code_data["client_id"] != client_id:
        return False

    if code_data["redirect_uri"] != redirect_uri:
        return False

    # Mark code as used
    _authorization_codes[code]["used"] = True

    return True


def _cleanup_expired_codes():
    """Remove expired authorization codes."""
    now = datetime.now(timezone.utc)
    expired = [code for code, data in _authorization_codes.items() if now > data["expires_at"]]
    for code in expired:
        del _authorization_codes[code]


def create_access_token(client_id: str, scopes: list[str] = None) -> tuple[str, int]:
    """Create a JWT access token.

    Returns:
        Tuple of (token, expires_in_seconds)
    """
    expires_delta = timedelta(minutes=oauth_config.access_token_expire_minutes)
    expire = datetime.now(timezone.utc) + expires_delta

    payload = {
        "sub": client_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "scope": " ".join(scopes or ["full"]),
        "iss": "mcp-sonarr",
    }

    token = jwt.encode(
        payload,
        oauth_config.jwt_secret,
        algorithm=oauth_config.jwt_algorithm,
    )

    return token, int(expires_delta.total_seconds())


def verify_access_token(token: str) -> Optional[dict]:
    """Verify a JWT access token.

    Returns:
        Token claims if valid, None otherwise.
    """
    try:
        payload = jwt.decode(
            token,
            oauth_config.jwt_secret,
            algorithms=[oauth_config.jwt_algorithm],
        )
        return payload
    except JWTError as e:
        logger.debug(f"JWT verification failed: {e}")
        return None


def verify_password(password: str) -> bool:
    """Verify the authorization password."""
    if not oauth_config.auth_password:
        return False
    # Use constant-time comparison to prevent timing attacks
    return secrets.compare_digest(password, oauth_config.auth_password)


def verify_client_credentials(client_id: str, client_secret: str) -> bool:
    """Verify OAuth client credentials."""
    if not oauth_config.oauth_enabled:
        return False
    return secrets.compare_digest(client_id, oauth_config.client_id) and secrets.compare_digest(
        client_secret, oauth_config.client_secret
    )


# HTML template for authorization form
# Note: CSS braces are doubled ({{ and }}) to escape them for Python's .format()
AUTHORIZATION_FORM_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Authorize MCP Sonarr</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .container {{
            background: #fff;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            max-width: 400px;
            width: 100%;
        }}
        .logo {{
            text-align: center;
            margin-bottom: 24px;
        }}
        .logo svg {{
            width: 64px;
            height: 64px;
            fill: #e74c3c;
        }}
        h1 {{
            color: #333;
            font-size: 24px;
            text-align: center;
            margin-bottom: 8px;
        }}
        .subtitle {{
            color: #666;
            text-align: center;
            margin-bottom: 32px;
            font-size: 14px;
        }}
        .client-info {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 24px;
        }}
        .client-info p {{
            color: #555;
            font-size: 14px;
        }}
        .client-info strong {{
            color: #333;
        }}
        .form-group {{
            margin-bottom: 20px;
        }}
        label {{
            display: block;
            color: #333;
            font-weight: 500;
            margin-bottom: 8px;
            font-size: 14px;
        }}
        input[type="password"] {{
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e1e5e9;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.2s;
        }}
        input[type="password"]:focus {{
            outline: none;
            border-color: #e74c3c;
        }}
        .error {{
            background: #fee;
            border: 1px solid #fcc;
            color: #c00;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }}
        .buttons {{
            display: flex;
            gap: 12px;
        }}
        button {{
            flex: 1;
            padding: 14px 20px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.1s, box-shadow 0.2s;
        }}
        button:active {{
            transform: scale(0.98);
        }}
        .btn-authorize {{
            background: #e74c3c;
            color: white;
        }}
        .btn-authorize:hover {{
            box-shadow: 0 4px 12px rgba(231, 76, 60, 0.4);
        }}
        .btn-cancel {{
            background: #e1e5e9;
            color: #333;
        }}
        .btn-cancel:hover {{
            background: #d1d5d9;
        }}
        .permissions {{
            margin-bottom: 24px;
        }}
        .permissions h3 {{
            color: #333;
            font-size: 14px;
            margin-bottom: 12px;
        }}
        .permissions ul {{
            list-style: none;
            padding: 0;
        }}
        .permissions li {{
            color: #555;
            font-size: 14px;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .permissions li:last-child {{
            border-bottom: none;
        }}
        .permissions li::before {{
            content: "✓";
            color: #27ae60;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
        </div>
        <h1>Authorize MCP Sonarr</h1>
        <p class="subtitle">An application wants to access your Sonarr instance</p>

        <div class="client-info">
            <p><strong>Client ID:</strong> {client_id}</p>
        </div>

        <div class="permissions">
            <h3>This will allow the application to:</h3>
            <ul>
                <li>View your series library</li>
                <li>Add and remove series</li>
                <li>Search for episodes</li>
                <li>Manage download queue</li>
                <li>View system status</li>
            </ul>
        </div>

        {error_html}

        <form method="POST">
            <input type="hidden" name="client_id" value="{client_id}">
            <input type="hidden" name="redirect_uri" value="{redirect_uri}">
            <input type="hidden" name="state" value="{state}">
            <input type="hidden" name="response_type" value="{response_type}">

            <div class="form-group">
                <label for="password">Authorization Password</label>
                <input type="password" id="password" name="password" placeholder="Enter your password" required autofocus>
            </div>

            <div class="buttons">
                <button type="button" class="btn-cancel" onclick="window.location.href='{redirect_uri}?error=access_denied&amp;state={state}'">Cancel</button>
                <button type="submit" class="btn-authorize">Authorize</button>
            </div>
        </form>
    </div>
</body>
</html>
"""


async def oauth_authorize(request: Request) -> HTMLResponse | RedirectResponse:
    """OAuth 2.0 Authorization Endpoint.

    GET: Display authorization form
    POST: Process authorization and redirect with code
    """
    if not oauth_config.oauth_enabled:
        return JSONResponse(
            {
                "error": "oauth_not_configured",
                "error_description": "OAuth is not configured on this server",
            },
            status_code=501,
        )

    if request.method == "GET":
        # Extract OAuth parameters
        client_id = request.query_params.get("client_id", "")
        redirect_uri = request.query_params.get("redirect_uri", "")
        state = request.query_params.get("state", "")
        response_type = request.query_params.get("response_type", "code")

        # Validate client_id
        if client_id != oauth_config.client_id:
            return JSONResponse(
                {"error": "invalid_client", "error_description": "Unknown client_id"},
                status_code=400,
            )

        # Validate response_type
        if response_type != "code":
            return JSONResponse(
                {
                    "error": "unsupported_response_type",
                    "error_description": "Only 'code' response type is supported",
                },
                status_code=400,
            )

        # Display authorization form (escape user-provided values to prevent XSS)
        html_content = AUTHORIZATION_FORM_HTML.format(
            client_id=html.escape(client_id),
            redirect_uri=html.escape(redirect_uri),
            state=html.escape(state),
            response_type=html.escape(response_type),
            error_html="",
        )
        return HTMLResponse(html_content)

    elif request.method == "POST":
        # Process form submission
        form = await request.form()
        client_id = form.get("client_id", "")
        redirect_uri = form.get("redirect_uri", "")
        state = form.get("state", "")
        password = form.get("password", "")

        # Validate client_id
        if client_id != oauth_config.client_id:
            return JSONResponse(
                {"error": "invalid_client", "error_description": "Unknown client_id"},
                status_code=400,
            )

        # Verify password
        if not verify_password(password):
            # Re-display form with error (escape user-provided values to prevent XSS)
            html_content = AUTHORIZATION_FORM_HTML.format(
                client_id=html.escape(client_id),
                redirect_uri=html.escape(redirect_uri),
                state=html.escape(state),
                response_type="code",
                error_html='<div class="error">Invalid password. Please try again.</div>',
            )
            return HTMLResponse(html_content, status_code=401)

        # Generate authorization code
        code = generate_authorization_code(client_id, redirect_uri)

        # Redirect back to client with code
        params = {"code": code}
        if state:
            params["state"] = state

        redirect_url = f"{redirect_uri}?{urlencode(params)}"
        return RedirectResponse(url=redirect_url, status_code=302)


async def oauth_token(request: Request) -> JSONResponse:
    """OAuth 2.0 Token Endpoint.

    Exchanges authorization code for access token.
    """
    if not oauth_config.oauth_enabled:
        return JSONResponse(
            {
                "error": "oauth_not_configured",
                "error_description": "OAuth is not configured on this server",
            },
            status_code=501,
        )

    # Parse form data
    form = await request.form()
    grant_type = form.get("grant_type")
    code = form.get("code")
    redirect_uri = form.get("redirect_uri")
    client_id = form.get("client_id")
    client_secret = form.get("client_secret")

    # Validate grant type
    if grant_type != "authorization_code":
        return JSONResponse(
            {
                "error": "unsupported_grant_type",
                "error_description": "Only 'authorization_code' grant type is supported",
            },
            status_code=400,
        )

    # Validate client credentials
    if not verify_client_credentials(client_id, client_secret):
        return JSONResponse(
            {"error": "invalid_client", "error_description": "Invalid client credentials"},
            status_code=401,
        )

    # Validate authorization code
    if not validate_authorization_code(code, client_id, redirect_uri):
        return JSONResponse(
            {
                "error": "invalid_grant",
                "error_description": "Invalid or expired authorization code",
            },
            status_code=400,
        )

    # Generate access token
    access_token, expires_in = create_access_token(client_id)

    return JSONResponse(
        {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
        }
    )


async def oauth_metadata(request: Request) -> JSONResponse:
    """OAuth 2.0 Authorization Server Metadata (RFC 8414).

    Returns metadata about the OAuth server endpoints.
    """
    # Determine base URL from request
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.url.netloc)
    base_url = f"{scheme}://{host}"

    return JSONResponse(
        {
            "issuer": base_url,
            "authorization_endpoint": f"{base_url}/oauth/authorize",
            "token_endpoint": f"{base_url}/oauth/token",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "token_endpoint_auth_methods_supported": ["client_secret_post"],
            "scopes_supported": ["full"],
            "code_challenge_methods_supported": ["S256"],
        }
    )


class OAuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware supporting OAuth and simple Bearer tokens."""

    # Paths that don't require authentication
    EXEMPT_PATHS = {
        "/health",
        "/info",
        "/debug/series",
        "/oauth/authorize",
        "/oauth/token",
        "/.well-known/oauth-authorization-server",
    }

    async def dispatch(self, request: Request, call_next):
        # Skip auth for exempt paths
        path = request.url.path.rstrip("/")
        if path in self.EXEMPT_PATHS or path == "":
            return await call_next(request)

        # Skip if no auth is configured
        if not oauth_config.auth_enabled:
            return await call_next(request)

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                {
                    "error": "unauthorized",
                    "error_description": "Missing or invalid Authorization header",
                },
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer realm="mcp-sonarr"'},
            )

        token = auth_header[7:]  # Remove "Bearer " prefix

        # Try simple Bearer token first (backward compatibility)
        if oauth_config.simple_auth_token:
            if secrets.compare_digest(token, oauth_config.simple_auth_token):
                request.state.auth_claims = {"sub": "bearer-token", "scope": "full"}
                return await call_next(request)

        # Try JWT verification
        claims = verify_access_token(token)
        if claims:
            request.state.auth_claims = claims
            return await call_next(request)

        # Token is invalid
        return JSONResponse(
            {
                "error": "invalid_token",
                "error_description": "The access token is invalid or expired",
            },
            status_code=401,
            headers={"WWW-Authenticate": 'Bearer realm="mcp-sonarr", error="invalid_token"'},
        )
