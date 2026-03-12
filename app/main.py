from fastapi import FastAPI
from app.api import routes_chat, routes_health, routes_models, routes_completions, routes_embeddings, routes_responses
from app.core.config import settings
from app.core.logging import setup_logging

# Initialize logging
setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Root level health routes
app.include_router(routes_health.router)

# V1 API routes
app.include_router(routes_chat.router, prefix=settings.API_V1_STR)
app.include_router(routes_models.router, prefix=settings.API_V1_STR)
app.include_router(routes_completions.router, prefix=settings.API_V1_STR)
app.include_router(routes_embeddings.router, prefix=settings.API_V1_STR)
app.include_router(routes_responses.router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": "LLM Message Normalization Adapter for llama.cpp is running"}
