# Create a new file: app/api/security.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.security import Report
from app.models.user import User
from app.schemas.security import ReportCreate, ReportInDB
from utilities.security import get_current_user

router = APIRouter()


@router.post("/reports", response_model=ReportInDB)
def create_report(
        report_data: ReportCreate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    # Prevent self-reporting for user-to-user reports
    if report_data.reported_user_id is not None and report_data.reported_user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="You cannot report yourself.")

    # If it's a user-to-user report, check if the reported user exists
    if report_data.reported_user_id is not None:
        reported_user = db.query(User).filter(User.user_id == report_data.reported_user_id).first()
        if not reported_user:
            raise HTTPException(status_code=404, detail="User to be reported not found.")

    new_report = Report(
        reporter_user_id=current_user.user_id,
        reported_user_id=report_data.reported_user_id,
        report_category=report_data.report_category,
        report_details=report_data.report_details,
        report_reason_text=report_data.report_reason_text
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)
    return new_report
