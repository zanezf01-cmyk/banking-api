import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from jose import JWTError, jwt
import bcrypt

load_dotenv()

# --- Config ---
SECRET_KEY = os.environ["8948390d3553c5b71cf796569ad3bd9315ff815976c65fb5a3b9f6203e75b4f4"]
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# --- Fake user "database" ---
fake_users_db = {
    "zane": {
        "username": "zane",
        # password: "password123"
        "hashed_password": "$2b$12$eT/dlD2at8jGIebewq91m.FiDh9rx6heF72x7D0d4kc7mmpQ3k9ty",
    }
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)