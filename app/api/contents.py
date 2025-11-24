from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.content import StaticContent, Announcement
from app.schemas.content import StaticContentInDB, AnnouncementInDB

router = APIRouter()


@router.get("/static-content/{key}", response_model=StaticContentInDB)
def get_static_content(key: str, db: Session = Depends(get_db)):
    content = db.query(StaticContent).filter(StaticContent.key == key).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return content


@router.get("/static-content", response_model=List[StaticContentInDB])
def list_static_content(db: Session = Depends(get_db)):
    return db.query(StaticContent).all()


@router.get("/announcements", response_model=List[AnnouncementInDB])
def list_announcements(db: Session = Depends(get_db)):
    return db.query(Announcement).order_by(Announcement.created_at.desc()).all()


@router.get("/announcements/{announcement_id}", response_model=AnnouncementInDB)
def get_announcement(announcement_id: int, db: Session = Depends(get_db)):
    ann = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return ann
