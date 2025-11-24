# app/api/auth.py
import random
import string
from datetime import timedelta, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from starlette import status

from app.database import get_db
from app.models.user import User, PasswordResetOtp
from app.schemas.base import MessageResponse
from app.schemas.user import UserInDB, Token, RegisterWithFirebase, ForgotPasswordRequest, ResetPasswordWithOtpRequest
from utilities.email import send_email
from utilities.firebase import verify_firebase_id_token
from utilities.notification import send_profile_completion_notification
from utilities.security import get_password_hash, get_otp_hash, verify_otp, create_access_token, verify_password

router = APIRouter()


@router.post("/register-with-firebase", response_model=UserInDB)
def register_with_firebase(
        user_data: RegisterWithFirebase,
        db: Session = Depends(get_db)
):
    print("=================================")
    print(user_data)
    print("=================================")
    decoded_token = verify_firebase_id_token(user_data.token_id)
    phone_number = decoded_token.get("phone_number")
    if not phone_number:
        raise HTTPException(status_code=400, detail="Firebase token is valid but does not contain a phone number.")
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if user_data.email and db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(User).filter(User.phone_number == phone_number).first():
        raise HTTPException(status_code=400, detail="Phone number already registered")
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        phone_number=phone_number,
        password_hash=hashed_password,
        auth_provider="firebase_phone",
        is_active=True,
        is_phone_verified=True,
        is_email_verified=False
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    notif_msg = "Welcome to Sambandha! Please complete your profile to find your perfect match."
    send_profile_completion_notification(db, db_user.user_id, 0, [notif_msg])
    return db_user


@router.post("/token", response_model=Token)
def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        (User.email == form_data.username) |
        (User.phone_number == form_data.username) |
        (User.username == form_data.username)
    ).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/phone or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Reactivate user on login
    if not user.is_active:
        if not user.deactivated_by == "admin":
            user.is_active = True
            user.deactivated_by = None
            db.commit()
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account deactivated by admin. Contact support."
            )

    access_token = create_access_token(data={"user_id": user.user_id})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/forgot-password-otp", response_model=MessageResponse)
def request_password_reset_otp(
        request: ForgotPasswordRequest,
        db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == request.email, User.is_active == True).first()

    if user:
        # Invalidate any old OTPs for this user
        db.query(PasswordResetOtp).filter(PasswordResetOtp.user_id == user.user_id).delete()

        # Generate a simple 6-digit OTP
        otp = ''.join(random.choices(string.digits, k=6))

        # Hash the OTP for storage
        otp_hash = get_otp_hash(otp)
        expires_at = datetime.utcnow() + timedelta(minutes=10)  # OTP is valid for 10 minutes

        otp_entry = PasswordResetOtp(
            user_id=user.user_id,
            otp_hash=otp_hash,
            expires_at=expires_at
        )
        db.add(otp_entry)
        db.commit()

        # Send the plain text OTP via email
        email_body = f"<p>Your password reset code is: <strong>{otp}</strong></p><p>This code is valid for 10 minutes.</p>"
        try:
            send_email(user.email, "Your Sambandha Password Reset Code", email_body)
        except Exception as e:
            print(f"ERROR: Failed to send password reset OTP to {user.email}: {e}")
            pass

    return MessageResponse(message="If an account with that email exists, a password reset code has been sent.")


@router.post("/reset-password-otp", response_model=MessageResponse)
def perform_password_reset_with_otp(
        request: ResetPasswordWithOtpRequest,
        db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP or email.")

    otp_entry = db.query(PasswordResetOtp).filter(
        PasswordResetOtp.user_id == user.user_id,
        PasswordResetOtp.is_used == False,
        PasswordResetOtp.expires_at > datetime.utcnow()
    ).first()  # Get the most recent valid OTP

    if not otp_entry or not verify_otp(request.otp, otp_entry.otp_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP.")

    # Update the user's password
    user.password_hash = get_password_hash(request.new_password)

    # Mark the token as used
    otp_entry.is_used = True

    db.commit()

    return MessageResponse(message="Password has been reset successfully. You can now log in.")
