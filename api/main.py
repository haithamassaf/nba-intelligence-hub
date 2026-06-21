"""FastAPI app entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router

app = FastAPI(
    title="NFL & NBA Intelligence Hub",
    description=(
        "RAG-powered sports analytics API. Ask natural language questions "
        "grounded in real NFL and NBA stats. Routes are sport-prefixed, "
        "e.g. /nfl/ask and /nba/players."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root():
    return {
        "message": "NFL & NBA Intelligence Hub API",
        "sports": ["nfl", "nba"],
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
