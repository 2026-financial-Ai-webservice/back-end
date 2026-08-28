"""merge portfolio_request into main history

Revision ID: 3f828954e17b
Revises: 9aacba99bed0, b7c9a751055e
Create Date: 2026-08-28 22:35:35.734035

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = '3f828954e17b'
down_revision: str | Sequence[str] | None = ('9aacba99bed0', 'b7c9a751055e')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
