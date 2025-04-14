# auth.py
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
import jwt
from database import SUPABASE_JWT_SECRET

security = HTTPBearer()

async def auth_middleware(request: Request, call_next):
    # Define public paths that don't require authentication
    public_paths = ["/login", "/signup", "/static"]
    
    # Check if the current path is in public paths
    current_path = request.url.path
    is_public_path = any(current_path.startswith(path) for path in public_paths)
    
    token = request.cookies.get("access_token")
    print(f"Cookie token: {token}")
    
    if token and token.startswith("Bearer "):
        token = token.split(" ")[1]  # Extract the actual token
        print(f"Extracted token: {token[:10]}...")
        request.headers.__dict__["_list"].append(
            (b"authorization", f"Bearer {token}".encode())
        )
    else:
        print("No valid token found in cookies")
        # If not a public path and no valid token, redirect to login
        if not is_public_path:
            print(f"Redirecting to login from {current_path}")
            return RedirectResponse("/login", status_code=303)
    
    response = await call_next(request)
    return response

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        # Remove 'Bearer ' prefix if present
        original_token = token
        if token.startswith("Bearer "):
            token = token.split(" ")[1]
        print(f"Original token: {original_token[:10]}...")
        print(f"Processed token: {token[:10]}...")
        
        # Add more flexible options for Supabase JWT validation
        payload = jwt.decode(
            token, 
            SUPABASE_JWT_SECRET, 
            algorithms=['HS256'], 
            options={
                "verify_signature": True,
                "verify_aud": False,
                "verify_iss": False,
                "verify_exp": True,
                "verify_iat": False,
                "verify_nbf": False,
                "leeway": 10  # Add leeway for clock skew
            }
        )
        user_id = payload.get('sub')
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.PyJWTError as e:
        print(f"JWT Error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
