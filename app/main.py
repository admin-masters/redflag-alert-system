from fastapi import FastAPI
from routers import health

app = FastAPI(title="Inditech RFA")

app.include_router(health.router, prefix="/healthz")
# other routers will be included as we flesh them out