
from sqlalchemy import text

from app.database import SessionLocal
from app.models.recommender import Recommendation
from app.models.interaction import Match
from app.models.user import User
from utilities.logging_config import logger
from utilities.recsys.match_maker import MatchMaker


def seed(db):
    """
    Run matchmaking and recommendation engine for all users.

    This function uses short-lived sessions per user to prevent DB timeouts
    on serverless databases during long computations.

    Args:
        db: The main database session (will be closed and not used;
            we create our own sessions for this operation)
    """
    logger.info("=" * 80)
    logger.info("STARTING MATCHMAKING AND RECOMMENDATIONS GENERATION")
    logger.info("=" * 80)

    # Close the provided db session as we'll manage our own
    db.close()

    # Get all user IDs first with a fresh session
    main_db = SessionLocal()
    try:
        user_ids = [u.user_id for u in main_db.query(User.user_id).order_by(User.user_id).all()]
        logger.info(f"Found {len(user_ids)} users to process")
    finally:
        main_db.close()

    total_users = len(user_ids)
    success_count, failed_count = 0, 0
    total_matches_created = 0

    # Process each user with its own session
    for i, user_id in enumerate(user_ids, 1):
        db_loop = SessionLocal()
        try:
            # Keep-alive query to prevent serverless DB from sleeping
            db_loop.execute(text("SELECT 1"))

            user = db_loop.get(User, user_id)
            if not user:
                logger.warning(f"[{i}/{total_users}] Could not find user with ID: {user_id}. Skipping.")
                failed_count += 1
                continue

            logger.info(f"[{i}/{total_users}] Processing user: {user.username} (ID: {user.user_id})")

            # Create matches from recommendations
            match_maker = MatchMaker(db_loop)
            created_matches = match_maker.create_matches_from_recs(user_id=user.user_id, limit=50)

            matches_count = len(created_matches)
            total_matches_created += matches_count
            logger.info(f"  ✓ Created {matches_count} matches for {user.username}")
            success_count += 1

        except Exception as e:
            logger.error(f"  ❌ Failed for user {user_id}: {str(e)}", exc_info=True)
            failed_count += 1
        finally:
            db_loop.close()

    # Final statistics
    logger.info("\n" + "=" * 80)
    logger.info("MATCHMAKING SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total users processed: {total_users}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {failed_count}")
    logger.info(f"Total matches created: {total_matches_created}")

    # Get final counts from database
    final_db = SessionLocal()
    try:
        final_recs = final_db.query(Recommendation).count()
        final_matches = final_db.query(Match).count()
        logger.info(f"\nFinal database counts:")
        logger.info(f"  - Recommendations: {final_recs}")
        logger.info(f"  - Matches: {final_matches}")
    finally:
        final_db.close()

    logger.info("=" * 80)
    if failed_count == 0:
        logger.info("✓ MATCHMAKING COMPLETE - ALL USERS PROCESSED SUCCESSFULLY!")
    else:
        logger.warning(f"⚠ MATCHMAKING COMPLETE - {failed_count} user(s) failed")
    logger.info("=" * 80)


if __name__ == "__main__":
    """Allow running this seeder directly for testing."""
    try:
        db = SessionLocal()
        seed(db)
    except Exception as e:
        logger.critical(f"A critical error occurred during matchmaking: {e}", exc_info=True)

