from fastapi import FastAPI

from database import Base, engine
from routers.admin_holidays import router as admin_holidays_router
from routers.calendar import router as calendar_router
from routers.core import router as core_router
from routers.marketplace import router as marketplace_router
from routers.payments import router as payments_router
from routers.recommendations import router as recommendations_router

app = FastAPI(title="Music Platform Backend", version="1.0.0")


@app.on_event("startup")
def on_startup():
    # Keep schema creation simple for now; migrations can replace this later.
    Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {"message": "Music Platform Backend Running"}


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(core_router)
app.include_router(marketplace_router)
app.include_router(payments_router)
app.include_router(calendar_router)
app.include_router(recommendations_router)
app.include_router(admin_holidays_router)
