Seeder system for Sambandha API

Overview

- Seed files live under `scripts/seeders`.
- Name them with numeric prefixes like `001_initial_admin.py` to control order.
- Each seeder module must expose a `seed(db)` function that performs idempotent operations.

Usage

- From the project root (same directory as main.py):

```bash
python -m scripts.seed list        # list available seeders
python -m scripts.seed run 001_initial_admin   # run single seeder
python -m scripts.seed run 002_seed_complete_users  # run specific seeder
python -m scripts.seed run-all    # run all seeders in order
python -m scripts.clean_db
python -m scripts.check_db
python -m scripts.seeders.003_run_matchmaking_and_recommendations 
python -m scripts.seeders.002_seed_complete_users 
```

Notes

- The runner will create/close a DB session for each seeder and commit on success.
- Seeders should be idempotent and safe to run multiple times.
- This is similar in style to Laravel seeders: explicit files, ordered execution, and easy CLI runner.

