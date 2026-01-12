from sqlalchemy import String, Integer, SmallInteger, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from lib.core.database import Base

class Stage(Base):
    __tablename__ = "stages"

    stage_id: Mapped[int] = mapped_column(primary_key=True)
    stage_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    
    # Zone과의 관계 (FK)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.zone_id", ondelete="CASCADE"), nullable=False)
    
    display_code: Mapped[str] = mapped_column(String, nullable=False) # 예: "1-7", "H8-4"
    name_ko: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    ap_cost: Mapped[int] = mapped_column(SmallInteger, default=0)
    danger_level: Mapped[str | None] = mapped_column(String) # 예: "Elite 2 Lv.40"

    # --- Relationships ---
    
    # 1. Parent (Zone)
    # Zone 정보를 참조합니다. 순환 참조 방지를 위해 문자열 경로 사용.
    zone = relationship("lib.models.common.Zone", back_populates="stages")