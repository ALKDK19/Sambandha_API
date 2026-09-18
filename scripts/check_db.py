from dotenv import load_dotenv

load_dotenv()

from app.database import SessionLocal
from app.models.preference import Preference
from app.models.user import User
from app.models.recommender import Recommendation
from app.models.interaction import Match
from app.models.profile import Profile

db = SessionLocal()

users = db.query(User).all()
profiles = db.query(Profile).all()
preferences = db.query(Preference).all()
recommendations = db.query(Recommendation).all()
matches = db.query(Match).all()

logger_info = f"\nTotal users: {len(users)}\n"
logger_info += f"Total profiles: {len(profiles)}\n"

verified_count = 0
unverified = []

for p in profiles:
    status = f"is_verified={p.is_verified}, status={p.verification_status}"
    if p.is_verified == 1:
        verified_count += 1
    else:
        unverified.append((p.user_id, status))

logger_info += f"Verified (is_verified=1): {verified_count}\n"
logger_info += f"Unverified (is_verified=0): {len(unverified)}\n"

logger_info += f"Total preferences: {len(preferences)}\n"
logger_info += f"Total recommendations: {len(recommendations)}\n"
logger_info += f"Total matches: {len(matches)}\n"

# Build a user_id -> username map to avoid repeated DB queries
user_map = {u.user_id: u.username for u in users}


# helper to format lists as multi-line bulleted strings
def format_bulleted(items):
    if not items:
        return "  (none)\n"
    return "\n".join(f"  - {it}" for it in items) + "\n"


# list usernames of recommendations for each username
logger_info += "Recommendations:\n"
user_recommendations = {}

for rec in recommendations:
    # use the precomputed user_map instead of querying DB per item
    user_username = user_map.get(rec.user_id)
    rec_username = user_map.get(rec.recommended_user_id)
    if user_username and rec_username:
        user_recommendations.setdefault(user_username, []).append(rec_username)

for username, recs in user_recommendations.items():
    logger_info += f"User '{username}' recommendations:\n"
    logger_info += format_bulleted(recs)

# show recommendations with score is equal to or above 0.45
logger_info += "Low-score Recommendations (score =< 0.45):\n"
low_score_recs = [rec for rec in recommendations if rec.recommendation_score <= 0.45]
for rec in low_score_recs:
    score = rec.recommendation_score
    user_username = user_map.get(rec.user_id)
    rec_username = user_map.get(rec.recommended_user_id)
    if user_username and rec_username:
        logger_info += f"  - User '{user_username}' recommended User '{rec_username}' with score {score}\n"

# list matches with usernames
logger_info += "Matches:\n"
for match in matches:
    user1_username = user_map.get(match.user1_id)
    user2_username = user_map.get(match.user2_id)
    if user1_username and user2_username:
        logger_info += f"  - User '{user1_username}' and User '{user2_username} matched\n"

print(logger_info)
db.close()
