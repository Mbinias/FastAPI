from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, default="TODO")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI()

tasks = []
pomodoro_sessions = []

class Task(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: str = "TODO"

class CreateTask(BaseModel):
    title: str
    description: Optional[str] = None

class PomodoroSession(BaseModel):
    task_id: int
    start_time: datetime
    end_time: datetime
    completed: bool

def find_task(task_id: int):
    return next((task for task in tasks if task["id"] == task_id), None)

def has_active_pomodoro(task_id: int):
    return any(
        session for session in pomodoro_sessions
        if session["task_id"] == task_id and not session["completed"]
    )

app.post("/tasks", response_model=Task)
def create_task(task: CreateTask):
    if any(t["title"] == task.title for t in tasks):
        raise HTTPException(status_code=400, detail="Task title must be unique.")

    new_task = {
        "id": len(tasks) + 1,
        "title": task.title,
        "description": task.description,
        "status": "TODO"
    }
    tasks.append(new_task)
    return new_task

@app.get("/tasks", response_model=List[Task])
def get_tasks():
    return tasks

# Get task details by ID
@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: int):
    task = find_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task

@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, task: CreateTask):
    existing_task = find_task(task_id)
    if not existing_task:
        raise HTTPException(status_code=404, detail="Task not found.")

    if task.title != existing_task["title"] and any(t["title"] == task.title for t in tasks):
        raise HTTPException(status_code=400, detail="Task title must be unique.")

    existing_task.update({
        "title": task.title,
        "description": task.description
    })
    return existing_task

@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    task = find_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    tasks.remove(task)
    return

@app.post("/pomodoro", response_model=PomodoroSession)
def create_pomodoro(task_id: int):
    task = find_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    if has_active_pomodoro(task_id):
        raise HTTPException(status_code=400, detail="An active Pomodoro already exists for this task.")

    session = {
        "task_id": task_id,
        "start_time": datetime.now(),
        "end_time": datetime.now() + timedelta(minutes = 2),
        "completed": False
    }
    pomodoro_sessions.append(session)
    return session

@app.post("/pomodoro/{task_id}/stop")
def stop_pomodoro(task_id: int):
    for session in pomodoro_sessions:
        if session["task_id"] == task_id and not session["completed"]:
            session["completed"] = True
            session["end_time"] = datetime.now()
            return session

    raise HTTPException(status_code=404, detail="No active Pomodoro found for this task.")

@app.get("/pomodoro", response_model=List[PomodoroSession])
def get_pomodoros():
    return pomodoro_sessions