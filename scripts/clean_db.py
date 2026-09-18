"""Clean up test data from database - COMPLETE VERSION"""

from dotenv import load_dotenv

load_dotenv()

from app.database import SessionLocal
from app.models.recommender import Recommendation
from app.models.interaction import Match, Like, Chat, Message, ProfileVisit
from app.models.engagement import Notification
from app.models.profile import Profile
from app.models.preference import Preference
from app.models.security import BlockedUser, Report
from app.models.shortlist import Shortlist
from app.models.user import User

db = SessionLocal()

logger_info = "\n" + "=" * 60 + "\n"
logger_info += "CLEANING DATABASE\n"
logger_info += "=" * 60 + "\n"

# Count before
users_before = db.query(User).count()
profiles_before = db.query(Profile).count()
prefs_before = db.query(Preference).count()

logger_info += f"BEFORE: {users_before} users, {profiles_before} profiles\n\n"

# Delete in CORRECT order (reverse dependency order)
logger_info += "Deleting all data in dependency order...\n"

try:
    # 1. Delete messages first (depends on chat)
    db.query(Message).delete(synchronize_session=False)
    logger_info += "  ✓ Deleted messages\n"

    # 2. Delete chats (depends on match)
    db.query(Chat).delete(synchronize_session=False)
    logger_info += "  ✓ Deleted chats\n"

    # 3. Delete notifications (depends on user)
    db.query(Notification).delete(synchronize_session=False)
    logger_info += "  ✓ Deleted notifications\n"

    # 4. Delete recommendations (depends on user)
    db.query(Recommendation).delete(synchronize_session=False)
    logger_info += "  ✓ Deleted recommendations\n"

    # 5. Delete matches (depends on user)
    db.query(Match).delete(synchronize_session=False)
    logger_info += "  ✓ Deleted matches\n"

    # 6. Delete likes (depends on user)
    db.query(Like).delete(synchronize_session=False)
    logger_info += "  ✓ Deleted likes\n"

    # 7. Delete profile visits (depends on user)
    db.query(ProfileVisit).delete(synchronize_session=False)
    logger_info += "  ✓ Deleted profile visits\n"

    # 8. Delete shortlists (depends on user)
    db.query(Shortlist).delete(synchronize_session=False)
    logger_info += "  ✓ Deleted shortlists\n"

    # 9. Delete reports (depends on user)
    db.query(Report).delete(synchronize_session=False)
    logger_info += "  ✓ Deleted reports\n"

    # 10. Delete blocked users (depends on user)
    db.query(BlockedUser).delete(synchronize_session=False)
    logger_info += "  ✓ Deleted blocked users\n"

    # 11. Delete preferences (depends on user)
    db.query(Preference).delete(synchronize_session=False)
    logger_info += "  ✓ Deleted preferences\n"

    # 12. Delete profiles (depends on user)
    db.query(Profile).delete(synchronize_session=False)
    logger_info += "  ✓ Deleted profiles\n"

    # 13. Delete users last
    db.query(User).delete(synchronize_session=False)
    logger_info += "  ✓ Deleted users\n"

    db.commit()
    logger_info += "\n✓ Committed all deletions\n"

    # Count after
    users_after = db.query(User).count()
    profiles_after = db.query(Profile).count()
    prefs_after = db.query(Preference).count()

    logger_info += f"\nAFTER: {users_after} users, {profiles_after} profiles\n"
    logger_info += "=" * 60

except Exception as e:
    logger_info += f"\n❌ ERROR during deletion: {str(e)}\n"
    logger_info += "Attempting rollback...\n"
    db.rollback()
    logger_info += "✓ Rolled back\n"
    logger_info += "=" * 60

print(logger_info)
db.close()
