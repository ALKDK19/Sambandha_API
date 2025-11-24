from datetime import datetime, date, timezone

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import joinedload

from app.models.interaction import Like, Match, ProfileVisit
from app.models.profile import Profile
from app.models.recommender import Recommendation
from app.models.security import BlockedUser
from app.models.user import User


class Recommender:
    """
    Triple-Layer Hybrid Recommender:
    1. Attribute Scoring: Strict checking of Age, Height, Marital Status against Preferences.
    2. Semantic Scoring (Embeddings): Handles "Ktm" vs "Kathmandu", "Climbing" vs "Mountaineering".
       - Acts as the "Implicit Profile Similarity" logic.
    3. Collaborative Scoring: Popularity booster.

    Special Logic:
    - Gotra: Enforces DISSIMILARITY for implicit profile checks.
    """

    # Load model once as a static class attribute to save RAM
    _embedding_model = None

    def __init__(self, session):
        self.session = session

        # Initialize Model (Singleton pattern)
        if Recommender._embedding_model is None:
            Recommender._embedding_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
        self.model = Recommender._embedding_model
        self._embedding_cache = {}

        self.behavior_weights = {
            "visit": 0.25, "like": 0.5, "superlike": 0.8, "match": 1.0
        }

        # Weights
        self.W_PREF_HIT = 1.0  # Exact Pref Match
        self.W_SEMANTIC_SIM = 0.6  # Implicit Profile Match (Vector)
        self.W_GOTRA_BONUS = 0.5  # Gotra Dissimilarity Bonus
        self.COLLAB_BOOST_FACTOR = 0.5

    # ------------------------------------------------------------------
    # HELPERS: Embeddings & Age
    # ------------------------------------------------------------------
    def _load_embedding(self, profile):
        """Safely loads the binary embedding vector."""
        if not profile: return None
        uid = profile.user_id
        if uid in self._embedding_cache:
            return self._embedding_cache[uid]

        raw = getattr(profile, "embedding_vector", None)

        # Fallback: If DB has no vector, compute it on the fly (slower but safer)
        if not raw:
            text = " ".join(filter(None, [
                profile.bio, profile.profession_text, profile.city_text,
                profile.hobbies_interests, profile.education_field_text
            ]))
            if text.strip():
                vec = self.model.encode(text, convert_to_tensor=False)
                return np.array(vec, dtype=np.float32)
            return None

        try:
            arr = np.frombuffer(raw, dtype=np.float32).copy()
            self._embedding_cache[uid] = arr
            return arr
        except Exception:
            return None

    def _get_age(self, profile):
        if not profile or not profile.date_of_birth: return None
        today = date.today()
        return today.year - profile.date_of_birth.year - (
                (today.month, today.day) < (profile.date_of_birth.month, profile.date_of_birth.day))

    # ------------------------------------------------------------------
    # SPECIAL FIELD LOGIC
    # ------------------------------------------------------------------
    def _score_gotra(self, cand_gotra, user_pref_gotra_text, user_prof_gotra):
        """
        Special Logic for Gotra:
        - Pref Set & Match = High Boost
        - Pref Not Set -> Profile Check -> MUST BE DIFFERENT for Boost
        """
        if not cand_gotra: return 0.0
        cand_g = cand_gotra.strip().lower()

        # 1. Explicit Preference (If user explicitly says "I want Gotra X" - rare but possible)
        if user_pref_gotra_text and 'any' not in user_pref_gotra_text.lower():
            wanted = [x.strip().lower() for x in user_pref_gotra_text.split(',')]
            if cand_g in wanted:
                return self.W_PREF_HIT

        # 2. Implicit Profile Check (The "Anti-Similarity" Rule)
        # If I am Gotra A, I should NOT marry Gotra A.
        if user_prof_gotra:
            user_g = user_prof_gotra.strip().lower()
            if user_g != cand_g:
                # They are different! Good!
                return self.W_GOTRA_BONUS
            else:
                # They are same! Bad! (Penalty or 0)
                return 0.0

        # 3. Fallback (User has no Gotra data) -> Assume OK
        return self.W_GOTRA_BONUS

    def _score_attribute_strict(self, cand_val, user_pref_val, is_numeric=False):
        """Strict checking only for Explicit Preferences (Rule 1)."""
        if user_pref_val is None: return 0.0

        if is_numeric:
            min_v, max_v = user_pref_val
            if cand_val is not None and min_v <= cand_val <= max_v:
                return self.W_PREF_HIT
        else:
            if isinstance(user_pref_val, str) and 'any' in user_pref_val.lower():
                return self.W_PREF_HIT / 2  # 'Any' gets half points

            if cand_val:
                wanted = [x.strip().lower() for x in str(user_pref_val).split(',')]
                if str(cand_val).strip().lower() in wanted:
                    return self.W_PREF_HIT
        return 0.0

    # ------------------------------------------------------------------
    # MAIN COMPUTATION
    # ------------------------------------------------------------------
    def _compute_content_scores(self, user):
        # 1. Strict Gender Filter
        base_query = self.session.query(Profile).filter(Profile.user_id != user.user_id)
        if user.preferences.looking_for:
            genders = [g.strip() for g in user.preferences.looking_for.split(',') if g.strip()]
            if genders and 'Any' not in genders:
                base_query = base_query.filter(Profile.gender.in_(genders))

        candidates = base_query.all()
        if not candidates: return {}

        u_prof = user.profile
        u_pref = user.preferences
        u_age = self._get_age(u_prof)
        u_vec = self._load_embedding(u_prof)  # User's semantic vector

        scores = {}

        # Prepare candidate vectors for batch processing (faster)
        cand_ids = []
        cand_vecs = []
        cand_objs = []

        for cand in candidates:
            vec = self._load_embedding(cand)
            if vec is not None:
                cand_ids.append(cand.user_id)
                cand_vecs.append(vec)
                cand_objs.append(cand)

        # Calculate Semantic Similarity (Rule 2 - Implicit fuzzy matching)
        # This handles "Ktm" approx "Kathmandu", "Climbing" approx "Mountaineering"
        semantic_scores = {}
        if u_vec is not None and cand_vecs:
            matrix = np.vstack(cand_vecs)
            try:
                # Cosine similarity returns -1 to 1. We map negatives to 0.
                sims = cosine_similarity([u_vec], matrix)[0]
                for i, uid in enumerate(cand_ids):
                    semantic_scores[uid] = max(0.0, float(sims[i]))
            except:
                pass

        # Attribute Loop
        for cand in cand_objs:
            uid = cand.user_id
            attr_score = 0.0
            total_checks = 0

            # --- A. Explicit Preference Checks (Strict) ---
            # Age
            c_age = self._get_age(cand)
            attr_score += self._score_attribute_strict(c_age,
                                                       (u_pref.min_age, u_pref.max_age) if u_pref.min_age else None,
                                                       True)
            total_checks += 1

            # Height
            attr_score += self._score_attribute_strict(cand.height_cm, (u_pref.min_height_cm,
                                                                        u_pref.max_height_cm) if u_pref.min_height_cm else None,
                                                       True)
            total_checks += 1

            # Marital Status
            attr_score += self._score_attribute_strict(cand.marital_status, u_pref.preferred_marital_status_text)
            total_checks += 1

            # --- B. Special Gotra Check ---
            # Does strict check OR implicit dissimilarity check
            gotra_points = self._score_gotra(cand.gotra, None,
                                             u_prof.gotra)  # Passing None for pref to force implicit check mostly
            attr_score += gotra_points
            total_checks += 1

            # --- C. Combine Scores ---
            # 1. Attribute Score (Normalized)
            normalized_attr = attr_score / total_checks if total_checks > 0 else 0

            # 2. Semantic Score (The Embeddings)
            # This covers Profession, City, Bio, Hobbies with fuzzy matching logic
            sem_score = semantic_scores.get(uid, 0.0)

            # Weighted Sum:
            # Attributes (Strict Matches) are worth 60%
            # Semantics (Implicit Fuzzy Matches) are worth 40%
            final_content_score = (0.6 * normalized_attr) + (0.4 * sem_score)

            # Double Boost Logic (if both are high)
            if normalized_attr > 0.5 and sem_score > 0.7:
                final_content_score += 0.2

            scores[uid] = final_content_score

        return scores

    # ------------------------------------------------------------------
    # COLLABORATIVE & COMBINE (Same as before)
    # ------------------------------------------------------------------
    def _compute_collaborative_scores(self, user_id):
        # ... (Same collaborative logic as previous answer) ...
        user_ids = [u.user_id for u in self.session.query(User.user_id).filter(User.user_id != user_id).all()]
        if not user_ids: return {}
        interactions = self._get_user_interactions(user_id)
        similarities = {}
        for other_id in user_ids:
            other_interactions = self._get_user_interactions(other_id)
            sim = self._interaction_similarity(interactions, other_interactions)
            if sim > 0: similarities[other_id] = sim
        return similarities

    def _get_user_interactions(self, user_id):
        interactions = {}
        for (tid,) in self.session.query(ProfileVisit.visited_profile_user_id).filter(
                ProfileVisit.visitor_user_id == user_id).all():
            interactions[tid] = interactions.get(tid, 0) + self.behavior_weights["visit"]
        for tid, ltype in self.session.query(Like.liked_user_id, Like.like_type).filter(
                Like.liker_user_id == user_id).all():
            weight = self.behavior_weights.get("superlike" if ltype == "super_like" else "like", 0.5)
            interactions[tid] = interactions.get(tid, 0) + weight
        for m in self.session.query(Match).filter((Match.user1_id == user_id) | (Match.user2_id == user_id)).all():
            other = m.user1_id if m.user2_id == user_id else m.user2_id
            interactions[other] = interactions.get(other, 0) + self.behavior_weights["match"]
        return interactions

    def _interaction_similarity(self, a, b):
        if not a or not b: return 0.0
        shared = set(a.keys()) & set(b.keys())
        if not shared: return 0.0
        num = sum(a[i] * b[i] for i in shared)
        denom = np.sqrt(sum(v ** 2 for v in a.values())) * np.sqrt(sum(v ** 2 for v in b.values()))
        return num / denom if denom else 0.0

    def _combine_scores(self, content, collab):
        all_ids = set(content) | set(collab)
        final_scores = {}
        for uid in all_ids:
            c_score = content.get(uid, 0)
            col_score = collab.get(uid, 0)
            # Booster Logic
            final_scores[uid] = c_score + (self.COLLAB_BOOST_FACTOR * col_score)
        return final_scores

    def _save_recommendations(self, user_id, ranked_results):
        self.session.query(Recommendation).filter(
            Recommendation.user_id == user_id,
            Recommendation.status == "pending"
        ).update({"status": "stale"}, synchronize_session=False)
        now = datetime.now(timezone.utc)
        for target_id, score in ranked_results:
            rec = Recommendation(
                user_id=user_id,
                recommended_user_id=target_id,
                recommendation_score=float(score),
                created_at=now,
                status="active",
            )
            self.session.add(rec)
        self.session.commit()

    # -------------------------------------------------------------
    # MAIN ENTRY POINT
    # -------------------------------------------------------------

    def recommend(self, user_id, top_n=20):
        """
        Main entry point.
        Strategy:
        1. Compute Scores.
        2. Filter Eligibility.
        3. Thresholding: Keep candidates > 0.6.
        4. Safety Net: If 0 candidates pass threshold, keep top 5 best available.
        """
        user = self.session.query(User).options(joinedload(User.profile), joinedload(User.preferences)).filter(
            User.user_id == user_id).first()
        if not user or not user.profile: return []

        # 1. Content
        content_scores = self._compute_content_scores(user)

        # 2. Collab
        collab_scores = self._compute_collaborative_scores(user_id)

        # 3. Combine
        combined = self._combine_scores(content_scores, collab_scores)

        # 4. Eligibility Filtering
        blocked_user_ids = {r[0] for r in self.session.query(BlockedUser.blocked_user_id).filter(
            BlockedUser.blocker_user_id == user.user_id).all()}
        disliked_user_ids = {r[0] for r in
                             self.session.query(Like.liked_user_id).filter(Like.liker_user_id == user.user_id,
                                                                           Like.like_type == 'dislike').all()}
        excluded_ids = blocked_user_ids | disliked_user_ids

        candidate_ids = [uid for uid in combined.keys() if uid not in excluded_ids]
        if not candidate_ids: return []

        eligible_users = (
            self.session.query(User)
            .options(joinedload(User.profile))
            .filter(User.user_id.in_(candidate_ids))
            .filter(User.is_active.is_(True))
            .all()
        )

        filtered_scores = {}
        for u in eligible_users:
            # Basic profile checks
            if not u.profile: continue
            if getattr(u.profile, "is_verified", 0) != 1: continue
            if getattr(u, "is_blocked", False): continue
            if getattr(u.profile, "is_hidden", 0) == 1: continue

            filtered_scores[u.user_id] = combined.get(u.user_id, 0)

        # 5. Sorting
        # Sort ALL valid candidates by score descending
        ranked_candidates = sorted(filtered_scores.items(), key=lambda x: x[1], reverse=True)

        if not ranked_candidates:
            return []

        # 6. Thresholding & Safety Net
        MIN_SCORE_THRESHOLD = 0.6  # Candidates below this failed preferences significantly

        # Filter: Get everyone above the threshold
        high_quality_candidates = [x for x in ranked_candidates if x[1] >= MIN_SCORE_THRESHOLD]

        final_list = []

        if high_quality_candidates:
            # Standard Case: We have good matches. Take top N.
            final_list = high_quality_candidates[:top_n]
        else:
            # Safety Net Case: No one met the threshold (Very strict prefs or small DB).
            # Take the top 5 absolute best available so the UI isn't empty.
            # We limit to 5 (not top_n) to encourage the user to broaden preferences.
            final_list = ranked_candidates[:5]

        # 7. Save
        self._save_recommendations(user_id, final_list)

        return [uid for uid, _ in final_list]
