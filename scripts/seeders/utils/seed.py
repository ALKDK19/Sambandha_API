"""
Seed runner for Sambandha API.

Usage (from project root - same folder as main.py):
    python -m scripts.seed list
    python -m scripts.seed run 001_initial_admin
    python -m scripts.seed run-all

Design:
- Discover seed modules in `scripts.seeders` package.
- Each seeder is a module that exposes a `seed(db)` function (or `run(db)` fallback).
- Seed modules should be idempotent.
- Runner handles transactions and logs.

This keeps seeding organized and similar to Laravel: numbered seed files, easy to run individually or all.
"""
import argparse
import importlib
import pkgutil
import difflib
from typing import List

import app.models as app_models
from app.database import SessionLocal
from utilities.logging_config import logger

# Make sure project root is importable when running as module
# When you run `python -m scripts.seed` from project root, sys.path already contains project root.

SEEDERS_PACKAGE = "scripts.seeders"


def discover_seed_modules() -> List[str]:
    """Return a sorted list of module names available under scripts.seeders"""
    try:
        package = importlib.import_module(SEEDERS_PACKAGE)
    except ModuleNotFoundError:
        return []

    names = []
    for _, modname, ispkg in pkgutil.iter_modules(package.__path__):
        if not ispkg:
            names.append(modname)

    # Sort by filename so numeric prefixes run in order
    names.sort()
    return names


def import_seeder_module(name: str):
    """Import a seeder module by name and provide helpful suggestions on import failure.

    This catches ModuleNotFoundError and suggests close matches from available seeders
    (useful when you mistype a seeder module name at the CLI).
    """
    full = f"{SEEDERS_PACKAGE}.{name}"
    try:
        return importlib.import_module(full)
    except ModuleNotFoundError:
        # Try to offer helpful close-match suggestions
        try:
            available = discover_seed_modules()
            close = difflib.get_close_matches(name, available, n=3, cutoff=0.5)
            if close:
                suggestion = f"Did you mean: {', '.join(close)}?"
            else:
                suggestion = "No close matches found."
        except Exception:
            suggestion = ""
        # Re-raise with augmented message
        raise ModuleNotFoundError(f"No module named '{full}'. {suggestion}")


def import_all_model_modules():
    """Import all modules in app.models to ensure SQLAlchemy mappers and relationships are configured.

    Some models reference other classes by name in relationships; importing all model modules
    guarantees those class names are available to the mapper and avoids "failed to locate a name" errors.
    """
    try:
        for _, modname, ispkg in pkgutil.iter_modules(app_models.__path__):
            # skip packages
            if ispkg:
                continue
            # import each model module (e.g., app.models.user, app.models.profile)
            importlib.import_module(f"app.models.{modname}")
    except Exception:
        # Don't crash the runner here; let actual seeder run report detailed errors
        logger.exception("Failed while importing model modules")


def run_seeder_module(name: str) -> bool:
    # Ensure models are imported so SQLAlchemy relationships are registered
    import_all_model_modules()
    logger.info(f"Running seeder: {name}")
    db = SessionLocal()
    try:
        mod = import_seeder_module(name)

        # Prefer 'seed' function, fall back to 'run'
        seeder_fn = getattr(mod, "seed", None) or getattr(mod, "run", None)
        if not seeder_fn:
            logger.error(f"Seeder module {name} does not expose a 'seed' or 'run' function")
            return False

        seeder_fn(db)
        db.commit()
        logger.info(f"Seeder {name} completed successfully")
        return True
    except Exception as e:
        logger.exception(f"Seeder {name} failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return False
    finally:
        db.close()


def list_seeders() -> List[str]:
    mods = discover_seed_modules()
    return mods


def run_all_seeders():
    mods = discover_seed_modules()
    if not mods:
        logger.warning("No seeders found.")
        return

    for name in mods:
        success = run_seeder_module(name)
        if not success:
            logger.error(f"Stopping seed run due to failure in {name}")
            break


def main():
    parser = argparse.ArgumentParser(description="Seeder runner")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("list", help="List available seeders")

    run_p = sub.add_parser("run", help="Run a single seeder (by module name, e.g. 001_initial_admin)")
    run_p.add_argument("name", help="Seeder module name to run")

    sub.add_parser("run-all", help="Run all seeders in order")

    args = parser.parse_args()

    if args.cmd == "list":
        mods = list_seeders()
        if not mods:
            print("No seeders found in scripts/seeders")
            return
        print("Available seeders:")
        for m in mods:
            print(" -", m)

    elif args.cmd == "run":
        # No changes required to run 002_seed_complete_users.py — use:
        #   python -m scripts.seed run 002_seed_complete_users
        # or
        #   python -m scripts.seeders.002_seed_complete_users
        run_seeder_module(args.name)

    elif args.cmd == "run-all":
        run_all_seeders()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
