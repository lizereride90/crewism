from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

try:
    from sqlalchemy import JSON as SA_JSON
except Exception:  # pragma: no cover
    SA_JSON = SQLITE_JSON


class Base(DeclarativeBase):
    pass


def utcnow():
    return datetime.utcnow()


class Player(Base):
    __tablename__ = "players"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    name: Mapped[str] = mapped_column(String(64), default="")
    level: Mapped[int] = mapped_column(Integer, default=1)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    money: Mapped[int] = mapped_column(Integer, default=500)
    reputation: Mapped[int] = mapped_column(Integer, default=0)
    energy: Mapped[int] = mapped_column(Integer, default=100)
    energy_updated: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    p_str: Mapped[int] = mapped_column(Integer, default=10)
    p_spd: Mapped[int] = mapped_column(Integer, default=10)
    p_end: Mapped[int] = mapped_column(Integer, default=10)
    p_tech: Mapped[int] = mapped_column(Integer, default=10)
    battle_iq: Mapped[int] = mapped_column(Integer, default=10)
    potential: Mapped[str] = mapped_column(String(16), default="C")
    talent: Mapped[int] = mapped_column(Integer, default=10)
    generation: Mapped[int] = mapped_column(Integer, default=2)
    bloodline_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    crew_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    region: Mapped[str] = mapped_column(String(64), default="jhigh")
    bounty: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    last_daily: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (UniqueConstraint("guild_id", "user_id", name="uq_player_guild_user"),)


class CharacterDefinition(Base):
    __tablename__ = "char_defs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    series: Mapped[str] = mapped_column(String(32), default="lookism")
    rarity: Mapped[str] = mapped_column(String(16), default="Common")
    style: Mapped[str] = mapped_column(String(32), default="Street Fighting")
    char_class: Mapped[str] = mapped_column(String(32), default="Brawler")
    generation: Mapped[int] = mapped_column(Integer, default=2)
    faction: Mapped[str] = mapped_column(String(64), default="Streets")
    role: Mapped[str] = mapped_column(String(16), default="recruitable")
    source: Mapped[str] = mapped_column(String(16), default="canon")
    recruitable: Mapped[int] = mapped_column(Integer, default=1)
    base_str: Mapped[int] = mapped_column(Integer, default=10)
    base_spd: Mapped[int] = mapped_column(Integer, default=10)
    base_end: Mapped[int] = mapped_column(Integer, default=10)
    base_tech: Mapped[int] = mapped_column(Integer, default=10)
    base_iq: Mapped[int] = mapped_column(Integer, default=10)
    bloodline: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ability_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    min_level: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[str] = mapped_column(Text, default="")


class CharacterInstance(Base):
    __tablename__ = "char_instances"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, index=True)
    def_id: Mapped[str] = mapped_column(String(64), index=True)
    level: Mapped[int] = mapped_column(Integer, default=1)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    c_str: Mapped[int] = mapped_column(Integer, default=10)
    c_spd: Mapped[int] = mapped_column(Integer, default=10)
    c_end: Mapped[int] = mapped_column(Integer, default=10)
    c_tech: Mapped[int] = mapped_column(Integer, default=10)
    loyalty: Mapped[int] = mapped_column(Integer, default=50)
    fragments: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[int] = mapped_column(Integer, default=0)


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, index=True)
    name: Mapped[str] = mapped_column(String(48), default="Main")
    is_active: Mapped[int] = mapped_column(Integer, default=1)

    __table_args__ = (UniqueConstraint("guild_id", "owner_id", "name", name="uq_team"),)


class TeamMember(Base):
    __tablename__ = "team_members"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    instance_id: Mapped[int] = mapped_column(Integer, ForeignKey("char_instances.id", ondelete="CASCADE"))
    slot: Mapped[int] = mapped_column(Integer, default=0)


class ItemDefinition(Base):
    __tablename__ = "item_defs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(24), default="consumable")
    rarity: Mapped[str] = mapped_column(String(16), default="Common")
    price: Mapped[int] = mapped_column(Integer, default=100)
    description: Mapped[str] = mapped_column(Text, default="")
    effects: Mapped[dict] = mapped_column(SA_JSON, default=dict)
    source: Mapped[str] = mapped_column(String(16), default="original")


class InventoryItem(Base):
    __tablename__ = "inventory"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, index=True)
    item_id: Mapped[str] = mapped_column(String(64), index=True)
    qty: Mapped[int] = mapped_column(Integer, default=1)
    equipped_to: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (UniqueConstraint("guild_id", "owner_id", "item_id", "equipped_to", name="uq_inv"),)


class AbilityDefinition(Base):
    __tablename__ = "abilities"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(24), default="passive")
    trigger: Mapped[str] = mapped_column(String(32), default="on_round")
    description: Mapped[str] = mapped_column(Text, default="")
    effects: Mapped[dict] = mapped_column(SA_JSON, default=dict)
    source: Mapped[str] = mapped_column(String(16), default="canon")


class Bloodline(Base):
    __tablename__ = "bloodlines"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(16), default="canon")


