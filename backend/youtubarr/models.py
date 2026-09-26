from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, utcnow


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SessionToken(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


class Integration(Base):
    __tablename__ = "integrations"
    __table_args__ = (UniqueConstraint("kind", "name", name="uq_integration_kind_name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(30), index=True)
    name: Mapped[str] = mapped_column(String(120))
    base_url: Mapped[str] = mapped_column(String(500))
    api_key_enc: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_status: Mapped[str] = mapped_column(String(40), default="unknown")
    last_error: Mapped[str] = mapped_column(Text, default="")
    last_version: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class RootMapping(Base):
    __tablename__ = "root_mappings"
    __table_args__ = (UniqueConstraint("integration_id", "remote_path", name="uq_mapping_remote"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    integration_id: Mapped[int] = mapped_column(ForeignKey("integrations.id", ondelete="CASCADE"), index=True)
    remote_path: Mapped[str] = mapped_column(String(1200))
    local_path: Mapped[str] = mapped_column(String(1200))
    free_space: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    valid: Mapped[bool] = mapped_column(Boolean, default=False)
    validation_error: Mapped[str] = mapped_column(Text, default="")


class MediaItem(Base):
    __tablename__ = "media_items"
    __table_args__ = (UniqueConstraint("integration_id", "remote_id", "kind", name="uq_media_remote"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    integration_id: Mapped[int] = mapped_column(ForeignKey("integrations.id", ondelete="CASCADE"), index=True)
    remote_id: Mapped[int] = mapped_column(Integer, default=0)
    kind: Mapped[str] = mapped_column(String(30), index=True)
    parent_remote_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    title: Mapped[str] = mapped_column(String(600))
    sort_title: Mapped[str] = mapped_column(String(600), default="")
    year: Mapped[int] = mapped_column(Integer, default=0)
    path: Mapped[str] = mapped_column(String(1600), default="")
    season_number: Mapped[int] = mapped_column(Integer, default=0)
    episode_number: Mapped[int] = mapped_column(Integer, default=0)
    track_number: Mapped[int] = mapped_column(Integer, default=0)
    disc_number: Mapped[int] = mapped_column(Integer, default=1)
    duration: Mapped[int] = mapped_column(Integer, default=0)
    monitored: Mapped[bool] = mapped_column(Boolean, default=True)
    has_file: Mapped[bool] = mapped_column(Boolean, default=False)
    poster_url: Mapped[str] = mapped_column(String(1600), default="")
    overview: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Playlist(Base):
    __tablename__ = "playlists"
    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(1600), unique=True)
    title: Mapped[str] = mapped_column(String(600), default="")
    target_kind: Mapped[str] = mapped_column(String(30), default="series")
    target_media_id: Mapped[int | None] = mapped_column(ForeignKey("media_items.id", ondelete="SET NULL"), index=True)
    season_number: Mapped[int] = mapped_column(Integer, default=1)
    auto_map_order: Mapped[bool] = mapped_column(Boolean, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    entry_count: Mapped[int] = mapped_column(Integer, default=0)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PlaylistEntry(Base):
    __tablename__ = "playlist_entries"
    __table_args__ = (UniqueConstraint("playlist_id", "youtube_id", name="uq_playlist_video"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    playlist_id: Mapped[int] = mapped_column(ForeignKey("playlists.id", ondelete="CASCADE"), index=True)
    youtube_id: Mapped[str] = mapped_column(String(64), index=True)
    url: Mapped[str] = mapped_column(String(1600))
    title: Mapped[str] = mapped_column(String(800), default="")
    position: Mapped[int] = mapped_column(Integer, default=0)
    duration: Mapped[int] = mapped_column(Integer, default=0)
    mapped_media_id: Mapped[int | None] = mapped_column(ForeignKey("media_items.id", ondelete="SET NULL"), index=True)


class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    youtube_url: Mapped[str] = mapped_column(String(1600))
    youtube_id: Mapped[str] = mapped_column(String(64), index=True)
    media_family: Mapped[str] = mapped_column(String(30), default="tv")
    virtual_relpath: Mapped[str] = mapped_column(String(500), unique=True)
    extension: Mapped[str] = mapped_column(String(16), default=".mp4")
    mime_type: Mapped[str] = mapped_column(String(120), default="video/mp4")
    strategy: Mapped[str] = mapped_column(String(30))
    format_id: Mapped[str] = mapped_column(String(120), default="")
    video_format_id: Mapped[str] = mapped_column(String(120), default="")
    audio_format_id: Mapped[str] = mapped_column(String(120), default="")
    reported_size: Mapped[int] = mapped_column(Integer, default=0)
    duration: Mapped[float] = mapped_column(Float, default=0)
    fingerprint: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_access_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Acquisition(Base):
    __tablename__ = "acquisitions"
    id: Mapped[int] = mapped_column(primary_key=True)
    media_item_id: Mapped[int] = mapped_column(ForeignKey("media_items.id", ondelete="CASCADE"), index=True)
    playlist_entry_id: Mapped[int | None] = mapped_column(ForeignKey("playlist_entries.id", ondelete="SET NULL"), index=True)
    youtube_url: Mapped[str] = mapped_column(String(1600))
    title: Mapped[str] = mapped_column(String(800), default="")
    mode: Mapped[str] = mapped_column(String(40), default="virtual_symlink")
    status: Mapped[str] = mapped_column(String(40), default="queued", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    output_path: Mapped[str] = mapped_column(String(1600), default="")
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"), default="")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
