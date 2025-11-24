from sqlalchemy.orm import joinedload

from app.models.engagement import Notification
from app.models.interaction import Chat
from app.models.interaction import Like, Match
from app.models.profile import Profile
from app.models.recommender import Recommendation
from app.models.user import User
from utilities.recsys.compatibility import CompatibilityScorer
from utilities.firebase_notifications import send_notification_to_user
from utilities.recsys.recommender import Recommender


class MatchMaker:
    """
    MatchMaker coordinates recommendations and compatibility scoring to create matches.

    Rules implemented:
      - Compute compatibility score (0-100) using CompatibilityScorer.calculate_mutual_score
      - If score >= 80 => create/upsert an active match (match_type='score_only')
      - If 50 <= score < 80 => require a mutual active like between users to create match
      - Otherwise no match is created

    The class uses an upsert-style helper to ensure a single Match row per unordered pair
    and enforces that both users have verified profiles before creating or keeping active matches.
    """

    def __init__(self, db_session):
        self.db = db_session
        self.recommender = Recommender(self.db)
        self.scorer = CompatibilityScorer()

    def _get_user(self, user_id):
        return self.db.query(User).options(joinedload(User.profile), joinedload(User.preferences)).filter(
            User.user_id == user_id,
            User.is_active == True,
            User.is_blocked == False
        ).first()

    def _is_verified(self, user: User) -> bool:
        return bool(user and getattr(user, 'profile', None) and
                    getattr(user.profile, 'verification_status', '') == 'verified' and
                    getattr(user.profile, 'is_verified', 0) == 1)

    def _has_mutual_like(self, user_a_id: int, user_b_id: int) -> bool:
        """Return True if both users have an active like for the other."""
        a_likes_b = self.db.query(Like).filter(
            Like.liker_user_id == user_a_id,
            Like.liked_user_id == user_b_id,
            Like.status == 'active'
        ).first() is not None
        b_likes_a = self.db.query(Like).filter(
            Like.liker_user_id == user_b_id,
            Like.liked_user_id == user_a_id,
            Like.status == 'active'
        ).first() is not None
        return a_likes_b and b_likes_a

    def _upsert_match(self, user_a: int, user_b: int, score: float | None = None, status: str = 'active',
                      match_type: str = 'score_only'):
        """Create or update a Match between two user ids. Keeps a single record per unordered pair.

        If either user is unverified, does not create a new active match and will deactivate existing active matches.
        """
        if user_a <= user_b:
            u1, u2 = user_a, user_b
        else:
            u1, u2 = user_b, user_a

        try:
            p1 = self.db.query(Profile).filter(Profile.user_id == u1).first()
            p2 = self.db.query(Profile).filter(Profile.user_id == u2).first()
        except Exception:
            p1 = p2 = None

        both_verified = False
        if p1 and p2:
            both_verified = (
                    getattr(p1, 'is_verified', 0) == 1 and getattr(p1, 'verification_status', '') == 'verified' and
                    getattr(p2, 'is_verified', 0) == 1 and getattr(p2, 'verification_status', '') == 'verified')

        existing = self.db.query(Match).filter(
            Match.user1_id == u1,
            Match.user2_id == u2
        ).first()

        if existing:
            # deactivate existing if users no longer verified
            if not both_verified and existing.match_status == 'active':
                existing.match_status = 'unmatched'
                self.db.commit()
                return existing

            updated = False
            previous_status = existing.match_status
            if existing.match_status != status:
                existing.match_status = status
                updated = True
            if score is not None and existing.compatibility_score != score:
                existing.compatibility_score = score
                updated = True
            if match_type and existing.match_type != match_type:
                existing.match_type = match_type
                updated = True
            if updated:
                self.db.commit()
                # If the match just became active, create chat and notify both users
                try:
                    if previous_status != 'active' and existing.match_status == 'active':
                        # ensure chat exists
                        existing_chat = self.db.query(Chat).filter(
                            ((Chat.initiator_user_id == u1) & (Chat.receiver_user_id == u2)) |
                            ((Chat.initiator_user_id == u2) & (Chat.receiver_user_id == u1))
                        ).first()
                        if not existing_chat:
                            new_chat = Chat()
                            new_chat.match_id = existing.match_id
                            new_chat.initiator_user_id = u1
                            new_chat.receiver_user_id = u2
                            new_chat.state = 'active'
                            self.db.add(new_chat)
                            self.db.commit()
                            self.db.refresh(new_chat)

                        # create notifications for both users
                        try:
                            user1_profile = p1
                            user2_profile = p2
                            if user1_profile and user2_profile:
                                new_notification_user1 = Notification()
                                new_notification_user1.user_id = u1
                                new_notification_user1.notification_type = 'new_match'
                                new_notification_user1.title = "It's a Match! 🎉"
                                new_notification_user1.message_body = f"You and {user2_profile.first_name} are now matched."
                                new_notification_user1.related_entity_type = 'match'
                                new_notification_user1.related_entity_id = existing.match_id
                                self.db.add(new_notification_user1)

                                new_notification_user2 = Notification()
                                new_notification_user2.user_id = u2
                                new_notification_user2.notification_type = 'new_match'
                                new_notification_user2.title = "It's a Match! 🎉"
                                new_notification_user2.message_body = f"You and {user1_profile.first_name} are now matched."
                                new_notification_user2.related_entity_type = 'match'
                                new_notification_user2.related_entity_id = existing.match_id
                                self.db.add(new_notification_user2)

                                self.db.commit()
                                self.db.refresh(new_notification_user1)
                                self.db.refresh(new_notification_user2)

                                # send FCM notifications
                                try:
                                    user1 = self.db.query(User).filter(User.user_id == u1).first()
                                    user2 = self.db.query(User).filter(User.user_id == u2).first()
                                    if user1 and user2 and user1.profile and user2.profile:
                                        notification_user1 = {
                                            'notification_id': new_notification_user1.notification_id,
                                            'user_id': user1.user_id,
                                            'notification_type': new_notification_user1.notification_type,
                                            'title': new_notification_user1.title,
                                            'message_body': new_notification_user1.message_body,
                                            'related_entity_type': new_notification_user1.related_entity_type,
                                            'related_entity_id': new_notification_user1.related_entity_id,
                                            'created_at': new_notification_user1.created_at.isoformat()
                                        }
                                        notification_user2 = {
                                            'notification_id': new_notification_user2.notification_id,
                                            'user_id': user2.user_id,
                                            'notification_type': new_notification_user2.notification_type,
                                            'title': new_notification_user2.title,
                                            'message_body': new_notification_user2.message_body,
                                            'related_entity_type': new_notification_user2.related_entity_type,
                                            'related_entity_id': new_notification_user2.related_entity_id,
                                            'created_at': new_notification_user2.created_at.isoformat()
                                        }

                                        send_notification_to_user(
                                            user=user2,
                                            title=new_notification_user2.title,
                                            body=new_notification_user2.message_body,
                                            data=notification_user2
                                        )
                                        send_notification_to_user(
                                            user=user1,
                                            title=new_notification_user1.title,
                                            body=new_notification_user1.message_body,
                                            data=notification_user1
                                        )
                                except Exception:
                                    # best-effort: don't fail the whole operation on push errors
                                    pass
                        except Exception:
                            pass
                except Exception:
                    pass
            return existing

        # create new match only if both verified for active matches
        if not both_verified and status == 'active':
            return None

        new_match = Match()
        new_match.user1_id = u1
        new_match.user2_id = u2
        new_match.compatibility_score = score
        new_match.match_status = status
        new_match.match_type = match_type or 'score_only'
        self.db.add(new_match)
        self.db.commit()
        self.db.refresh(new_match)
        # side effects: if the match is active, create chat, notifications and send FCM
        try:
            if new_match.match_status == 'active':
                # ensure chat exists
                existing_chat = self.db.query(Chat).filter(
                    ((Chat.initiator_user_id == u1) & (Chat.receiver_user_id == u2)) |
                    ((Chat.initiator_user_id == u2) & (Chat.receiver_user_id == u1))
                ).first()
                if not existing_chat:
                    new_chat = Chat()
                    new_chat.match_id = new_match.match_id
                    new_chat.initiator_user_id = u1
                    new_chat.receiver_user_id = u2
                    new_chat.state = 'active'
                    self.db.add(new_chat)
                    self.db.commit()
                    self.db.refresh(new_chat)

                # create notifications for both users
                try:
                    if p1 and p2:
                        new_notification_user1 = Notification()
                        new_notification_user1.user_id = u1
                        new_notification_user1.notification_type = 'new_match'
                        new_notification_user1.title = "It's a Match! 🎉"
                        new_notification_user1.message_body = f"You and {p2.first_name} are now matched."
                        new_notification_user1.related_entity_type = 'match'
                        new_notification_user1.related_entity_id = new_match.match_id
                        self.db.add(new_notification_user1)

                        new_notification_user2 = Notification()
                        new_notification_user2.user_id = u2
                        new_notification_user2.notification_type = 'new_match'
                        new_notification_user2.title = "It's a Match! 🎉"
                        new_notification_user2.message_body = f"You and {p1.first_name} are now matched."
                        new_notification_user2.related_entity_type = 'match'
                        new_notification_user2.related_entity_id = new_match.match_id
                        self.db.add(new_notification_user2)

                        self.db.commit()
                        self.db.refresh(new_notification_user1)
                        self.db.refresh(new_notification_user2)

                        # send FCM notifications
                        try:
                            user1 = self.db.query(User).filter(User.user_id == u1).first()
                            user2 = self.db.query(User).filter(User.user_id == u2).first()
                            if user1 and user2 and user1.profile and user2.profile:
                                notification_user1 = {
                                    'notification_id': new_notification_user1.notification_id,
                                    'user_id': user1.user_id,
                                    'notification_type': new_notification_user1.notification_type,
                                    'title': new_notification_user1.title,
                                    'message_body': new_notification_user1.message_body,
                                    'related_entity_type': new_notification_user1.related_entity_type,
                                    'related_entity_id': new_notification_user1.related_entity_id,
                                    'created_at': new_notification_user1.created_at.isoformat()
                                }
                                notification_user2 = {
                                    'notification_id': new_notification_user2.notification_id,
                                    'user_id': user2.user_id,
                                    'notification_type': new_notification_user2.notification_type,
                                    'title': new_notification_user2.title,
                                    'message_body': new_notification_user2.message_body,
                                    'related_entity_type': new_notification_user2.related_entity_type,
                                    'related_entity_id': new_notification_user2.related_entity_id,
                                    'created_at': new_notification_user2.created_at.isoformat()
                                }

                                send_notification_to_user(
                                    user=user2,
                                    title=new_notification_user2.title,
                                    body=new_notification_user2.message_body,
                                    data=notification_user2
                                )
                                send_notification_to_user(
                                    user=user1,
                                    title=new_notification_user1.title,
                                    body=new_notification_user1.message_body,
                                    data=notification_user1
                                )
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

        return new_match

    def create_match_if_eligible(self, user1_id: int, user2_id: int):
        """Check a single pair for eligibility using compatibility score and likes, then create/upsert match."""
        # sanity: avoid self-match
        if user1_id == user2_id:
            return None

        # Load users
        u1 = self._get_user(user1_id)
        u2 = self._get_user(user2_id)
        if not u1 or not u2:
            return None

        # must both have profiles
        if not getattr(u1, 'profile', None) or not getattr(u2, 'profile', None):
            return None

        score = self.scorer.calculate_mutual_score(u1, u2)
        if score >= 80.0:
            return self._upsert_match(user1_id, user2_id, score=score, status='active', match_type='score_only')

        if 50.0 <= score < 80.0:
            # require mutual like
            if self._has_mutual_like(user1_id, user2_id):
                return self._upsert_match(user1_id, user2_id, score=score, status='active',
                                          match_type='mutual_like_and_score')
            return None

        return None

    # -------------------------------------------------------
    # Main processing methods
    # -------------------------------------------------------

    def create_matches_from_recs(self, user_id: int, limit: int = 50):
        """Generate recommendations for `user_id`, then evaluate top candidates to create matches per rules.

        Returns a list of Match objects created or updated.
        """
        # Refresh recommendations (this persists Recommendation rows)
        try:
            self.recommender.recommend(user_id, top_n=limit)
        except Exception:
            # best-effort: continue to read any existing recommendations
            pass

        recs = self.db.query(Recommendation).filter(
            Recommendation.user_id == user_id,
            Recommendation.status == 'active'
        ).order_by(Recommendation.recommendation_score.desc()).limit(limit).all()

        created = []
        user = self._get_user(user_id)
        if not user:
            return created

        for rec in recs:
            candidate_id = rec.recommended_user_id
            candidate = self._get_user(candidate_id)
            if not candidate:
                continue

            try:
                score = self.scorer.calculate_mutual_score(user, candidate)
            except Exception:
                score = 0.0

            match_obj = None
            if score >= 80.0:
                match_obj = self._upsert_match(user_id, candidate_id, score=score, status='active',
                                               match_type='score_only')
            elif 50.0 <= score < 80.0:
                if self._has_mutual_like(user_id, candidate_id):
                    match_obj = self._upsert_match(user_id, candidate_id, score=score, status='active',
                                                   match_type='mutual_like_and_score')

            if match_obj:
                created.append(match_obj)

        return created
