from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(bind=None) -> None:
    target_engine = bind or engine
    Base.metadata.create_all(bind=target_engine)
    if target_engine.dialect.name == "sqlite":
        with target_engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(image_analyses)")).fetchall()
            if result:
                cols = {row[1] for row in result}
                if "image_width" not in cols:
                    conn.execute(text("ALTER TABLE image_analyses ADD COLUMN image_width INTEGER"))
                if "image_height" not in cols:
                    conn.execute(text("ALTER TABLE image_analyses ADD COLUMN image_height INTEGER"))
                conn.commit()

