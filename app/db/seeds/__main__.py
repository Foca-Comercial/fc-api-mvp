import logging

from app.db.database import SessionLocal
from app.db.seeds.engine import seed_entity
from app.db.seeds.registry import SEEDS

logging.basicConfig(level=logging.INFO, format="%(message)s")


def run() -> None:
    with SessionLocal() as db:
        try:
            for spec in SEEDS:
                seed_entity(db, spec)
            db.commit()  # un solo commit: todo o nada
        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    run()
