import json
import os
import random
import uuid
from datetime import datetime, date, timezone
from types import SimpleNamespace

from dotenv import load_dotenv

from app.api.profiles import calculate_profile_completion
from app.database import SessionLocal
from app.models.admin import Admin
from app.models.interaction import Like
from app.models.preference import Preference
from app.models.profile import Profile
from app.models.user import User
from scripts.seeders.data.likes import hybrid_recommendation_likes, mutual_like_pairs
from utilities.cloudinary import upload_image_to_cloudinary, configure_cloudinary
from utilities.logging_config import logger
from utilities.notification import send_profile_verification_status_notification
from utilities.recsys.embedding_utils import update_profile_embedding
from utilities.security import get_password_hash

load_dotenv()


def normalize_looking_for(raw: str | None) -> str | None:
    """Normalize a comma-separated looking_for string into canonical capitalized tokens."""
    if not raw:
        return None
    parts = [p.strip() for p in raw.split(',') if p.strip()]
    canon = []
    for p in parts:
        low = p.lower()
        if low == 'male':
            canon.append('Male')
        elif low == 'female':
            canon.append('Female')
        elif low == 'other':
            canon.append('Other')
        elif low == 'any':
            canon.append('Any')
        elif low == 'bride':
            canon.append('Bride')
        elif low == 'bridegroom' or low == 'groom':
            canon.append('Bridegroom')
        else:
            canon.append(p.strip().title())
    seen = set()
    out = []
    for c in canon:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return ','.join(out)


def create_like_if_not_exists(db: SessionLocal, liker_user_id: int, liked_user_id: int) -> bool:
    """Create a like if it doesn't already exist. Returns True if created, False if already exists."""
    existing_like = db.query(Like).filter(
        Like.liker_user_id == liker_user_id,
        Like.liked_user_id == liked_user_id
    ).first()

    if not existing_like:
        new_like = Like(
            liker_user_id=liker_user_id,
            liked_user_id=liked_user_id,
            like_type='like',
            status='active'
        )
        db.add(new_like)
        return True
    return False


