import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import JSON, DateTime, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from packages.core.models import Settings


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    parent_id: Mapped[str | None] = mapped_column(String(64), index=True)
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class Store:
    def __init__(self, url: str | None = None):
        self.data_dir = Path(os.getenv("SHADOWLAB_DATA_DIR", ".shadowlab")).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        url = url or os.getenv("SHADOWLAB_DATABASE_URL", f"sqlite:///{self.data_dir / 'shadowlab.db'}")
        self.engine = create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})
        self.session = sessionmaker(self.engine, expire_on_commit=False)

    def initialize(self):
        from alembic import command
        from alembic.config import Config
        config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        config.set_main_option("script_location", str(Path(__file__).with_name("migrations")))
        with self.engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")

    def put(self, kind: str, data: dict, id: str | None = None, parent_id: str | None = None):
        id = id or str(uuid4())
        with self.session.begin() as session:
            doc = session.get(Document, id)
            if doc and doc.kind != kind:
                raise ValueError("Document kind mismatch")
            if doc:
                doc.data = {**doc.data, **data}
            else:
                doc = Document(id=id, kind=kind, parent_id=parent_id, data=data)
                session.add(doc)
        return self.get(kind, id)

    def get(self, kind: str, id: str):
        with self.session() as session:
            doc = session.get(Document, id)
            if not doc or doc.kind != kind:
                return None
            return {**doc.data, "id": doc.id, "created_at": doc.created_at.isoformat(), "parent_id": doc.parent_id}

    def list(self, kind: str, parent_id: str | None = None):
        with self.session() as session:
            stmt = select(Document).where(Document.kind == kind).order_by(Document.created_at)
            if parent_id is not None:
                stmt = stmt.where(Document.parent_id == parent_id)
            return [{**d.data, "id": d.id, "created_at": d.created_at.isoformat(), "parent_id": d.parent_id}
                    for d in session.scalars(stmt)]

    def settings(self):
        doc = self.get("settings", "settings")
        return Settings.model_validate(doc or {})

    def save_settings(self, settings: Settings):
        self.put("settings", settings.model_dump(mode="json"), id="settings")
        return settings

    def event(self, scan_id: str, stage: str, message: str, **details):
        return self.put("event", {"stage": stage, "message": message, **details}, parent_id=scan_id)
