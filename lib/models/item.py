from sqlalchemy import String, Integer, SmallInteger, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from lib.core.database import Base
from datetime import datetime

class Item(Base):
    __tablename__ = "items"

    item_id: Mapped[int] = mapped_column(primary_key=True)
    item_code: Mapped[str] = mapped_column(String(64), unique=True)
    name_ko: Mapped[str] = mapped_column(String(64))
    rarity: Mapped[int] = mapped_column(SmallInteger, default=0)
    icon_id: Mapped[str | None] = mapped_column(String(128))
    item_type: Mapped[str | None] = mapped_column(String(32))
    classify_type: Mapped[str | None] = mapped_column(String(32))
    usage_text: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    obtain_approach: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())