def seed():
    """
    Seeds users, profiles, and preferences from a single JSON file.
    This version uses short-lived sessions and a keep-alive query to prevent DB timeouts.
    """
    logger.info("Starting comprehensive seeding from JSON file...")
    configure_cloudinary()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, 'data', 'complete_users.json')

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            user_data_list = json.load(f)
    except FileNotFoundError:
        logger.error(f"CRITICAL: Data file not found at {json_path}. Aborting seed.")
        return
    except json.JSONDecodeError:
        logger.error(f"CRITICAL: Could not parse JSON from {json_path}. Check for syntax errors. Aborting seed.")
        return

    default_password = "User@#23201"
    hashed_password = get_password_hash(default_password)

    # === STAGE 1 & 2: UPSERT USERS, PROFILES, PREFERENCES, AND EMBEDDINGS ===
    db = SessionLocal()
    try:
        logger.info("--- Stage 1: Processing User, Profile, and Preference data ---")
        profiles_to_embed = []
        for user_data in user_data_list:
            user_details = user_data['user']
            profile_details = user_data['profile']
            preference_details = user_data['preferences']

            user = db.query(User).filter(User.username == user_details['username']).first()
            if not user:
                user = User(
                    username=user_details['username'],
                    email=f"{user_details['username']}@gmail.com",
                    phone_number=f"+97798{random.randint(10000000, 99999999)}",
                    password_hash=hashed_password, is_active=True, is_phone_verified=True
                )
                db.add(user)
                logger.info(f"Created new user: {user.username}")
            else:
                logger.info(f"Found existing user: {user.username}")

            db.flush()

            profile = db.query(Profile).filter(Profile.user_id == user.user_id).first()
            if not profile:
                profile = Profile(user_id=user.user_id)
                db.add(profile)

            for key, value in profile_details.items():
                if key == 'date_of_birth' and value:
                    setattr(profile, key, date.fromisoformat(value))
                else:
                    setattr(profile, key, value)

            percent, _, _ = calculate_profile_completion(profile)
            profile.profile_completion_percentage = percent
            profiles_to_embed.append(profile)

            preference = db.query(Preference).filter(Preference.user_id == user.user_id).first()
            if not preference:
                preference = Preference(user_id=user.user_id)
                db.add(preference)

            for key, value in preference_details.items():
                if key == 'looking_for':
                    value = normalize_looking_for(value)
                setattr(preference, key, value)

        logger.info("Committing all user, profile, and preference data...")
        db.commit()

        logger.info("--- Stage 2: Generating embeddings for all profiles ---")
        for profile in profiles_to_embed:
            profile_in_session = db.get(Profile, profile.profile_id)
            if profile_in_session:
                update_profile_embedding(db, profile_in_session)
        logger.info("Embeddings generated successfully.")
    finally:
        db.close()

    # === STAGE 3: CREATE STRATEGIC LIKES ===
    db = SessionLocal()
    try:
        logger.info("--- Stage 3: Creating strategic likes for hybrid recommendations and mutual matches ---")
        user_lookup = {u.username: u for u in db.query(User).all()}

        logger.info("Creating hybrid recommendation likes for Users 11-22...")
        hybrid_likes_created = 0
        for liker_username, liked_usernames in hybrid_recommendation_likes.items():
            liker_user = user_lookup.get(liker_username)
            if not liker_user: continue
            for liked_username in liked_usernames:
                liked_user = user_lookup.get(liked_username)
                if not liked_user: continue
                if create_like_if_not_exists(db, liker_user.user_id, liked_user.user_id):
                    hybrid_likes_created += 1

        logger.info("Creating mutual likes for Users 32-40...")
        mutual_likes_created = 0
        for user1_username, user2_username in mutual_like_pairs:
            user1 = user_lookup.get(user1_username)
            user2 = user_lookup.get(user2_username)
            if not user1 or not user2: continue
            if create_like_if_not_exists(db, user1.user_id, user2.user_id): mutual_likes_created += 1
            if create_like_if_not_exists(db, user2.user_id, user1.user_id): mutual_likes_created += 1

        logger.info("Committing all strategic likes...")
        db.commit()
        logger.info(
            f"✅ Strategic likes creation completed: Total likes created: {hybrid_likes_created + mutual_likes_created}")
    finally:
        db.close()

    # === STAGE 4: PROFILE VERIFICATION WORKFLOW ===
    db = SessionLocal()
    try:
        logger.info("--- Stage 4: Profile Verification Workflow ---")
        admin = db.query(Admin).first()
        if not admin:
            admin = Admin(username="admin_sambandha", email="admin@sambandha.local",
                          password_hash=get_password_hash("Admin@#23201"), is_superuser=True, is_active=True)
            db.add(admin)
            db.commit()
        admin_id = admin.admin_id

        all_user_profiles = db.query(Profile).all()
        id_card_path = os.path.join(base_dir, 'data', 'id-card.jpg')
        if os.path.exists(id_card_path):
            for profile in all_user_profiles:
                if not profile.government_id_url:
                    public_id = f"user_{profile.user_id}_govtid_{uuid.uuid4().hex}"
                    with open(id_card_path, 'rb') as f:
                        mock_upload_file = SimpleNamespace(file=f)
                        image_url = upload_image_to_cloudinary(file=mock_upload_file,
                                                               folder="sambandha/government_ids",
                                                               public_id=public_id)
                    profile.government_id_url = image_url
                    profile.verification_status = "requested"
        db.commit()

        for profile in all_user_profiles:
            profile.is_verified = 1
            profile.verified_at = datetime.now(timezone.utc)
            profile.verified_by_admin_id = admin_id
            profile.verification_status = "verified"
            profile.is_approved = 1
            profile.is_hidden = 0
            send_profile_verification_status_notification(db, profile.user_id, "verified",
                                                          "Your profile has been verified successfully.")
        db.commit()
        logger.info("✓ Verification workflow complete.")
    finally:
        db.close()

    logger.info("\n" + "=" * 80)
    logger.info("✓ USER DATA SEEDING COMPLETE - ALL STAGES SUCCESSFUL!")
    logger.info("=" * 80)
    logger.info("User profiles, preferences, likes, and verifications seeded successfully!")
    logger.info("\nTo generate matches and recommendations, run:")
    logger.info("  python -m scripts.seeders.utils.seed run 003_run_matchmaking_and_recommendations")
    logger.info("=" * 80)


# This file defines seed() and has a __main__ guard so you can also run:
#   python -m scripts.seeders.002_seed_complete_users
# or run via the runner:
#   python -m scripts.seed run 002_seed_complete_users

if __name__ == "__main__":
    try:
        seed()
    except Exception as e:
        logger.critical(f"A critical error occurred during the seeding process: {e}", exc_info=True)
