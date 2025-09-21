from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
import httpx
import os
from typing import Optional
import uvicorn
import secrets
from dotenv import load_dotenv
load_dotenv()
app = FastAPI(title="Google Sign-In Test App")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5175", "http://127.0.0.1:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8001/auth/callback/google"

# In-memory storage for state (use Redis/database in production)
oauth_states = {}

async def verify_google_token(token: str) -> Optional[dict]:
    """Verify Google ID token and return user info"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
            )
            if response.status_code == 200:
                return response.json()
            return None
    except Exception as e:
        print(f"Error verifying token: {e}")
        return None

@app.get("/")
async def root():
    return {"message": "Google Sign-In Test API"}

@app.get("/auth/google")
async def google_auth():
    """Initiate Google OAuth flow"""
    state = secrets.token_urlsafe(32)
    oauth_states[state] = True
    
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"scope=openid%20email%20profile&"
        f"response_type=code&"
        f"state={state}"
    )
    
    return RedirectResponse(url=auth_url)

@app.get("/auth/callback/google")
async def google_callback(request: Request):
    """Handle Google OAuth callback"""
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    
    # Verify state parameter
    if not state or state not in oauth_states:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    # Remove used state
    del oauth_states[state]
    
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not provided")
    
    # Exchange code for tokens
    token_data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data=token_data
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange code for tokens")
        
        tokens = response.json()
        access_token = tokens.get("access_token")
        id_token = tokens.get("id_token")
        
        if not id_token:
            raise HTTPException(status_code=400, detail="No ID token received")
        
        # Get user info
        user_info = await verify_google_token(id_token)
        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to verify user")
        
        # Redirect to frontend with user info
        frontend_url = f"http://localhost:5175/welcome?email={user_info.get('email')}&name={user_info.get('name')}&picture={user_info.get('picture', '')}"
        return RedirectResponse(url=frontend_url)

@app.get("/api/user")
async def get_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get user information from Google token"""
    token = credentials.credentials
    user_info = await verify_google_token(token)
    
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return {
        "email": user_info.get("email"),
        "name": user_info.get("name"),
        "picture": user_info.get("picture")
    }

@app.post("/api/verify-token")
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify Google token and return user info"""
    token = credentials.credentials
    user_info = await verify_google_token(token)
    
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return {
        "valid": True,
        "user": {
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "picture": user_info.get("picture")
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
