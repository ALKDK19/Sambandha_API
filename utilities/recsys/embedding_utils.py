import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from app.models.profile import Profile
from utilities.logging_config import logger

# Load the model once (on CPU)
model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")


def profile_to_text(profile: Profile) -> str:
    """Convert profile fields into a descriptive text for embedding."""
    parts = [
        profile.bio,
        profile.profession_text,
        profile.education_level_text,
        profile.religion_text,
        profile.caste_text,
        profile.hobbies_interests,
        profile.mother_tongue,
        profile.country
    ]
    return " ".join(filter(None, parts))


def update_profile_embedding(db: Session, profile: Profile):
    """Generate and update a single profile’s embedding."""
    try:
        text = profile_to_text(profile)
        if not text.strip():
            logger.warning(f"Skipping empty profile for user_id={profile.user_id}")
            return
        emb = model.encode(text, convert_to_tensor=False)
        profile.embedding_vector = np.array(emb, dtype=np.float32).tobytes()
        db.add(profile)
        db.commit()
        logger.info(f"✅ Updated embedding for user_id={profile.user_id}")
    except Exception as e:
        logger.error(f"❌ Failed to update embedding for user_id={profile.user_id}: {e}")
        db.rollback()


def warmup_embeddings_on_startup(db: Session):
    """Compute embeddings for all profiles missing them."""
    logger.info("🚀 Warming up embeddings for all profiles without vectors...")
    profiles = db.query(Profile).filter(Profile.embedding_vector.is_(None)).all()
    if not profiles:
        logger.info("✅ All profiles already have embeddings. Skipping warmup.")
        return
    for p in profiles:
        update_profile_embedding(db, p)
    logger.info("🔥 Embedding warmup completed successfully.")
