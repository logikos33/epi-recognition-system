"""Migration runner with graceful error handling."""
import logging
import os

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "sql")


def run_migrations(db_pool) -> dict:
    """
    Run all SQL migrations idempotently.
    Each migration failure is logged but does NOT stop the system.
    Returns dict with results per migration.
    """
    results = {"ok": [], "failed": [], "skipped": []}

    if not db_pool.is_available:
        logger.warning("Database unavailable — skipping migrations")
        return results

    # Ensure migration tracking table exists
    _ensure_migrations_table(db_pool)

    migration_files = sorted(
        f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql")
    )

    for filename in migration_files:
        migration_id = filename
        if _is_applied(db_pool, migration_id):
            results["skipped"].append(migration_id)
            continue

        filepath = os.path.join(MIGRATIONS_DIR, filename)
        try:
            with open(filepath) as f:
                sql = f.read()
            with db_pool.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(sql)
                cur.execute(
                    "INSERT INTO _migrations (id) VALUES (%s) ON CONFLICT DO NOTHING",
                    (migration_id,),
                )
            results["ok"].append(migration_id)
            logger.info("[MIGRATION] Applied: %s", migration_id)
        except Exception as e:
            results["failed"].append(migration_id)
            logger.warning(
                "[MIGRATION] Failed %s (degraded): %s", migration_id, e
            )

    if results["failed"]:
        logger.warning(
            "[MIGRATIONS] %d failed — affected features degraded. OK: %d, Skipped: %d",
            len(results["failed"]),
            len(results["ok"]),
            len(results["skipped"]),
        )
    else:
        logger.info(
            "[MIGRATIONS] All OK (%d applied, %d skipped)",
            len(results["ok"]),
            len(results["skipped"]),
        )

    return results


def _ensure_migrations_table(db_pool) -> None:
    with db_pool.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)


def _is_applied(db_pool, migration_id: str) -> bool:
    with db_pool.get_cursor() as cur:
        cur.execute("SELECT 1 FROM _migrations WHERE id = %s", (migration_id,))
        return cur.fetchone() is not None