class BloodlineStage(Base):
    __tablename__ = "bloodline_stages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bloodline_id: Mapped[str] = mapped_column(String(64), index=True)
    stage: Mapped[int] = mapped_column(Integer)
    level_req: Mapped[int] = mapped_column(Integer, default=1)
    name: Mapped[str] = mapped_column(String(64), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    effects: Mapped[dict] = mapped_column(SA_JSON, default=dict)


class BloodlineProgress(Base):
    __tablename__ = "bloodline_progress"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    bloodline_id: Mapped[str] = mapped_column(String(64))
    stage: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (UniqueConstraint("guild_id", "user_id", "bloodline_id", name="uq_blood_prog"),)


class MasteryProgress(Base):
    __tablename__ = "masteries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    mastery: Mapped[str] = mapped_column(String(24))
    stage: Mapped[str] = mapped_column(String(24), default="Normal")
    progress: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (UniqueConstraint("guild_id", "user_id", "mastery", name="uq_mastery"),)


class Trainer(Base):
    __tablename__ = "trainers"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    specialty: Mapped[str] = mapped_column(String(24), default="strength")
    price: Mapped[int] = mapped_column(Integer, default=500)
    duration_min: Mapped[int] = mapped_column(Integer, default=60)
    req_level: Mapped[int] = mapped_column(Integer, default=1)
    region: Mapped[str] = mapped_column(String(64), default="jhigh")
    rarity: Mapped[str] = mapped_column(String(16), default="Common")
    source: Mapped[str] = mapped_column(String(16), default="original")


class TrainingSession(Base):
    __tablename__ = "training"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    instance_id: Mapped[int] = mapped_column(Integer, index=True)
    trainer_id: Mapped[str] = mapped_column(String(64))
    ends_at: Mapped[datetime] = mapped_column(DateTime)
    claimed: Mapped[int] = mapped_column(Integer, default=0)


class Crew(Base):
    __tablename__ = "crews"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    name: Mapped[str] = mapped_column(String(48))
    tag: Mapped[str] = mapped_column(String(8), default="")
    leader_id: Mapped[int] = mapped_column(BigInteger)
    treasury: Mapped[int] = mapped_column(Integer, default=0)
    reputation: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (UniqueConstraint("guild_id", "name", name="uq_crew_name"),)


class CrewMember(Base):
    __tablename__ = "crew_members"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crew_id: Mapped[int] = mapped_column(Integer, ForeignKey("crews.id", ondelete="CASCADE"), index=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)

    __table_args__ = (UniqueConstraint("crew_id", "user_id", name="uq_crew_member"),)


class Territory(Base):
    __tablename__ = "territories"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    rec_level: Mapped[int] = mapped_column(Integer, default=1)
    income: Mapped[int] = mapped_column(Integer, default=200)
    boss_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")


class TerritoryOwnership(Base):
    __tablename__ = "territory_ownership"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    territory_id: Mapped[str] = mapped_column(String(64), index=True)
    owner_type: Mapped[str] = mapped_column(String(16), default="npc")
    crew_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    influence: Mapped[int] = mapped_column(Integer, default=0)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint("guild_id", "territory_id", name="uq_terr"),)


class Battle(Base):
    __tablename__ = "battles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    battle_type: Mapped[str] = mapped_column(String(24), default="pve")
    p1_id: Mapped[int] = mapped_column(BigInteger)
    p2_id: Mapped[int] = mapped_column(BigInteger, default=0)
    state: Mapped[str] = mapped_column(String(16), default="active")
    winner_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    wager: Mapped[int] = mapped_column(Integer, default=0)
    log: Mapped[dict] = mapped_column(SA_JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Quest(Base):
    __tablename__ = "quests"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(24), default="daily")
    description: Mapped[str] = mapped_column(Text, default="")
    req: Mapped[dict] = mapped_column(SA_JSON, default=dict)
    rewards: Mapped[dict] = mapped_column(SA_JSON, default=dict)


class QuestProgress(Base):
    __tablename__ = "quest_progress"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    quest_id: Mapped[str] = mapped_column(String(64), index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[int] = mapped_column(Integer, default=0)
    claimed: Mapped[int] = mapped_column(Integer, default=0)
    date_key: Mapped[str] = mapped_column(String(16), default="")

    __table_args__ = (UniqueConstraint("guild_id", "user_id", "quest_id", "date_key", name="uq_quest"),)


class Boss(Base):
    __tablename__ = "bosses"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    level: Mapped[int] = mapped_column(Integer, default=10)
    stats: Mapped[dict] = mapped_column(SA_JSON, default=dict)
    abilities: Mapped[list] = mapped_column(SA_JSON, default=list)
    phases: Mapped[list] = mapped_column(SA_JSON, default=list)
    rewards: Mapped[dict] = mapped_column(SA_JSON, default=dict)
    region: Mapped[str] = mapped_column(String(64), default="jhigh")
    cooldown_h: Mapped[int] = mapped_column(Integer, default=24)
    generation: Mapped[int] = mapped_column(Integer, default=1)


class BossAttempt(Base):
    __tablename__ = "boss_attempts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    boss_id: Mapped[str] = mapped_column(String(64), index=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    won: Mapped[int] = mapped_column(Integer, default=0)


class Event(Base):
    __tablename__ = "events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    starts_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    ends_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    config: Mapped[dict] = mapped_column(SA_JSON, default=dict)
    active: Mapped[int] = mapped_column(Integer, default=0)


class EconomyTransaction(Base):
    __tablename__ = "economy_ledger"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    amount: Mapped[int] = mapped_column(Integer)
    before: Mapped[int] = mapped_column(Integer)
    after: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(64))
    ref: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (Index("ix_ledger_guild_user", "guild_id", "user_id"),)


class Cooldown(Base):
    __tablename__ = "cooldowns"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    scope: Mapped[str] = mapped_column(String(48), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)

    __table_args__ = (UniqueConstraint("guild_id", "user_id", "scope", name="uq_cd"),)


class ServerConfig(Base):
    __tablename__ = "server_config"
    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    encounter_enabled: Mapped[int] = mapped_column(Integer, default=1)
    pvp_enabled: Mapped[int] = mapped_column(Integer, default=1)
    gambling_enabled: Mapped[int] = mapped_column(Integer, default=1)
    spawn_channel: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    config: Mapped[dict] = mapped_column(SA_JSON, default=dict)
