import difflib
import math
from datetime import date
from typing import Dict, Union, List, Tuple

# Import SentenceTransformer for Semantic Matching
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from app.models.preference import Preference
from app.models.profile import Profile
from app.models.user import User


class CompatibilityScorer:
    """
    Advanced Two-Way Compatibility Scorer.

    Hybrid Logic:
    1. Strict: Age, Height, Marital Status (Finite sets).
    2. Fuzzy (String Distance): City, Caste, Religion (Semi-structured).
    3. Semantic (AI Vectors): Profession, Education, Bio (Free text).
    """

    # Singleton Model to avoid reloading
    _embedding_model = None

    DEFAULT_WEIGHTS: Dict[str, Union[int, float]] = {
        "demographics": 25,
        "core_values": 35,
        "lifestyle": 15,
        "background": 15,
        "cultural": 10,
    }

    # Keep normalization for common Nepali abbreviations
    NORMALIZATION_MAP = {
        "ktm": "kathmandu", "bkt": "bhaktapur", "pok": "pokhara",
        "patan": "lalitpur", "birat": "biratnagar", "ktm.": "kathmandu"
    }

    def _init_(self, custom_weights: Dict[str, Union[int, float]] | None = None):
        self.weights = self.DEFAULT_WEIGHTS.copy()
        if custom_weights:
            self.weights.update(custom_weights)

        # Initialize Model only if needed (Singleton)
        if CompatibilityScorer._embedding_model is None:
            # We use the CPU device explicitly to avoid VRAM issues on standard servers
            CompatibilityScorer._embedding_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
        self.model = CompatibilityScorer._embedding_model

    def calculate_mutual_score(self, user_a: User, user_b: User) -> float:
        if not all([user_a.profile, user_a.preferences, user_b.profile, user_b.preferences]):
            return 0.0

        score_a_for_b = self._calculate_directional_score(user_a, user_b)
        score_b_for_a = self._calculate_directional_score(user_b, user_a)

        if score_a_for_b <= 0 or score_b_for_a <= 0:
            return 0.0

        mutual_score = math.sqrt(score_a_for_b * score_b_for_a)
        return round(mutual_score * 100, 2)

    def _calculate_directional_score(self, perspective_user: User, candidate_user: User) -> float:
        p_prof, p_prefs = perspective_user.profile, perspective_user.preferences
        c_prof = candidate_user.profile

        scores = {
            "demographics": self._score_category([
                (self._score_age(c_prof, p_prefs, p_prof), 1.0),
                (self._score_height(c_prof, p_prefs, p_prof), 0.5),
            ]),
            "core_values": self._score_category([
                # USE FUZZY for semi-structured fields
                (self._score_fuzzy(c_prof.religion_text, p_prefs.preferred_religions_text, p_prof.religion_text), 1.0),
                (self._score_fuzzy(c_prof.caste_text, p_prefs.preferred_castes_text, p_prof.caste_text), 1.0),
                (self._score_text_strict(c_prof.manglik_status, p_prefs.preferred_manglik_status,
                                         p_prof.manglik_status), 1.0),
            ]),
            "lifestyle": self._score_category([
                # STRICT for finite options
                (self._score_text_strict(c_prof.marital_status, p_prefs.preferred_marital_status_text,
                                         p_prof.marital_status), 1.0),
                (self._score_text_strict(c_prof.dietary_preferences, p_prefs.preferred_dietary_habits,
                                         p_prof.dietary_preferences), 0.5),
                (self._score_text_strict(c_prof.smoking_habits, p_prefs.preferred_smoking_habits,
                                         p_prof.smoking_habits), 0.3),
                (self._score_text_strict(c_prof.drinking_habits, p_prefs.preferred_drinking_habits,
                                         p_prof.drinking_habits), 0.3),
            ]),
            "background": self._score_category([
                # USE SEMANTIC AI for free text fields
                (self._score_semantic(c_prof.education_level_text, p_prefs.preferred_education_levels_text,
                                      p_prof.education_level_text), 1.0),
                (self._score_semantic(c_prof.profession_text, p_prefs.preferred_professions_text,
                                      p_prof.profession_text), 1.0),
                # FUZZY for locations (Handles Ktm vs Kathmandu)
                (self._score_fuzzy(c_prof.city_text, p_prefs.preferred_locations_text, p_prof.city_text), 0.7),
            ]),
            "cultural": self._score_gotra(c_prof.gotra, p_prof.gotra),
        }

        total_score = sum(scores[cat] * self.weights[cat] for cat in self.weights if cat in scores)
        total_weight = sum(self.weights[cat] for cat in self.weights if cat in scores)

        return total_score / total_weight if total_weight > 0 else 0.0

    # --- 1. SEMANTIC AI SCORING (The New Logic) ---

    def _score_semantic(self, candidate_val: str, explicit_pref: str, fallback_val: str) -> float:
        """Uses Vectors to compare values. Handles 'SDE' vs 'Software Engineer'."""
        target_text = self._resolve_text_preference(explicit_pref, fallback_val)
        if target_text is None or 'any' in target_text.lower():
            return 1.0
        if not candidate_val:
            return 0.5  # Neutral

        # Optimization: Check exact match first to avoid AI computation
        targets_list = [x.strip().lower() for x in target_text.split(',')]
        if candidate_val.strip().lower() in targets_list:
            return 1.0

        # AI Matching
        try:
            vec_cand = self.model.encode(candidate_val, convert_to_tensor=False)
            targets = [t.strip() for t in target_text.split(',')]
            vec_targets = self.model.encode(targets, convert_to_tensor=False)

            # Compute Cosine Similarity against all targets and take the best one
            sims = cosine_similarity([vec_cand], vec_targets)[0]
            return float(max(sims))
        except Exception:
            # Fallback to fuzzy if AI fails (e.g. model load issue)
            return self._score_fuzzy(candidate_val, explicit_pref, fallback_val)

    # --- 2. FUZZY SCORING ---

    def _score_fuzzy(self, candidate_val, explicit_pref, fallback_val) -> float:
        target_text = self._resolve_text_preference(explicit_pref, fallback_val)
        if target_text is None or 'any' in target_text.lower(): return 1.0
        if not candidate_val: return 0.5

        c_norm = self.NORMALIZATION_MAP.get(candidate_val.strip().lower(), candidate_val.strip().lower())
        targets = [self.NORMALIZATION_MAP.get(t.strip().lower(), t.strip().lower()) for t in target_text.split(',')]

        if c_norm in targets: return 1.0

        # Check fuzzy match
        for t in targets:
            if t in c_norm or c_norm in t: return 0.8
            if difflib.SequenceMatcher(None, c_norm, t).ratio() > 0.85: return 0.9

        return 0.0

    # --- 3. STRICT SCORING ---

    def _score_text_strict(self, candidate_val, explicit_pref, fallback_val) -> float:
        target_text = self._resolve_text_preference(explicit_pref, fallback_val)
        if target_text is None or 'any' in target_text.lower(): return 1.0
        if not candidate_val: return 0.5

        targets = [t.strip().lower() for t in target_text.split(',')]
        if candidate_val.strip().lower() in targets:
            return 1.0
        return 0.0

    # --- Helpers ---

    def _resolve_text_preference(self, explicit_pref, fallback_prof_value) -> str | None:
        if explicit_pref is not None:
            pref_str = str(explicit_pref).strip()
            if pref_str and pref_str.lower() != 'any': return pref_str
        if fallback_prof_value is not None:
            return str(fallback_prof_value).strip()
        return None

    def _resolve_numeric_preference(self, explicit_pref, fallback_prof_value) -> Union[int, float, None]:
        if isinstance(explicit_pref, (int, float)): return explicit_pref
        if isinstance(fallback_prof_value, (int, float)): return fallback_prof_value
        return None

    def _score_gotra(self, candidate_gotra: str | None, perspective_gotra: str | None) -> float:
        if not candidate_gotra or not perspective_gotra: return 1.0
        c_norm = candidate_gotra.strip().lower()
        p_norm = perspective_gotra.strip().lower()
        if difflib.SequenceMatcher(None, c_norm, p_norm).ratio() > 0.85:
            return 0.0  # Fail
        return 1.0

    def _get_age(self, profile: Profile) -> int | None:
        if not profile or not profile.date_of_birth: return None
        today = date.today()
        return today.year - profile.date_of_birth.year - (
                (today.month, today.day) < (profile.date_of_birth.month, profile.date_of_birth.day))

    def _score_age(self, candidate_profile: Profile, p_prefs: Preference, p_profile: Profile) -> float:
        candidate_age = self._get_age(candidate_profile)
        if candidate_age is None: return 0.5
        p_user_age = self._get_age(p_profile)
        min_pref = self._resolve_numeric_preference(p_prefs.min_age, p_user_age - 5 if p_user_age else None)
        max_pref = self._resolve_numeric_preference(p_prefs.max_age, p_user_age + 5 if p_user_age else None)
        if min_pref is None or max_pref is None: return 1.0
        if min_pref <= candidate_age <= max_pref: return 1.0

        center = (min_pref + max_pref) / 2
        span = (max_pref - min_pref) / 2
        if span <= 0: return 1.0 if candidate_age == center else 0.0

        if abs(candidate_age - center) <= span * 1.5: return 0.5
        return 0.0

    def _score_height(self, candidate_profile: Profile, p_prefs: Preference, p_profile: Profile) -> float:
        c_height = candidate_profile.height_cm
        if c_height is None: return 0.5
        p_height = p_profile.height_cm
        min_pref = self._resolve_numeric_preference(p_prefs.min_height_cm, p_height)
        max_pref = self._resolve_numeric_preference(p_prefs.max_height_cm, p_height)
        if min_pref is None or max_pref is None: return 1.0
        if min_pref <= c_height <= max_pref: return 1.0
        return 0.0

    def _score_category(self, scores_with_weights: List[Tuple[float, float]]) -> float:
        total_score, total_weight = 0, 0
        for score, weight in scores_with_weights:
            total_score += score * weight
            total_weight += weight
        return total_score / total_weight if total_weight > 0 else 0.5