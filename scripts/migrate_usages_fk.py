#!/usr/bin/env python3
"""
Migration: Drop FK constraints on conversation_usages.

Converts conversation_usages to an append-only audit ledger by removing
ON DELETE CASCADE foreign keys. Columns stay NOT NULL with IDs preserved
forever as plain data, ensuring usage records survive parent deletion
(responses, threads, workspaces).

Idempotent — safe to run multiple times.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from src.server.database.conversation import get_db_connection_string


async def migrate():
    import psycopg

    db_url = get_db_connection_string()
    print("Connecting to database...")

    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        async with conn.cursor() as cur:
            # Drop all 3 FK constraints (idempotent)
            # Both naming conventions: auto-generated (_fkey suffix) and explicit (fk_ prefix)
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
                print(f"  Dropped constraint: {constraint}")

            # Verify no FK constraints remain
            await cur.execute("""
                SELECT conname FROM pg_constraint
                WHERE conrelid = 'conversation_usages'::regclass AND contype = 'f';
            """)
            remaining = await cur.fetchall()
            if remaining:
                print(f"  WARNING: {len(remaining)} FK constraints still exist: {remaining}")
            else:
                print("  Verified: no FK constraints on conversation_usages")

        await conn.commit()
        print("Migration complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
