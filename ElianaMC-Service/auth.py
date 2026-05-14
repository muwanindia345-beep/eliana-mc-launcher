from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uvicorn, json, os, hashlib, time, secrets

app = FastAPI(title="ElianaMC Auth", version="1.0")

app.add_middleware(CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"],
    allow_headers=["*"], allow_credentials=True
)

# ── Storage ───────────────────────────────────────
USERS_FILE  = "users.json"
TOKENS_FILE = "tokens.json"

def load(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

def save(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

# ── Models ────────────────────────────────────────
class RegisterModel(BaseModel):
    username: str
    email: str
    password: str

class LoginModel(BaseModel):
    email: str
    password: str

# ── Helpers ───────────────────────────────────────
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token() -> str:
    return secrets.token_hex(32)

def verify_token(token: str) -> dict:
    tokens = load(TOKENS_FILE)
    if token not in tokens:
        return None
    data = tokens[token]
    # Check expiry (7 days)
    if time.time() > data.get("expires", 0):
        del tokens[token]
        save(TOKENS_FILE, tokens)
        return None
    return data

security = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user

# ── Routes ────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/register")
async def register(data: RegisterModel):
    users = load(USERS_FILE)

    # Validate
    if len(data.username) < 3:
        raise HTTPException(status_code=400, detail="Username too short (min 3)")
    if "@" not in data.email:
        raise HTTPException(status_code=400, detail="Invalid email")
    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="Password too short (min 8)")

    # Check existing
    for u in users.values():
        if u["email"] == data.email:
            raise HTTPException(status_code=400, detail="Email already registered")
        if u["username"].lower() == data.username.lower():
            raise HTTPException(status_code=400, detail="Username already taken")

    # Create user
    user_id = secrets.token_hex(8)
    user    = {
        "id":         user_id,
        "username":   data.username,
        "email":      data.email,
        "password":   hash_password(data.password),
        "created_at": time.time(),
        "role":       "admin" if not users else "user"
    }
    users[user_id] = user
    save(USERS_FILE, users)

    # Generate token
    token  = generate_token()
    tokens = load(TOKENS_FILE)
    tokens[token] = {
        "user_id":  user_id,
        "email":    data.email,
        "username": data.username,
        "role":     user["role"],
        "expires":  time.time() + 604800  # 7 days
    }
    save(TOKENS_FILE, tokens)

    return {
        "token": token,
        "user": {
            "id":       user_id,
            "username": data.username,
            "email":    data.email,
            "role":     user["role"]
        }
    }

@app.post("/login")
async def login(data: LoginModel):
    users = load(USERS_FILE)

    # Find user
    found = None
    for u in users.values():
        if u["email"] == data.email:
            found = u
            break

    if not found:
        raise HTTPException(status_code=401, detail="No account found with this email")

    if found["password"] != hash_password(data.password):
        raise HTTPException(status_code=401, detail="Wrong password")

    # Generate token
    token  = generate_token()
    tokens = load(TOKENS_FILE)
    tokens[token] = {
        "user_id":  found["id"],
        "email":    found["email"],
        "username": found["username"],
        "role":     found.get("role", "user"),
        "expires":  time.time() + 604800
    }
    save(TOKENS_FILE, tokens)

    return {
        "token": token,
        "user": {
            "id":       found["id"],
            "username": found["username"],
            "email":    found["email"],
            "role":     found.get("role", "user")
        }
    }

@app.post("/logout")
async def logout(user = Depends(get_current_user)):
    return {"message": "Logged out"}

@app.get("/me")
async def me(user = Depends(get_current_user)):
    return user

@app.get("/users")
async def list_users(user = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    users = load(USERS_FILE)
    return {"users": [
        {"id": u["id"], "username": u["username"], "email": u["email"], "role": u.get("role","user")}
        for u in users.values()
    ]}

if __name__ == "__main__":
    uvicorn.run("auth:app", host="0.0.0.0", port=8008, reload=False)
