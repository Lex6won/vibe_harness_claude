"""gg-webapp 표준 진입점(Track A). 레일(/health·보안헤더·base_path·파라미터바인딩) 제거 금지."""
import os
from pathlib import Path

from fastapi import FastAPI, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import Column, Integer, String, create_engine, select
from sqlalchemy.orm import Session, declarative_base, sessionmaker

APP_NAME = os.getenv("APP_NAME", "gg-webapp")
BASE_PATH = os.getenv("APP_BASE_PATH", "/apps/gg-webapp")   # 하드코딩 금지 — 환경변수 주입
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://localhost/gg_webapp")
BASE_DIR = Path(__file__).resolve().parent

# 인증(레일): 로그인·해시 직접 구현 금지. 실제 배포 시 OIDC_* 로 Keycloak(authlib) 연동.

app = FastAPI(title=APP_NAME, root_path=BASE_PATH)   # nginx가 /apps/<project>/ 프록시
templates = Jinja2Templates(directory=BASE_DIR / "templates")   # 자동 이스케이프(XSS 예방)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Item(Base):            # 예시 모델 — 개인정보 컬럼 평문 저장 금지
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.middleware("http")
async def _security_headers(request, call_next):   # 보안헤더 레일(제거·약화 금지)
    resp = await call_next(request)
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Content-Security-Policy"] = "default-src 'self'; object-src 'none'; frame-ancestors 'none'"
    resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return resp


@app.get("/health")          # 배포 게이트 필수
def health():
    return {"status": "ok", "service": APP_NAME}


@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    rows = db.execute(select(Item).order_by(Item.id.desc())).scalars().all()  # 파라미터 바인딩
    return templates.TemplateResponse("index.html", {"request": request, "app_name": APP_NAME, "items": rows})


@app.post("/items")
def create_item(title: str = Form(...), db: Session = Depends(get_db)):
    db.add(Item(title=title))    # ORM 바인딩 — 문자열 조립 금지
    db.commit()
    return RedirectResponse(url="", status_code=303)
