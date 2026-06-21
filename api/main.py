"""FastAPI app entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router

app = FastAPI(
    title="NFL & NBA Roster Grader",
    description=(
        "Roster grading API. Per-position grades from advanced stats, plus "
        "team needs and summaries. Routes are sport-prefixed, e.g. "
        "/nfl/teams and /nba/teams/{team}/grades."
    ),
    version="3.0.0",
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
        "message": "NFL & NBA Roster Grader API",
        "sports": ["nfl", "nba"],
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
