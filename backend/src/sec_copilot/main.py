from collections.abc import Generator

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from sec_copilot.answering import AskRequest, AskResponse, CitedAnswerService
from sec_copilot.comparison import CompareRequest, CompareResponse, FilingComparisonService
from sec_copilot.config import get_settings
from sec_copilot.db.session import SessionLocal

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API foundation for cited SEC filing research workflows.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "sec-filing-intelligence-copilot",
        "environment": settings.app_env,
    }


def get_db_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session


@app.post("/ask", response_model=AskResponse, tags=["qa"])
def ask(request: AskRequest, session: Session = Depends(get_db_session)) -> AskResponse:
    try:
        return CitedAnswerService(session=session).answer(request)
    except ValueError as exc:
        detail = str(exc)
        if detail.startswith("Filing not found"):
            raise HTTPException(status_code=404, detail=detail) from exc
        raise HTTPException(status_code=422, detail=detail) from exc


@app.post("/compare", response_model=CompareResponse, tags=["qa"])
def compare(request: CompareRequest, session: Session = Depends(get_db_session)) -> CompareResponse:
    try:
        return FilingComparisonService(session=session).compare(request)
    except ValueError as exc:
        detail = str(exc)
        if detail.startswith("Filing not found"):
            raise HTTPException(status_code=404, detail=detail) from exc
        raise HTTPException(status_code=422, detail=detail) from exc
