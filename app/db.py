from datetime import date, datetime, timezone

from sqlalchemy import (Column, Date, DateTime, Float, ForeignKey, Integer, String, Table, Text,
                        UniqueConstraint, create_engine, event)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


partner_flags = Table(
    "partner_flags",
    Base.metadata,
    Column("partner_id", ForeignKey("partners.id", ondelete="CASCADE"), primary_key=True),
    Column("flag_id", ForeignKey("flags.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    partners: Mapped[list["Partner"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    flags: Mapped[list["Flag"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class Flag(Base):
    __tablename__ = "flags"
    __table_args__ = (UniqueConstraint("owner_id", "name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(40))
    color: Mapped[str] = mapped_column(String(16), default="spicy")
    owner: Mapped[User] = relationship(back_populates="flags")


class Partner(Base):
    __tablename__ = "partners"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    nickname: Mapped[str | None] = mapped_column(String(80), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    met_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    times: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[str] = mapped_column(Text, default="")
    photo: Mapped[str | None] = mapped_column(String(64), nullable=True)
    overall: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    owner: Mapped[User] = relationship(back_populates="partners")
    scores: Mapped[list["Score"]] = relationship(back_populates="partner", cascade="all, delete-orphan")
    flags: Mapped[list[Flag]] = relationship(secondary=partner_flags, order_by="Flag.name")

    def score_map(self) -> dict[str, int]:
        return {s.criterion: s.value for s in self.scores}


class Score(Base):
    __tablename__ = "scores"
    __table_args__ = (UniqueConstraint("partner_id", "criterion"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id", ondelete="CASCADE"), index=True)
    criterion: Mapped[str] = mapped_column(String(32))
    value: Mapped[int] = mapped_column(Integer)
    partner: Mapped[Partner] = relationship(back_populates="scores")


def make_engine(url: str):
    kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
    engine = create_engine(url, **kwargs)
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()
    return engine


def make_sessionmaker(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
