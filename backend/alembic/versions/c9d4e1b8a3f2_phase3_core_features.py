"""phase3_core_features

Revision ID: c9d4e1b8a3f2
Revises: b4f8c2a91d3e
Create Date: 2026-04-11 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "c9d4e1b8a3f2"
down_revision = "b4f8c2a91d3e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    user_role = postgresql.ENUM("student", "club_admin", "organizer", name="user_role", create_type=True)
    user_role.create(op.get_bind(), checkfirst=True)

    event_rsvp_status = postgresql.ENUM("going", "waitlist", name="event_rsvp_status", create_type=True)
    event_rsvp_status.create(op.get_bind(), checkfirst=True)

    notification_type = postgresql.ENUM(
        "reminder", "invite", "announce", "karma", "rsvp", name="notification_type", create_type=True
    )
    notification_type.create(op.get_bind(), checkfirst=True)

    op.add_column("users", sa.Column("branch", sa.String(length=80), nullable=True))
    op.add_column("users", sa.Column("year", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("bio", sa.String(length=240), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "role",
            postgresql.ENUM("student", "club_admin", "organizer", name="user_role", create_type=False),
            nullable=False,
            server_default="student",
        ),
    )
    op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"))

    op.create_table(
        "clubs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=140), nullable=False, unique=True),
        sa.Column("category", sa.String(length=60), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("banner_url", sa.String(length=500), nullable=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("member_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("event_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("founded_year", sa.Integer(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("location", sa.String(length=180), nullable=False),
        sa.Column("organizer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("club_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clubs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("attendee_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("allow_waitlist", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("banner_url", sa.String(length=500), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("schedule", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("speakers", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("is_cancelled", sa.Boolean(), nullable=False, server_default="false"),
    )

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("recipient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "type",
            postgresql.ENUM("reminder", "invite", "announce", "karma", "rsvp", name="notification_type", create_type=False),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("related_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("related_type", sa.String(length=60), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "polls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("votes", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("creator_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("total_votes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "club_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("club_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_unique_constraint("uq_club_membership_user_club", "club_memberships", ["club_id", "user_id"])

    op.create_table(
        "event_rsvps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("going", "waitlist", name="event_rsvp_status", create_type=False),
            nullable=False,
            server_default="going",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_unique_constraint("uq_event_rsvp_user_event", "event_rsvps", ["event_id", "user_id"])

    op.create_table(
        "poll_votes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("poll_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("polls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("option_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_unique_constraint("uq_poll_vote_user_poll", "poll_votes", ["poll_id", "user_id"])


def downgrade() -> None:
    op.drop_constraint("uq_poll_vote_user_poll", "poll_votes", type_="unique")
    op.drop_table("poll_votes")

    op.drop_constraint("uq_event_rsvp_user_event", "event_rsvps", type_="unique")
    op.drop_table("event_rsvps")

    op.drop_constraint("uq_club_membership_user_club", "club_memberships", type_="unique")
    op.drop_table("club_memberships")

    op.drop_table("polls")
    op.drop_table("notifications")
    op.drop_table("events")
    op.drop_table("clubs")

    op.drop_column("users", "is_active")
    op.drop_column("users", "role")
    op.drop_column("users", "bio")
    op.drop_column("users", "year")
    op.drop_column("users", "branch")

    op.execute("DROP TYPE IF EXISTS notification_type")
    op.execute("DROP TYPE IF EXISTS event_rsvp_status")
    op.execute("DROP TYPE IF EXISTS user_role")
