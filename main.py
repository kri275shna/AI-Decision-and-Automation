from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.db.database import engine, Base
from app.api.routes import router
from app.queue.in_memory_queue import task_queue
from app.engine.workflow_engine import workflow_engine

Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    task_queue.set_processor(workflow_engine.process_task)
    task_queue.start()
    yield
    task_queue.stop()

app = FastAPI(title="AI Decision & Automation Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "AI Decision & Automation Platform", "version": "1.0.0"}
