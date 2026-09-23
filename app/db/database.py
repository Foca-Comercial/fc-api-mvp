from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, echo=True)

# Creador de Sesiones
# autocommit y autoflush en False dan el control manual de las transacciones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Clase Base para los Modelos ORM
# Todas las entidades (Client, SaleOrder, etc.) heredarán de esta clase
Base = declarative_base()


# Inyección de Dependencias
# Función que generará una sesión de BD única por cada petición web que reciba FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
