from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine
from app.routers import households, recipes, ingredients, planning, shopping

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Vianda API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # uso personal, sin necesidad de restringir orígenes
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(households.router)
app.include_router(recipes.router)
app.include_router(ingredients.router)
app.include_router(planning.router)
app.include_router(shopping.router)


@app.get("/health")
def health():
    return {"status": "ok"}
