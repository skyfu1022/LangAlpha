"""Add factor_library table for alpha factor persistence.

Revision ID: 009
Revises: 008
Create Date: 2026-04-21
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE factor_library (
            id SERIAL PRIMARY KEY,
            workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            formula TEXT NOT NULL,
            category TEXT,
            ic_mean DOUBLE PRECISION NOT NULL,
            icir DOUBLE PRECISION,
            max_corr DOUBLE PRECISION,
            evaluation_config JSONB NOT NULL DEFAULT '{}',
            parameters JSONB NOT NULL DEFAULT '{}',
            admitted_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX idx_factor_library_workspace ON factor_library(workspace_id);
        CREATE INDEX idx_factor_library_workspace_category ON factor_library(workspace_id, category);
        CREATE UNIQUE INDEX idx_factor_library_workspace_name ON factor_library(workspace_id, name);
        CREATE UNIQUE INDEX idx_factor_library_workspace_formula ON factor_library(workspace_id, formula);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS factor_library CASCADE")
