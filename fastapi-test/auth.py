import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from starlette import status

from parse_config import conf
from werkzeug.security import check_password_hash

SECRET_KEY = conf['app_config']['secret_key']
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

admin_user = conf['user']
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


def authenticate_user(username: str, password: str):
    if username != admin_user['name']:
        return False
    if not check_password_hash(admin_user['password'], password):
        return False
    return {"username": username}


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    if "sub" not in to_encode:
        raise ValueError("Missing 'sub' claim in token data")
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None or username != admin_user['name']:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
    return {"username": username}
