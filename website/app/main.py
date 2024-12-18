from fastapi import FastAPI, Depends, HTTPException, APIRouter, status, Query, Header, Request, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .init import User, Chat
from fastapi.responses import RedirectResponse
from typing import Optional
from . import crud, schemas
from fastapi.templating import Jinja2Templates
import bcrypt
from jose import jwt
from datetime import datetime, timedelta
import uvicorn
from .utils import verify_password, get_db, get_current_user


app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

# Конфигурация JWT
SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# Регистрация
@app.post("/register/")
def register(user: schemas.UserCreate,
    db: Session = Depends(get_db)):
    # Проверка, зарегистрирован ли уже пользователь с данным email
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Хэширование пароля пользователя
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), salt)

    # Создание пользователя с хэшированным паролем
    user_data = schemas.UserCreate(email=user.email, password=hashed_password.decode('utf-8'))
    return crud.create_user(db=db, user=user_data)


# Аутентификация
@app.post("/login/", response_model=schemas.Token)
def login(user: schemas.UserCreate,
          db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()

    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate JWT token for authentication
    access_token = create_access_token(data={"sub": user.email})
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="access_token", value=access_token, httponly=False)

    return response


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Получение списка своих комнат
@app.get("/my-chats/")
async def get_user_rooms(
    request: Request,
    db: Session = Depends(get_db),
):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/")
    user = get_current_user(token, db)
    if user:
        rooms = db.query(Chat).filter(Chat.owner_id == user.id).all()
        return templates.TemplateResponse("my-rooms.html", {"request": request, "rooms": rooms})
    if not user:
        return RedirectResponse(url="/")


@app.post("/my-chats/add/")
async def add_chat(
        request: Request,
        chat: schemas.ChatCreate,
        db: Session = Depends(get_db),
):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/")
    user = get_current_user(token, db)
    crud.create_chat(db=db, chat=chat, user_id=user.id)
    return RedirectResponse(url="/my-chats", status_code=303)

@app.post("/my-chats/delete/{chat_id}/")
async def delete_chat(request: Request, chat_id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/")
    user = get_current_user(token, db)
    crud.delete_chat(db=db, chat_id=chat_id)
    return RedirectResponse(url="/my-chats", status_code=303)


@app.get("/rooms/")
async def get_rooms(
        request: Request,
        db: Session = Depends(get_db),
        search: Optional[str] = Query(None)
):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/")

    if search:
        rooms = db.query(Chat).filter(Chat.name.ilike(f"%{search}%")).all()
    else:
        rooms = db.query(Chat).all()

    return templates.TemplateResponse("rooms.html", {"request": request, "rooms": rooms})


@app.get("/")
async def get_root_page(
    request: Request,
    db: Session = Depends(get_db)
):
    token = request.cookies.get("access_token")

    if token and get_current_user(token, db):
        return RedirectResponse(url="/home")
    else:
        return templates.TemplateResponse("index.html", {"request": request})


@app.get("/home/")
async def get_home_page(
    request: Request,
    db: Session = Depends(get_db)
):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/")
    user = get_current_user(token, db)
    if user:
        return templates.TemplateResponse("home.html", {"request": request, "username": user.email})
    else:
        return RedirectResponse(url="/")


@app.get("/ws/{chat_id}/")
async def get_ws(request: Request, chat_id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/")
    user = get_current_user(token, db)
    if not user:
        return RedirectResponse(url="/")
    return templates.TemplateResponse("chat.html", {"request": request, "chat_id": chat_id})


# if __name__ == "__main__":
#     uvicorn.run(app, host="127.0.0.1", port=8001)
