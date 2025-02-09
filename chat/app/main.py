import logging
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from jose import jwt

app = FastAPI()

# Конфигурация JWT
SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[List[WebSocket]] = []

    async def connect(self, websocket: WebSocket, chat_id: int):
        await websocket.accept()
        if chat_id not in self.active_connections:
            while len(self.active_connections) < chat_id:
                self.active_connections.append([])

        self.active_connections[chat_id - 1].append(websocket)

    def disconnect(self, websocket: WebSocket, chat_id: int):
        self.active_connections[chat_id - 1].remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str, chat_id: int):
        for connection in self.active_connections[chat_id - 1]:
            await connection.send_text(message)

# Инициализация менеджера подключений
manager = ConnectionManager()

@app.websocket("/ws/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: int):
    # Проверка пользователя через JWT токен

    token = websocket.query_params.get("token")
    print(token)
    if not token:
        await websocket.close(code=1008)
        return
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email: str = payload.get("sub")

    await manager.connect(websocket, chat_id)
    await manager.broadcast(f"{email} joined the chat", chat_id)

    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"{email}: {data}", chat_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, chat_id)
        await manager.broadcast(f"{email} left the chat", chat_id)


# if __name__ == "__main__":
#     uvicorn.run(app, host="127.0.0.1", port=8000)
