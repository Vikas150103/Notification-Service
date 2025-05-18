### main.py (FastAPI Entry Point)
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app import models, schemas, database, tasks
from app.database import engine, get_db
from app.models import Notification
from app.tasks import send_notification_task

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.post("/notifications")
def send_notification(notification: schemas.NotificationCreate, db: Session = Depends(get_db)):
    db_notification = models.Notification(
        user_id=notification.user_id,
        type=notification.type,
        message=notification.message,
        status="queued"
    )
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)

    send_notification_task.delay(db_notification.id)
    return {"status": "queued", "notification_id": db_notification.id}


@app.get("/users/{user_id}/notifications", response_model=list[schemas.NotificationOut])
def get_notifications(user_id: int, db: Session = Depends(get_db)):
    return db.query(Notification).filter(Notification.user_id == user_id).all()


### database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./notifications.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


### models.py
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.database import Base

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    type = Column(String)
    message = Column(String)
    status = Column(String, default="queued")
    timestamp = Column(DateTime, default=datetime.utcnow)


### schemas.py
from pydantic import BaseModel
from datetime import datetime

class NotificationCreate(BaseModel):
    user_id: int
    type: str
    message: str

class NotificationOut(NotificationCreate):
    id: int
    status: str
    timestamp: datetime

    class Config:
        orm_mode = True


### tasks.py (Celery Tasks)
from celery import Celery
from app.models import Notification
from app.database import SessionLocal
import time

celery = Celery(__name__, broker="pyamqp://guest@rabbitmq//")

def dispatch_notification(notification):
    print(f"Sending {notification.type} notification: {notification.message}")
    time.sleep(2)  # simulate delay

@celery.task(bind=True, max_retries=3)
def send_notification_task(self, notification_id):
    db = SessionLocal()
    try:
        notification = db.query(Notification).filter(Notification.id == notification_id).first()
        if not notification:
            return

        dispatch_notification(notification)
        notification.status = "sent"
        db.commit()
    except Exception as e:
        self.retry(exc=e, countdown=2 ** self.request.retries)
    finally:
        db.close()


### celery_worker.py
from app.tasks import celery

if __name__ == "__main__":
    celery.start()


### requirements.txt
fastapi
uvicorn
sqlalchemy
pydantic
celery


### docker-compose.yml (FastAPI + Celery + RabbitMQ)
version: '3.8'

services:
  rabbitmq:
    image: rabbitmq:3-management
    container_name: rabbitmq
    ports:
      - "5672:5672"
      - "15672:15672"

  backend:
    build:
      context: .
    container_name: fastapi_app
    ports:
      - "8000:8000"
    depends_on:
      - rabbitmq
    volumes:
      - .:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

  celery_worker:    
    build:
      context: .
    container_name: celery_worker
    command: celery -A app.tasks worker --loglevel=info
    depends_on:
      - rabbitmq
    volumes:
      - .:/app


### Dockerfile (FastAPI Backend + Celery)
FROM python:3.10-slim

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


### __init__.py
# (Place this empty file inside the app/ folder)
# app/__init__.py


