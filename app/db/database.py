from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, echo=settings.DEBUG)

# Creador de Sesiones
# autoflush en False da el control manual de las transacciones
SessionLocal = sessionmaker(autoflush=False, bind=engine)


# Clase Base para los Modelos ORM
# Todas las entidades (Client, SaleOrder, etc.) heredarán de esta clase
class Base(DeclarativeBase):
    pass


# Inyección de dependencias
# Genera una sesión de BD única por cada petición web que reciba FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
