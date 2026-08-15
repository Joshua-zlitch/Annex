#!/usr/bin/env python
"""Cloud Run Job: Database Migration Runner.

This script runs as a Cloud Run Job to execute database migrations
during deployment.
"""

import os
import subprocess
import sys


def run_migrations() -> int:
    """Run alembic migrations."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        return 1

    # Ensure we're in the right directory
    os.chdir("/app")

    # Run migrations
    cmd = ["alembic", "upgrade", "head"]
    print(f"Running: {' '.join(cmd)}")
    print(f"DATABASE_URL: {database_url[:50]}...")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        print("Migrations completed successfully")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Migration failed with exit code {e.returncode}")
        print(e.stdout)
        print(e.stderr, file=sys.stderr)
        return e.returncode
    except FileNotFoundError:
        print("ERROR: alembic not found")
        return 1


if __name__ == "__main__":
    sys.exit(run_migrations())