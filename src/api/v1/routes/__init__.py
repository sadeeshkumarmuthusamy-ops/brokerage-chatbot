from fastapi import APIRouter

from src.api.v1.routes.chatbotapi import router as chatbot_router

v1_router = APIRouter()
v1_router.include_router(chatbot_router)
