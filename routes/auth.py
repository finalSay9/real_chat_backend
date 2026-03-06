from datetime import datetime, timedelta
from multiprocessing import get_context
from fastapi.params import Form
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status,APIRouter
from fastapi.security import( 
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
    SecurityScopes)
from sqlalchemy.orm import Session
from config import settings
from dependency import get_db
from models import User



SECRET_KEY = settings.SECRET_KEY
ALGOLITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

oauth_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password, hashed_password):
    return get_context.verify(plain_password, hashed_password)



def authenticate_user(
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str =Form(...)):
        user = db.query(User).filter(User.username == username & User.password==password).first()
        if not user:
             return HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
             )
        return user
            



def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encode_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGOLITHM)




def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGOLITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                 detail="invalid token",
                                 headers={"WWW-Authenticate": "Bearer"},)
        return username
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                             detail="invalid token",
                             headers={"WWW-Authenticate": "Bearer"},)
    
    

        