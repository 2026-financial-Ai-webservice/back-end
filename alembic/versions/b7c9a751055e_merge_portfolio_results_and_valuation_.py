"""merge portfolio_results and valuation_result branches

Revision ID: b7c9a751055e
Revises: bf09e2b084e8, ef4a6e6a76b8
Create Date: 2026-08-28 22:02:52.622998

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = 'b7c9a751055e'
down_revision: str | Sequence[str] | None = ('bf09e2b084e8', 'ef4a6e6a76b8')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
