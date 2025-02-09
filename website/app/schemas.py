from pydantic import BaseModel


class UserBase(BaseModel):
    email: str


class UserCreate(UserBase):
    password: str


class ChatBase(BaseModel):
    name: str


class ChatCreate(ChatBase):
    pass


class Chat(ChatBase):
    id: int
    owner_id: int

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str
