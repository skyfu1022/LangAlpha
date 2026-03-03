#!/usr/bin/env python3
"""
Migration 013: Add conversation_feedback table and convert usages to audit ledger.

1. Creates conversation_feedback table (thumbs up/down ratings with FK to responses).
2. Adds credit_exempt / credit_exempt_reason columns to conversation_usages.
3. Drops FK constraints on conversation_usages (append-only audit ledger).

Idempotent — safe to run multiple times.

Usage:
    uv run python scripts/migrations/013_feedback_and_usages_audit.py
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
load_dotenv(project_root / ".env")

from src.server.database.conversation import get_db_connection_string


async def migrate():
    import psycopg

    db_url = get_db_connection_string()
    print("Migration 013: Feedback table + usages audit ledger")
    print("=" * 55)
    print("Connecting to database...")

    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        async with conn.cursor() as cur:
            # =============================================================
            # 1. Create conversation_feedback table
            # =============================================================
            print("\n-- Creating conversation_feedback table ...")
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS conversation_feedback (
                    conversation_feedback_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    conversation_response_id UUID NOT NULL
                        REFERENCES conversation_responses(conversation_response_id)
                        ON DELETE CASCADE,
                    user_id VARCHAR(255) NOT NULL,
                    rating VARCHAR(20) NOT NULL
                        CHECK (rating IN ('thumbs_up', 'thumbs_down')),
                    issue_categories TEXT[],
                    comment TEXT,
                    consent_human_review BOOLEAN NOT NULL DEFAULT FALSE,
                    review_status VARCHAR(50)
                        CHECK (review_status IN ('pending', 'confirmed', 'rejected')),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CONSTRAINT unique_feedback_per_response_user
                        UNIQUE (conversation_response_id, user_id)
                );
            """)
            await cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_review_status
                ON conversation_feedback(review_status)
                WHERE review_status IS NOT NULL;
            """)
            print("   conversation_feedback OK")

            # Ensure FK constraint for databases that created the table without it
            print("\n-- Ensuring FK constraint on conversation_response_id ...")
            await cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints
                        WHERE table_name = 'conversation_feedback'
                          AND constraint_type = 'FOREIGN KEY'
                          AND constraint_name = 'fk_feedback_response'
                    ) THEN
                        ALTER TABLE conversation_feedback
                        ADD CONSTRAINT fk_feedback_response
                        FOREIGN KEY (conversation_response_id)
                        REFERENCES conversation_responses(conversation_response_id)
                        ON DELETE CASCADE;
                    END IF;
                END $$;
            """)
            print("   FK constraint OK")

            # updated_at trigger
            print("\n-- Adding updated_at trigger ...")
            await cur.execute("""
                DROP TRIGGER IF EXISTS trg_conversation_feedback_updated_at
                ON conversation_feedback;
            """)
            await cur.execute("""
                CREATE TRIGGER trg_conversation_feedback_updated_at
                    BEFORE UPDATE ON conversation_feedback
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column();
            """)
            print("   trigger OK")

            # =============================================================
            # 2. Add credit_exempt columns to conversation_usages
            # =============================================================
            print("\n-- Adding credit_exempt columns to conversation_usages ...")
            await cur.execute("""
                ALTER TABLE conversation_usages
                ADD COLUMN IF NOT EXISTS credit_exempt BOOLEAN NOT NULL DEFAULT FALSE;
            """)
            await cur.execute("""
                ALTER TABLE conversation_usages
                ADD COLUMN IF NOT EXISTS credit_exempt_reason VARCHAR(100);
            """)
            print("   credit_exempt columns OK")

            # =============================================================
            # 3. Drop FK constraints on conversation_usages (audit ledger)
            # =============================================================
            print("\n-- Dropping FK constraints on conversation_usages ...")
            # Both naming conventions: auto-generated (_fkey) and explicit (fk_)
            constraints = [
                "conversation_usages_conversation_response_id_fkey",
                "conversation_usages_conversation_thread_id_fkey",
                "conversation_usages_workspace_id_fkey",
                "fk_conversation_usages_conversation_response_id",
                "fk_conversation_usages_conversation_thread_id",
                "fk_conversation_usages_workspace_id",
            ]
            for constraint in constraints:
                await cur.execute(f"""
                    ALTER TABLE conversation_usages
                    DROP CONSTRAINT IF EXISTS {constraint};
                """)

            # Verify no FK constraints remain
            await cur.execute("""
                SELECT conname FROM pg_constraint
                WHERE conrelid = 'conversation_usages'::regclass AND contype = 'f';
            """)
            remaining = await cur.fetchall()
            if remaining:
                print(f"   WARNING: {len(remaining)} FK constraints still exist: {remaining}")
            else:
                print("   Verified: no FK constraints on conversation_usages")

        await conn.commit()
        print("\nMigration 013 complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
