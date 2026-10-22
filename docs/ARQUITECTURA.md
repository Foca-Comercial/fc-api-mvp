# FC API MVP — Documentación Técnica

API REST para gestión comercial de **Foca Comercial** (venta y distribución de hielo/agua),
construida con **FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL**. La arquitectura está
inspirada en **Onion Architecture / N-Capas** (experiencia previa del equipo en .NET/C#),
adaptada a las convenciones idiomáticas de Python y FastAPI.

> Los comandos para instalar, migrar, cargar seeds y levantar la API están en el
> [`README.md`](../README.md) de la raíz.

---

## 1. Stack tecnológico

| Pieza | Tecnología |
|---|---|
| Framework web | FastAPI |
| ORM | SQLAlchemy 2.0 (Declarative Mapping moderno: `Mapped` / `mapped_column`) |
| Migraciones | Alembic |
| Base de datos | PostgreSQL |
| Validación / DTOs | Pydantic v2 |
| Autenticación | JWT (PyJWT) — access + refresh tokens con rotación |
| Hasheo de contraseñas | `pwdlib[argon2]` |
| Generación de PDF | ReportLab |
| Config / variables de entorno | `pydantic-settings` (lee `.env` desde la raíz del proyecto) |
| Seeds | Archivos `.jsonc` leídos con `json5` |
| Archivado mensual | Google Sheets vía `gspread` + `google-auth` (cuenta de servicio) |
| Exportación a Siigo | Excel `.xlsx` generado con `openpyxl` |

---

## 2. Estructura del proyecto

```
app/
├── api/
│   ├── dependencies.py          # CurrentUser, get_current_user, require_roles
│   ├── exception_handlers.py    # Traduce excepciones de negocio/BD a respuestas HTTP
│   └── routers/
│       ├── auth/
│       │   ├── auth_router.py   # Login, refresh, logout, logout-all
│       │   └── secured_router.py # APIRouter extendido: rol ADMINISTRADOR por defecto
│       ├── securityModule/      # Person, User, Role, UserRole
│       ├── coreModule/          # Client, Product, Order, OrderDetail, etc.
│       └── parametersModule/    # Zone, Neighborhood, Route, Vehicle
├── core/
│   ├── config.py                 # Settings (pydantic-settings), lee .env
│   ├── security.py               # JWT: create/decode access token, refresh token helpers
│   ├── timezone.py               # BOGOTA_TZ, today_bogota() y rangos de día/mes en Bogotá
│   └── strategies/
│       └── deletion_strategy.py  # SoftDeleteStrategy / HardDeleteStrategy
├── db/
│   ├── database.py               # engine, SessionLocal, Base, get_db() (con rollback)
│   ├── custom_types.py           # IntEnumType (TypeDecorator para enums numéricos)
│   └── seeds/                    # Datos iniciales (ver sección 6)
│       ├── __main__.py           # python -m app.db.seeds
│       ├── registry.py           # SEEDS: orden de carga (= orden de dependencias)
│       ├── engine.py             # SeedSpec, seed_entity (valida con el schema Create)
│       ├── loader.py             # Lee los .jsonc con json5
│       └── data/<módulo>/*.jsonc
├── models/                       # Entidades SQLAlchemy, agrupadas por módulo de dominio
│   ├── securityModule/           # Person, User, Role, UserRole, UserSession
│   ├── coreModule/               # Client, Product, SpecialCustomerPrice, Order,
│   │                              # OrderDetail, ShiftClosure, UserVehicle, ClientRoute,
│   │                              # DailyOrderCounter, MonthlyArchive, ArchiveSpreadsheet
│   └── parametersModule/         # Zone, Neighborhood, Route, Vehicle
├── schemas/                      # DTOs Pydantic, mismo agrupamiento que models/
│   ├── auth/                     # Token, RefreshRequest, SessionCreate/Update
│   ├── securityModule/
│   ├── coreModule/
│   └── parametersModule/
├── repositories/                  # Acceso a datos (capa Data)
│   ├── base_repository.py        # CRUD genérico + helpers reutilizables
│   ├── time_filters.py           # on_bogota_day / between_bogota_dates / on_db_today
│   └── <mismos módulos que models/>
├── services/                      # Lógica de negocio (capa Business)
│   ├── base_service.py           # CRUD genérico + hooks de validación declarativa
│   ├── validation.py             # UniqueRule, ReferenceRule, UniqueTogether
│   ├── auth/                     # AuthService (login/refresh/logout)
│   ├── pdf/                      # PdfService (comprobantes de despacho) + assets/logo
│   └── <mismos módulos que models/>   # coreModule incluye además:
│       # archive_export.py (tabla del mes para Sheets), sheets_writer.py (SheetsWriter /
│       # GoogleSheetsWriter) y closure_export.py (Excel del cierre para Siigo)
└── utils/
    ├── schema_types.py               # UpperText / LowerText (strip + cambio de caja)
    ├── exceptions/
    │   └── business_exceptions.py    # Jerarquía BusinessError
    ├── enums/                        # Enums centralizados (los modelos solo los importan)
    │   ├── archive_status.py         # ArchiveStatus (EXPORTED/PURGED)
    │   ├── day_week.py               # DayWeek (1 = lunes ... 7 = domingo)
    │   ├── delete_type.py            # DeletionType (SOFT/HARD)
    │   └── order_state.py            # OrderState
    └── helpers/
        ├── password_helper.py        # hash_password / verify_password (pwdlib/argon2)
        ├── schema_helper.py          # partial_model (genera schemas Update automáticamente)
        └── string_helper.py          # comparison_key (normalización para unicidad)
docs/
└── ARQUITECTURA.md                   # Este documento
tests/                                # pytest (ver sección 11)
├── conftest.py                       # BD de pruebas, migraciones, datos base, overrides
├── helpers.py                        # API, item(), FakeSheetsWriter
└── test_*.py
requirements.txt                      # Dependencias de la API (versiones fijadas)
requirements-dev.txt                  # + pytest, httpx
pytest.ini
```

**Convención de organización:** cada capa (`models`, `schemas`, `repositories`, `services`,
`api/routers`) se agrupa en los mismos tres submódulos de dominio
(`securityModule`, `coreModule`, `parametersModule`). Lo que **no** es una entidad del
dominio del negocio (autenticación, generación de PDF, helpers transversales) vive fuera de
esa agrupación, en su propia carpeta temática (`auth/`, `pdf/`, `core/`, `utils/`).

### Variables de entorno (`.env`)

El `.env` vive en la **raíz del proyecto**, no dentro de `app/`, porque `pydantic-settings`
resuelve rutas relativas contra el directorio de ejecución (`cwd`), coincidiendo con cómo se
invoca Alembic y `uvicorn`. **No se versiona** (está en `.gitignore`); cada entorno crea el
suyo con estas variables:

| Variable | Obligatoria | Default |
|---|---|---|
| `DATABASE_URL` | Sí | — (`postgresql+psycopg2://usuario:clave@host:puerto/bd`) |
| `SECRET_KEY` | Sí | — (generar con `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `DEBUG` | No | `False` (en `True`, SQLAlchemy imprime cada SQL) |
| `ALGORITHM` | No | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `30` |
| `GOOGLE_CREDENTIALS_FILE` | Solo para exportar a Sheets | — (ruta al JSON de la cuenta de servicio de Google) |
| `HISTORY_RETENTION_MONTHS` | No | `2` (meses que se conservan en la BD, incluido el vigente) |
| `DEFAULT_SELLER_CODE` | No | `01` (`user_vehicle.code` que recibe en el cierre los pedidos sin conductor) |

---

## 3. Arquitectura por capas

```
Router (FastAPI)  →  Service (negocio)  →  Repository (datos)  →  Modelo ORM (SQLAlchemy)
                            ↓
                     Schema Pydantic (validación de entrada/salida)
```

- **Router**: delgado — solo recibe el request, llama al service correspondiente, retorna
  el resultado. No contiene lógica de negocio.
- **Service**: orquesta la operación, aplica reglas de negocio y validaciones, decide qué
  repositorios usar. Es donde vive la complejidad real.
- **Repository**: abstrae el acceso a la base de datos vía SQLAlchemy. No contiene reglas
  de negocio — solo consultas y operaciones CRUD.
- **Modelo ORM**: mapea una tabla física. Declarative Mapping moderno de SQLAlchemy 2.0
  fusiona en una sola clase lo que en EF Core estaría separado entre la entidad POCO y su
  `IEntityTypeConfiguration<T>` — no existe un patrón nativo de configuración separada en
  SQLAlchemy, es el diseño idiomático de la librería.
- **Schema Pydantic**: el modelo ORM y el schema son **independientes**, sin herencia ni
  sincronización automática entre ellos — resuelven responsabilidades distintas (estructura
  de tabla vs. contrato de API), aunque a veces compartan validaciones similares
  (`max_length`, etc.) por coincidencia, no por acoplamiento.

### Genéricos reutilizables: `BaseRepository` / `BaseService`

Ambos son clases genéricas (`Generic[ModelType, CreateSchemaType, UpdateSchemaType]`) que
proveen las operaciones CRUD estándar (`get_all`, `get`, `create`, `update`, `remove`) más
utilidades de soporte (`get_by_field`, `exists`, `exists_normalized`, y `add`/`delete` con
`flush()` para operaciones compuestas). Cada entidad define su propio repositorio y servicio
heredando de estas bases:

```python
# repositories/securityModule/user_repository.py
class RepositoryUser(BaseRepository[User, UserCreate, UserUpdate]):
    pass


user_repository = RepositoryUser(User)


# services/securityModule/user_service.py
class UserService(BaseService[User, UserCreate, UserUpdate]):
    unique_rules = (UniqueRule("username", "Nombre de usuario", normalized=False),)

    def __init__(self):
        super().__init__(repository=user_repository, entity_name="Usuario")


user_service = UserService()
```

**`BaseRepository.update`** recibe un schema (`model_dump(exclude_unset=True)`, solo lo
enviado) o un `dict`, y recorre **esos campos** — no `db_obj.__dict__`, que tras un commit
previo en la misma sesión llega sin columnas porque el objeto está expirado. Cada campo se
valida contra las columnas del mapper: uno que no sea columna lanza `ValueError` (error de
programación: schema y modelo desalineados) en vez de ignorarse en silencio.

Cuando una entidad necesita lógica más elaborada que el CRUD genérico (como `Order`), su
servicio sigue heredando `BaseService` para conservar `get`/`get_all`/`update`, pero agrega
métodos propios en vez de forzar la operación dentro de `create()`/`update()` genéricos
(ver sección 10).

**`get_all` y registros inactivos (decisión explícita):** solo `Client`, `Product` y
`Route` sobrescriben `get_all` para excluir los registros con `active = False`, porque son
los que se listan en el flujo operativo (formulario de pedido). Las cards de la vista de
Rutas usan su propia consulta (`/routes/cards`), que sí incluye las inactivas. El resto de entidades devuelve
también los inactivos **a propósito** — sus listados son de administración, donde ver lo
desactivado es útil.

### Validaciones declarativas (`services/validation.py`)

En vez de escribir validaciones imperativas repetidas en cada servicio, se declaran como
reglas reutilizables a nivel de clase:

```python
class UserRoleService(BaseService[UserRole, UserRoleCreate, UserRoleUpdate]):
    references = (
        ReferenceRule("id_user", "Usuario", user_repository),
        ReferenceRule("id_role", "Rol", role_repository),
    )
    unique_together = (UniqueTogether("Usuario y rol", ("id_user", "id_role")),)
```

- **`UniqueRule`**: un campo no puede repetirse (opcionalmente comparando normalizado:
  mayúsculas/espacios ignorados). Cuenta también los registros inactivos.
- **`ReferenceRule`**: valida que una FK apunte a una entidad existente **y activa**.
  En `on_create` ignora el campo si es `None` (FK opcional no enviada); en `on_update` solo
  revalida si el valor cambió respecto al existente (así un registro cuyo padre se
  desactivó después puede seguir editándose sin tocar esa FK).
- **`UniqueTogether`**: una combinación de campos no puede repetirse (tablas de asociación).

`BaseService._validate_before_create` / `_validate_before_update` recorren automáticamente
las reglas declaradas. Instancias independientes, fuera de este mecanismo
(`ensure_unique`, `ensure_reference`, `ensure_unique_together`), están disponibles como
funciones sueltas para validaciones puntuales dentro de un servicio específico.

### Patrón Strategy para eliminación (soft / hard delete)

```python
class DeletionType(str, enum.Enum):
    SOFT = "SOFT"
    HARD = "HARD"
```

`BaseService.remove()` recibe un `strategy_type: DeletionType = DeletionType.SOFT` y delega
en una de dos estrategias (`app/core/strategies/deletion_strategy.py`):

- **`SoftDeleteStrategy`**: cambia `active = False` (requiere que la entidad tenga ese
  atributo; si no, lanza `BusinessRuleViolationError`).
- **`HardDeleteStrategy`**: `DELETE` físico del registro.

El router expone el tipo de estrategia como query param:
```python
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_person(id: int, strategy: DeletionType = Query(DeletionType.SOFT), ...):
    ...
```

**`Order` no tiene `DELETE`:** no tiene columna `active`, y un pedido no se borra — se
cancela (transición a `CANCELLED`, pendiente; ver sección 12).

---

## 4. Modelado de entidades — convenciones

### Relaciones y referencias cruzadas

Toda FK se declara dos veces: la columna física (`ForeignKey(...)`) y la navegación Python
(`relationship(...)`), enlazadas en ambos lados con `back_populates` (equivalente a las
navigation properties bidireccionales de EF Core). **Cada `back_populates` debe tener su
pareja exacta** en la clase del otro lado — es el error más común y silencioso al modelar
relaciones; SQLAlchemy lo reporta recién cuando algo toca esa relación en ejecución, no al
arrancar la app.

Para evitar imports circulares entre entidades que se referencian mutuamente:
```python
if TYPE_CHECKING:
    from app.models.parametersModule.zone import Zone


class Neighborhood(Base):
    zone: Mapped["Zone"] = relationship(back_populates="neighborhoods")
```
En tiempo de ejecución, SQLAlchemy resuelve `Mapped["Zone"]` mediante su propio *registry*
interno — no hace falta importar la clase real, siempre que ambas hayan sido importadas en
algún punto (por eso `models/__init__.py` importa todas las entidades, registrándolas en
`Base.metadata`). El bloque `TYPE_CHECKING` es solo para que el editor/type-checker
(Pylance/mypy) tenga autocompletado, sin generar imports reales ni riesgo de ciclo.

### Entidades de asociación (tablas pivote)

Cuando una tabla intermedia tiene **PK propia y/o columnas adicionales** (ej. `UserRole`,
`SpecialCustomerPrice`), se modela como entidad completa, no con el atajo
`relationship(secondary=...)` de SQLAlchemy (que solo aplica a M2M "puros").

### Constraints e índices

Traducidos fielmente desde el DDL original con `__table_args__`:
`UniqueConstraint`, `CheckConstraint`, `Index` (Postgres no indexa automáticamente las FKs,
solo las PKs). Cada `CHECK` se revisa individualmente — los operadores no siempre coinciden
entre columnas similares (`>= 0` vs `> 0` según el caso real de negocio).

### Dinero

Todos los campos monetarios usan `Numeric(12, 2)` a nivel de columna y `Decimal` (de
`decimal.Decimal`) como tipo Python — **nunca `Float`**, para evitar errores de redondeo
binario (IEEE 754) en operaciones financieras.

### Fechas y horas

No todos los campos de fecha/hora se tratan igual — depende de **cuándo se conoce el
valor** y **qué tipo de dato representa**:

| Caso | Tipo de columna | Default | Ejemplo |
|---|---|---|---|
| Instante absoluto, generado por la BD | `DateTime(timezone=True)` | `server_default=func.now()` | `Order.creation_datetime` |
| Hora del día, decisión de negocio al crear | `Time` | Sin default, la aporta quien registra | `Order.estimated_delivery` |
| Hora del día, evento posterior (fuera del INSERT) | `Time` | Sin default, asignado explícito en el service | `Order.dispatch_time`, `delivery_time` |

**`default` vs `server_default`:** `default=...` se resuelve en Python, al momento del
INSERT hecho por SQLAlchemy — no aplica si otro sistema inserta directo por SQL.
`server_default=...` se resuelve en PostgreSQL a nivel de columna, se garantiza siempre, y
Alembic lo refleja en el DDL generado. Para timestamps de auditoría, siempre
`server_default`.

**`Time` no necesita zona horaria** — representa una hora del día en el contexto de la
operación ("3:00 PM, hora de Bogotá"), no un instante fijo en la línea temporal universal.
Postgres tiene `TIME WITH TIME ZONE` pero su propia documentación recomienda evitarlo (es
ambiguo, no se sabe a qué fecha corresponde).

**Zona horaria explícita — `app/core/timezone.py` es la única fuente:**

| Necesidad | Cómo |
|---|---|
| Hora actual de Bogotá (Python) | `datetime.now(BOGOTA_TZ).time()` |
| Fecha de hoy en Bogotá (Python) | `today_bogota()` (p. ej. `Query(default_factory=today_bogota)`) |
| Mostrar un `TIMESTAMPTZ` leído de la BD | `valor.astimezone(BOGOTA_TZ)` antes de formatear |
| **Filtrar** por día/rango local en SQL | `on_bogota_day(col, día)` / `between_bogota_dates(col, desde, hasta)` (`repositories/time_filters.py`) |
| Filtrar por "hoy" según la BD (junto al consecutivo) | `on_db_today(col)` |
| **Mostrar o agrupar** por fecha u hora local en SQL | `func.timezone(BOGOTA_TZ.key, columna)` y luego `cast(..., Date)` / `func.to_char(...)` |

Nunca `datetime.now()` ni `date.today()` sin zona — dependen de la zona horaria del servidor
(en producción suele ser UTC). Del mismo modo, `func.date(columna_timestamptz)` sin
convertir usa la zona de la **sesión de PostgreSQL**: un pedido creado después de las 7 p. m.
de Bogotá caería en el día siguiente si la BD está en UTC.
**Filtrar siempre por rango, nunca aplicando funciones a la columna:** los helpers de
`time_filters.py` traducen el día de Bogotá a un rango de instantes
(`col >= inicio AND col < fin`), así PostgreSQL usa el índice
`idx_sale_order_creation_datetime`. Un `WHERE date(timezone(..., col)) = día` recorre la
tabla completa. La conversión con `func.timezone` queda solo para el `SELECT`/`GROUP BY`;
al agrupar por esa expresión se agrupa por su **alias** (`.group_by("order_day")`), porque
repetir la expresión duplica el parámetro de la zona y PostgreSQL no la reconoce como la
misma.

Requiere el paquete `tzdata` instalado (`zoneinfo` de la librería estándar no trae los datos
de zonas horarias en Windows por defecto).

### Enums — dos patrones distintos según cómo se persiste el valor

Todos los enums viven centralizados en **`app/utils/enums/`** (`archive_status.py`,
`day_week.py`, `delete_type.py`, `order_state.py`); los modelos y schemas los importan desde ahí.

**A) Enum de texto** (ej. `OrderState`):
```python
class OrderState(str, enum.Enum):
    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


state: Mapped[OrderState] = mapped_column(
    SQLEnum(
        OrderState,
        name="chk_order_state",
        native_enum=False,
        length=20,
        values_callable=lambda e: [x.value for x in e],
    ),
    nullable=False,
    default=OrderState.PENDING,
)
```
`native_enum=False` es la decisión clave: la columna física queda como `VARCHAR` + un
`CHECK` autogenerado, **no** un tipo `ENUM` nativo de Postgres (más rígido de modificar:
agregar un valor requiere `ALTER TYPE ... ADD VALUE` con restricciones de transacción).
*(Lección aprendida: una primera versión sin `native_enum=False` creó un ENUM nativo real;
migrar de vuelta a VARCHAR falló por incompatibilidad de operadores entre tipos — la
corrección robusta fue columna temporal + copia de datos + drop del tipo huérfano.)*

**B) Enum numérico** (`IntEnumType`): `sqlalchemy.Enum` solo sabe guardar como
texto, así que se creó un `TypeDecorator` propio en `app/db/custom_types.py`:
```python
class IntEnumType(TypeDecorator):
    impl = Integer
    cache_ok = True

    def __init__(self, enum_class, *args, **kwargs): ...
    def process_bind_param(self, value, dialect): ...  # Python -> BD: enum -> int
    def process_result_value(self, value, dialect): ...  # BD -> Python: int -> enum
```
La columna física sigue siendo `INTEGER` (con su `CheckConstraint` de rango como respaldo),
pero el atributo Python devuelve directamente una instancia del enum, no un `int` suelto.
Hoy ningún modelo lo usa (lo usaba `Route.day_week`), pero se conserva porque la migración
inicial lo referencia.

**C) Lista de valores de un enum numérico** (`Route.days_week`): una ruta sale varios días
de la semana, así que se guarda como `SMALLINT[]` de PostgreSQL (`ARRAY(SmallInteger)`)
con un `CHECK` que exige al menos un día y solo valores 1..7. En el schema el campo es
`list[DayWeek]` (`min_length=1`), se normaliza sin repetidos y en orden (`[4, 1, 1]` →
`[1, 4]`) y se serializa como enteros. Al editar se reemplaza la lista completa (SQLAlchemy
no detecta mutaciones en sitio de un `ARRAY`). Para buscar las rutas de un día:
`dia == any_(Route.days_week)` (`ARRAY.any()` está obsoleto desde SQLAlchemy 2.1).

**Alembic y tipos personalizados:** cuando una columna usa un tipo con argumentos
obligatorios (`IntEnumType(DayWeek)`), Alembic no genera automáticamente el argumento al
autogenerar — requiere un hook `render_item` en `env.py` (ver sección 7) para que la
migración autogenerada incluya correctamente el import y el argumento.

**Reutilización en schemas:** los schemas usan el mismo enum que el modelo, sin
redefinirlo — es una excepción deliberada a "modelo y schema son independientes", porque un
`Enum` es una lista cerrada de valores, no una regla de negocio que deba divergir entre
capas.

---

## 5. Schemas (Pydantic) — convenciones

### Patrón estándar por entidad

```
XxxBase (atributos compartidos) → XxxCreate → XxxUpdate → XxxResponse
```

- **`XxxCreate`**: hereda de `Base`. Agrega campos exclusivos de creación (ej. `password`
  en `UserCreate`) y **excluye** campos con `server_default` o valor inicial fijo (ej.
  `state` de `Order` nunca se pide — siempre nace `PENDING`).
- **`XxxUpdate`**: todos los campos opcionales, para soportar `PATCH` (actualización
  parcial). **Generado automáticamente**, no repetido a mano (ver `partial_model` abajo). A
  veces se declara **explícito y acotado**, heredando directo de `BaseModel` en vez de
  `Base`, cuando la regla de negocio exige restringir qué campos son editables: `OrderUpdate`
  solo tiene `id_user_vehicle` (`null` para desasignar); los items se editan por
  `sync_items` y el resto de campos de `Order` no se tocan por esta vía.
- **`XxxResponse`**: hereda de `Base`, agrega el/los identificador(es) y cualquier campo que
  solo tenga sentido en la salida. Declara `model_config = ConfigDict(from_attributes=True)`
  (sintaxis de Pydantic v2; la clase interna `class Config` está obsoleta) para
  construirse directamente desde una instancia ORM.

**Decisión explícita:** a diferencia de un enfoque con un solo DTO para crear y actualizar
(donde la lógica de negocio decide qué hacer con el `Id`), aquí se usan schemas separados,
porque Pydantic necesita campos opcionales para soportar `PATCH` real sin sacrificar
validación estricta al crear.

### `partial_model` — generación automática de `Update`

```python
from app.utils.helpers.schema_helper import partial_model


@partial_model
class PersonUpdate(PersonBase):
    pass
```

Utilidad en `app/utils/helpers/schema_helper.py` que usa `pydantic.create_model` para
generar dinámicamente una versión de cualquier schema con todos los campos opcionales
(`default=None`), **conservando** las validaciones originales (`max_length`, etc.) vía
`copy.deepcopy` de cada `FieldInfo`. Evita repetir cada campo manualmente. Los
`# type: ignore` presentes en la implementación son necesarios porque los *stubs* de tipado
de Pydantic no logran describir con precisión la generación dinámica de modelos — no ocultan
errores reales.

### Texto normalizado — `UpperText` / `LowerText`

`app/utils/schema_types.py` define tipos `Annotated` que hacen `strip` y cambio de caja
**antes** de validar longitudes, así que `"   "` se rechaza como vacío:

- `UpperText`: nombres y direcciones de clientes (`ClientBase` y también `NewClientInput`,
  el cliente que se crea desde el flujo de pedido — ambos caminos guardan igual).
- `LowerText`: `username`.

Como exigen al menos un carácter, un campo opcional sin valor se envía como `null` u
omitido, no como `""`.

### Validaciones de negocio replicadas en el schema

Los `CHECK` de la base de datos se replican como validaciones Pydantic en la frontera de la
API (`Field(..., ge=0)`, `Field(..., gt=0)`), dando un error 422 claro y temprano en vez de
una excepción de PostgreSQL menos amigable. No reemplazan el `CHECK` de la BD, que sigue
siendo la garantía final.

---

## 6. Seeds — datos iniciales

`python -m app.db.seeds` carga los datos de `app/db/seeds/data/<módulo>/*.jsonc`
(JSON con comentarios, leído con `json5`).

- **Orden:** la tupla `SEEDS` de `registry.py` **es** el orden de dependencias (personas y
  roles antes que usuarios, zonas antes que barrios, etc.). No se debe alterar.
- **Validación:** cada registro pasa por el schema `Create` de su entidad, así que aplican
  las mismas reglas que en la API; un campo desconocido en el `.jsonc` detiene la carga.
  Un `transform` opcional permite preparar datos (p. ej. hashear contraseñas).
- **Idempotente por tabla:** si una tabla ya tiene filas, se omite.
- **IDs esperados:** las referencias entre archivos asumen que el registro N recibe el ID N.
  Si la secuencia no arranca en 1 (tabla vaciada sin reiniciar la identidad), la carga falla
  con un mensaje que indica usar `TRUNCATE ... RESTART IDENTITY`.
- **Todo o nada:** un único `commit()` al final; cualquier error hace `rollback()`.
- **Vendedor por defecto:** los seeds asignan a "HIELO FOCA" (usuario `admin`) el rol
  `VENDEDOR` y un `user_vehicle` con código `01` (ver Vista Cierre). En una BD que ya tenía
  datos hay que crearlo a mano (`POST /user_roles` + `POST /user_vehicles`).

---

## 7. Alembic — configuración especial

- **`prepend_sys_path = .`** en `alembic.ini`: sin esto, `env.py` no encuentra el paquete
  `app` (Alembic no garantiza que la raíz del proyecto esté en `sys.path` por defecto).
- **Secciones de logging completas** (`[loggers]`, `[handlers]`, `[formatters]`, etc.) en
  `alembic.ini` — si faltan, `fileConfig()` falla con `KeyError`.
- **`import app.models` en `env.py`** antes de `target_metadata = Base.metadata` — sin esto,
  `Base.metadata` queda vacío y `--autogenerate` genera migraciones vacías. Ruff puede
  marcarlo como import no usado (`F401`) y un auto-organize de imports puede borrarlo; se
  protege con `# noqa: F401`.
- **Hook `render_item`** para tipos personalizados (`IntEnumType`):
  ```python
  def render_item(type_, obj, autogen_context):
      if type_ == "type" and isinstance(obj, IntEnumType):
          autogen_context.imports.add(
              f"from {obj.enum_class.__module__} import {obj.enum_class.__name__}"
          )
          return f"app.db.custom_types.IntEnumType({obj.enum_class.__name__})"
      return False


  # en run_migrations_online(): context.configure(..., render_item=render_item)
  ```
  Sin esto, Alembic genera `IntEnumType()` vacío (sin el argumento `enum_class` obligatorio),
  rompiendo la migración al aplicarla.

### Flujo estándar

```bash
alembic revision --autogenerate -m "descripcion"
# revisar el archivo generado antes de aplicar — especialmente cambios de tipo de columna
# (pueden requerir postgresql_using) o columnas con tipos personalizados
alembic upgrade head
```

---

## 8. Autenticación y autorización

### JWT access + refresh con rotación (mismo patrón que Google/grandes corporaciones)

| Token | Vida | Dónde vive | Propósito |
|---|---|---|---|
| **Access token** | Corta (60 min, configurable) | En memoria del frontend | Autoriza cada petición. Stateless — nunca se guarda en BD. |
| **Refresh token** | Larga (30 días, configurable) | Body de respuesta (cookie en `httpOnly`) | Renueva el access token sin re-login. **Con estado**, registrado en `user_session`. |

**Por qué el refresh token necesita tabla propia:** un JWT es stateless por diseño — el
servidor nunca lo "recuerda", solo valida su firma y `exp`. Esto es ideal para el access
token, pero imposibilita revocar un refresh token robado antes de que expire por sí solo. La
tabla `user_session` le da estado (y por tanto, control) al refresh token.

**`user_session`** (una fila = una sesión activa/histórica en un dispositivo):
`refresh_token_hash` (SHA-256, nunca el token en texto plano), `id_user`, `user_agent`,
`ip_address`, `expires_at`, `revoked`, `created_at`.

**Rotación + detección de reutilización** (`AuthService`):
1. **Login** → crea una fila nueva (`revoked=false`).
2. **Refresh** → busca la fila activa por el hash recibido **bloqueándola**
   (`SELECT ... FOR UPDATE`); si existe y no expiró, se marca `revoked=true` y se crea una
   fila nueva con un token distinto (rotación). Revocación y sesión nueva se confirman en
   **un solo `commit()`**, y el bloqueo dura hasta ese momento.
3. **Reutilización detectada**: si el token recibido corresponde a una fila **ya
   revocada**, es señal de robo (el legítimo ya rotó, alguien más tiene una copia vieja) →
   se revocan **todas** las sesiones activas de ese usuario (`revoke_all_for_user`),
   forzando re-login en todos los dispositivos.
4. **Logout** → revoca solo la sesión actual. **Logout-all** → revoca todas las del usuario.

**Dos refresh simultáneos con el mismo token:** el segundo espera el bloqueo y, al
continuar, encuentra la sesión ya revocada → se trata como reutilización (paso 3) y se
cierran todas las sesiones del usuario. Es el comportamiento seguro, pero implica una
regla para el frontend: **un solo refresh en vuelo a la vez** (si varias peticiones
reciben 401 al mismo tiempo, todas esperan la misma promesa de refresh en lugar de lanzar
una cada una).

**Hasheo del refresh token:** SHA-256 (determinístico, para poder *buscar* por hash exacto),
**no** `pwdlib`/Argon2 (que genera un hash distinto cada vez, pensado para que no se pueda
hacer *lookup* — correcto para contraseñas, inútil aquí).

### Roles embebidos en el JWT (equivalente a claims de ASP.NET Core)

Al hacer login, se consultan los roles del usuario (`UserRole` → `Role`) y se embeben en el
payload del access token:
```python
access_token = create_access_token(
    subject=user.id_user, roles=["GESTOR_COMERCIAL", ...]
)
```
Trade-off aceptado: un cambio de rol solo se refleja en el próximo login, no en la sesión
activa (mismo comportamiento que los claims de JWT en cualquier stack). La desactivación de
un usuario, en cambio, sí es inmediata: `get_current_user` recarga el `User` en cada
petición y rechaza con 401 si `active = False`.

### Doble nivel de protección — `SecuredRouter`

Equivalente a `[Authorize]` de clase + `[Authorize(Roles = "...")]` de acción en ASP.NET
Core, resuelto con un `APIRouter` extendido (`app/api/routers/auth/secured_router.py`) que
intercepta `get/post/put/patch/delete` para inyectar automáticamente una dependencia de rol:

```python
router = SecuredRouter(prefix="/roles", tags=["Roles"])

@router.get("/")                              # sin roles= → requiere ADMINISTRADOR (por defecto)
def get_all_roles(...): ...

@router.post("/", roles=["GESTOR_COMERCIAL"])  # ADMINISTRADOR o GESTOR_COMERCIAL
def create_role(...): ...
```

Roles del sistema: `ADMINISTRADOR`, `GESTOR_COMERCIAL` (opera las vistas de Pedidos,
Rutas, Histórico y Cierre) y `VENDEDOR` (el domiciliario; hoy no usa la API directamente).

`ADMINISTRADOR` siempre hace bypass total, sin importar `roles=[...]`. Sin `roles=[...]`
declarado, el endpoint exige `ADMINISTRADOR` exclusivamente (comportamiento seguro por
defecto — todo nuevo endpoint nace restringido, hay que abrirlo explícitamente). El mensaje
de error 403 incluye siempre `ADMINISTRADOR` en la lista de roles aceptados, aunque no se
haya declarado explícitamente, para que el mensaje sea honesto sobre qué roles realmente
sirven.

**Importante:** nunca mezclar la sintaxis manual (`dependencies=[Depends(require_roles(...))]`)
con `SecuredRouter` en el mismo endpoint — se acumulan ambas dependencias en vez de
reemplazarse, causando bloqueos inesperados. Siempre usar el kwarg `roles=[...]`.

### Contraseñas

`pwdlib[argon2]` (Argon2, ganador de la Password Hashing Competition, recomendado sobre
bcrypt actualmente). El hasheo ocurre en la capa `services` (`_before_create` del
`UserService`), nunca en el schema ni en el modelo.

---

## 9. Manejo de errores

### Jerarquía `BusinessError` (`utils/exceptions/business_exceptions.py`)

Excepciones de negocio desacopladas de HTTP (no conocen status codes):
`EntityNotFoundError`, `BusinessValidationError`, `ConflictError`,
`BusinessRuleViolationError`, `UnauthorizedError`, `ForbiddenError`, `ExternalServiceError`.
Cada una trae `.message`, `.code`, `.field` opcional. Firmas a tener en cuenta:
`BusinessRuleViolationError(message, rule_code=...)` (no `code=`),
`EntityNotFoundError(entity_type, id)` y `ExternalServiceError(service_name, message)`
(→ 502, p. ej. si Google Sheets falla).

### Traducción a HTTP (`api/exception_handlers.py`)

Un `exception_handler` global mapea cada tipo de `BusinessError` a su status code
correspondiente (recorriendo el MRO, así una subclase futura hereda el status de su padre si
no se registra explícitamente), devolviendo siempre el mismo formato:
```json
{"detail": "...", "code": "...", "field": null}
```

Un segundo handler captura `IntegrityError` de SQLAlchemy (violaciones de constraint a nivel
de BD que se escapan de las validaciones de negocio) y las traduce según el código SQLSTATE
de Postgres (`23505` → conflicto de duplicado, `23503` → violación de FK), sin exponer el
detalle técnico de la excepción original al cliente (se loggea, no se retorna).

**Nota conocida:** los errores de validación nativos de Pydantic/FastAPI (`422` por schema
inválido) usan el formato nativo de FastAPI, distinto al formato uniforme de
`BusinessError` — decisión consciente, pendiente de resolver en el frontend con un segundo
handler de errores allá.

---

## 10. Flujos de negocio implementados

### Registro de pedido — operación atómica multi-tabla

**El problema de fondo:** `BaseRepository.create()` hace `commit()` inmediato por cada
llamada — perfecto para una tabla, peligroso para una operación que toca
`Client`/`Order`/`OrderDetail` en conjunto (un fallo a mitad de camino dejaría registros
huérfanos).

**La solución — patrón Unit of Work explícito en el service:**
```python
def add(self, db: Session, *, obj_in_data: dict[str, Any]) -> ModelType:
    """flush() en vez de commit() — reversible hasta el commit final del service."""
    db_obj = self.model(**obj_in_data)
    db.add(db_obj)
    db.flush()
    return db_obj
```
`OrderService` usa `repository.add(...)` (no `create()`) para cada entidad involucrada, y
hace **un único `db.commit()`** al final de toda la operación. Si cualquier validación falla
en el camino (producto inexistente, barrio inválido), nada se compromete — equivalente
conceptual a `DbContext.SaveChanges()` en EF Core.

`get_db()` también se reforzó con `rollback()` en el `except`, como red de seguridad general
ante cualquier excepción no capturada que suba hasta el router sin commit explícito.

**Dos flujos de creación, no genéricos:**
- `POST /orders/new-client` (`create_for_new_client`): recibe datos del cliente inline
  (`NewClientInput`, sin `is_registered`/`active` expuestos — el service fuerza
  `is_registered=False`, ya que clientes nuevos no permanecen indefinidamente en BD) +
  items del pedido. Nombre y dirección se normalizan con `UpperText`, igual que en
  `POST /clients`.
- `POST /orders/existing-client` (`create_for_existing_client`): recibe solo `id_client`
  (no se permite editar datos del cliente desde este flujo — eso es responsabilidad de
  `PATCH /clients/{id}`, por separado). Solo acepta clientes **registrados**
  (`is_registered=True`); un temporal responde 422 `CLIENT_NOT_REGISTERED`.
- `POST /orders/routes/{id_route}`: pedidos en lote desde una ruta (ver "Pedidos por
  ruta").

**`purchase_order` — consecutivo diario:** cada pedido recibe `"001"`, `"002"`, … según el
día de Bogotá en que se crea; al día siguiente vuelve a `"001"` y los días anteriores
conservan sus números. El contador vive en `daily_order_counter` (una fila por día) y se
incrementa con `INSERT ... ON CONFLICT DO UPDATE ... RETURNING` dentro de la misma
transacción del pedido: dos pedidos simultáneos nunca reciben el mismo número y, si el
pedido falla, el incremento se revierte. Usa `now()` de la BD, el mismo instante que
recibe `creation_datetime`. Máximo 999 por día (`DAILY_ORDER_LIMIT`).

Ambos validan referencias (barrio/cliente, productos) **antes** de crear nada, calculan
`subtotal = cant * unit_price` por cada item (nunca se confía en un subtotal enviado por el
cliente) y `order_total` como la suma. Un mismo producto no puede repetirse en dos
renglones del pedido (`_ensure_no_duplicate_products` → 422 con código
`DUPLICATE_PRODUCT`); la cantidad se agrupa en un solo renglón. `id_user_taker` se obtiene del usuario autenticado
(`current.user.id_user`), nunca del body — ya disponible porque `get_current_user` carga el
`User` completo desde el JWT.

**`unit_price` (decisión explícita del MVP):** se acepta el precio unitario que envía el
frontend (precargado desde el catálogo y editable por el vendedor), sin compararlo contra
`effective_price` ni auditar diferencias. Validar y auditar desviaciones de precio queda
para una iteración posterior.

**No existe `POST /orders/` genérico** — un `Order` sin `OrderDetail` no tiene sentido de
negocio, así que solo existen los dos flujos especializados.

### Edición de productos de un pedido — sincronización completa (`PUT`, no `PATCH`)

`PUT /orders/{id}/items-order` recibe la **lista final deseada** de items; el backend
calcula qué agregar/editar/eliminar comparando contra lo existente:
```python
class OrderItemSync(BaseModel):
    id_order_detail: (
        int | None
    )  # None = producto nuevo; con valor = edición de ese renglón
    id_product: int
    cant: int
    unit_price: Decimal
```
Cualquier `OrderDetail` existente que **no** aparezca en la lista enviada se elimina. Mismo
patrón de atomicidad (`flush`/`commit` único) que la creación. Solo permitido mientras
`order.state == PENDING`. La lista final tampoco puede repetir productos (misma validación
que la creación, aplicada antes de modificar nada). Se valida en el service y no con un
`UniqueConstraint(id_order, id_product)` en BD, porque la sincronización borra y reescribe
renglones dentro de la misma transacción.

**`/orders_details` es solo lectura** (`GET /` y `GET /{id}`, ADMIN): los detalles se
crean, editan y eliminan únicamente por este endpoint de sincronización, que valida el
estado del pedido y recalcula `order_total`.

**Cuidado al eliminar de una colección ya cargada en memoria:** no basta con `db.delete(obj)`
si `obj` sigue referenciado en una relación cargada (`order.order_details`) — hay que
removerlo explícitamente de la colección también (`order.order_details.remove(detail)`)
antes/junto con el `db.delete()`, o SQLAlchemy lanza `InvalidRequestError` al intentar
sincronizar esa colección más adelante (ej. en un `refresh()` posterior).

### Catálogo de productos con precio resuelto

`GET /products/catalog?id_client={opcional}` — `LEFT JOIN` contra `SpecialCustomerPrice`
filtrado por cliente; devuelve `base_price`, `agreed_price` (si existe) y `effective_price`
(el que realmente aplica). Pensado para precargar precios editables en el formulario de
pedido sin una llamada por producto.

### Búsqueda de clientes existentes

`GET /clients/search?name=...` — búsqueda parcial case-insensitive (`ILIKE`), para precargar
datos de un cliente existente en el flujo de registro de pedido. Solo devuelve clientes
**registrados** y activos: los temporales (`is_registered=False`, creados desde
`/orders/new-client`) no aparecen.

### Consultas de pedidos para la UI

- **`GET /orders/dashboard-summary?target_date=AAAA-MM-DD`** (`GESTOR_COMERCIAL`): tabla
  principal del día, con los pedidos por gestionar: `PENDING` y `CANCELLED`.
- **`GET /orders/dispatched-summary?target_date=AAAA-MM-DD`** (`GESTOR_COMERCIAL`): vista de
  los pedidos del día que ya salieron: `DISPATCHED` y `DELIVERED`.

  Ambas comparten la misma consulta (`RepositoryOrder._summary_by_states`) y el mismo
  formato de respuesta (`OrderSummaryResponse`). `target_date` es opcional y por defecto
  toma la fecha de hoy en Bogotá (`today_bogota`). El filtro por día y la hora mostrada
  (`creation_time`) se calculan sobre `creation_datetime` convertido a hora de Bogotá en
  SQL; el "día" de un pedido es el de su creación.
- **`GET /orders/{id}/details`** (`GESTOR_COMERCIAL`): detalle completo para el modal —
  items (con `id_order_detail`, para editarlos luego vía `PUT /items-order`), cliente,
  barrio, zona y conductor. `driver_code` / `driver_name` llegan en `null` si el pedido no
  tiene conductor asignado. Es la misma consulta que alimenta el PDF.

### Vista de Rutas

Roles: `GESTOR_COMERCIAL` (y `ADMINISTRADOR`). Desactivar/eliminar una ruta
(`DELETE /routes/{id}`) sigue siendo solo de `ADMINISTRADOR`.

- **`GET /routes/cards?only_active=false`**: una card por ruta con nombre, `days_week`,
  hora de salida, estado y `clients_count` (clientes **activos** asignados). Incluye las
  rutas inactivas salvo `only_active=true`.
- **`POST /routes/`** y **`PATCH /routes/{id}`**: crear y editar (`days_week` como lista,
  ver sección 4).
- **`GET /routes/{id}/clients`**: clientes asignados, con teléfono, dirección, barrio, zona,
  estado y su **pedido base** (`base_items`: producto, código, nombre y cantidad).
- **`GET /routes/{id}/available-clients`**: selector de clientes para asignar —
  registrados, activos y aún no asignados a esa ruta.
- **`POST /routes/{id}/clients`** `{"id_client": ...}`: asigna un cliente (debe existir,
  estar activo y ser **registrado**: 422 `CLIENT_NOT_REGISTERED`; 409 si ya está asignado).
  Se permite aunque la ruta esté inactiva.
- **`DELETE /routes/{id}/clients/{id_client}`**: quita la asignación (borra la fila de
  `client_route` y, en cascada, su pedido base; el cliente no se toca). 404 si no estaba
  asignado.
- **`PUT /routes/{id}/clients/{id_client}/base-order`** `{"items": [{"id_product", "cant"}]}`:
  guarda el **pedido base** del cliente en la ruta (lo que suele pedir cada vez que sale).
  Es la lista FINAL: reemplaza la anterior y una lista vacía lo borra. Productos que existan
  y estén activos (`REFERENCE_INACTIVE`), sin repetidos (`DUPLICATE_PRODUCT`), `cant > 0`.
  404 si el cliente no está en la ruta. Tabla `client_route_item` (FK a `client_route` con
  `ON DELETE CASCADE`, único por producto). No guarda precio: se resuelve al generar el
  pedido.

El CRUD genérico `/client_routes` se mantiene solo para `ADMINISTRADOR`; la vista usa los
endpoints anidados bajo `/routes/{id}/clients`.

### Pedidos por ruta

Flujo plantilla → formulario → POST (`GESTOR_COMERCIAL`):

1. **`GET /orders/routes-of-day?target_date=`**: rutas activas que salen ese día de la
   semana, con `clients_count` y cuántos pedidos de ese día salieron de cada una.
2. **`GET /orders/routes/{id}/template`**: precarga del formulario — productos del
   catálogo y, por cliente de la ruta (registrado y activo), el precio que le aplica a cada
   producto (`is_special` si es precio pactado), `existing_order_id` si ya tiene pedido de
   hoy desde esa ruta y `base_items` (su pedido base, solo productos activos) para
   precargar las cantidades.
3. **`POST /orders/routes/{id}`**: crea en **una sola transacción** los pedidos de los
   clientes que vienen con productos (todo o nada). Bloquea la ruta (`FOR UPDATE`) para que
   dos gestores no la generen dos veces. Rechaza ruta inactiva (`ROUTE_INACTIVE`), clientes
   repetidos (`DUPLICATE_CLIENT`), clientes fuera de la ruta (`CLIENT_NOT_IN_ROUTE`) y
   clientes que ya tienen pedido de hoy desde la ruta (409 `ROUTE_ORDER_EXISTS`). Los
   errores de renglón indican el cliente. Cada pedido guarda `id_route` (FK opcional en
   `sale_order`) y recibe su consecutivo diario.

### Vista Histórico

**`GET /orders/history`** (`GESTOR_COMERCIAL`): listado paginado de pedidos, del más
reciente al más antiguo.

- Filtros: `date_from` / `date_to` (por defecto, del 1 del mes anterior a hoy: lo que
  retiene la BD; ambos extremos incluidos; 422 `INVALID_DATE_RANGE` si están invertidos),
  `state`, `id_route`, `id_user_vehicle` y `search` (nombre del cliente o N.° de pedido
  exacto). Paginación `page` / `page_size` (1–200).
- Cada fila: fecha y hora (Bogotá), N.° de pedido, cliente, zona, ruta, productos y
  cantidad, total, conductor y estado.
- Respuesta con `total`, `pages` y `total_sales` del filtro completo (sin cancelados).
- Los productos se agregan en una subconsulta por pedido, así la paginación es sobre
  pedidos y no sobre renglones de detalle.

### Vista Cierre — factura global por vendedor y exportación a Siigo

El cierre del día consolida los pedidos **despachados y entregados** de un día (el de su
creación, en Bogotá) en una factura global por vendedor (`user_vehicle`). Reglas:

- `PENDING` y `CANCELLED` no se facturan; solo aparecen en las cards.
- Los pedidos **sin conductor** se suman al vendedor por defecto
  (`DEFAULT_SELLER_CODE`, `"01"`). La asignación ocurre solo en el cierre: el pedido no se
  modifica. Si hay pedidos sin conductor y ese vendedor no existe → 422
  `DEFAULT_SELLER_MISSING`.
- Siigo recibe el código del vendedor como **número** (`"01"` → `1`), por eso
  `user_vehicle.code` exige 2 dígitos al crear/editar (`^\d{2}$`); un código antiguo no
  numérico responde 422 `INVALID_SELLER_CODE` en el cierre.
- No se puede cerrar una fecha futura (422 `INVALID_CLOSURE_DATE`).

Endpoints (`GESTOR_COMERCIAL`), bajo `/shifts_closures`:

- **`GET /shifts_closures/summary?target_date=`**: cards (total del día, pendientes,
  despachados, entregados, cancelados, vendedores e ingreso facturable) y una fila por
  vendedor, ordenada por código: productos con cantidad (sumando sus distintos precios),
  cantidad total, pedidos, `unassigned_orders` (pedidos sin conductor sumados al vendedor
  por defecto) y total vendido. Por fila, `exported_at` y `export_outdated` (se exportó,
  pero los pedidos o el total cambiaron después); `exported` resume todo el día.
- **`POST /shifts_closures/{fecha}/export`**: descarga `cierre_AAAA-MM-DD.xlsx`
  (`closure_export.py`). Columnas `Fecha | Cód. vendedor | Vendedor | Cód. producto |
  Producto | Cantidad | Precio unit. | Subtotal`, un renglón por vendedor + producto +
  precio, una fila "Total vendedor" por vendedor y "TOTAL DEL DÍA". Formato provisional
  hasta que Siigo defina su plantilla. 422 `NO_BILLABLE_ORDERS` si el día no tiene pedidos
  facturables.

**Cerrar el día = exportarlo.** No hay otra acción que escriba en `shift_closure`: la
exportación hace un *upsert* (`ON CONFLICT` sobre `uq_shift_closure_date_vehicle`) de un
cierre por vendedor y día con `total_orders`, `total_sales`, `exported_siigo=True` y
`exported_at`, y elimina los cierres de ese día de vendedores que ya no tienen pedidos
facturables (p. ej. se les reasignó el pedido). Reexportar está permitido y refleja los
pedidos actuales. El Excel se genera **antes** de escribir en la BD: si falla, no queda
nada marcado como exportado. El CRUD `/shifts_closures` (`GET /` y `GET /{id}`) es de solo
lectura para `ADMINISTRADOR`.

La consolidación (`ShiftClosureService.consolidate`) es una sola y la usan el resumen y la
exportación: renglones agrupados por (vendedor, producto, precio) en SQL y fusión en Python
de los pedidos sin conductor con los propios del vendedor por defecto.

### Archivado mensual — Google Sheets y purga

Para que la BD no crezca sin límite, se conservan `HISTORY_RETENTION_MONTHS` meses (2: el
vigente y el anterior). Los meses más viejos se exportan a Google Sheets y se borran.
Todo es manual y solo de `ADMINISTRADOR` (`/archive`):

- **Configuración:** un spreadsheet por año (`archive_spreadsheet`),
  `PUT /archive/spreadsheets/{año}` con el ID o la URL; `GET /archive/spreadsheets`. La API
  escribe con una **cuenta de servicio** (`GOOGLE_CREDENTIALS_FILE`); el spreadsheet debe
  estar compartido como editor con su `client_email`.
- **`POST /archive/{AAAA-MM}/export`**: escribe (o reescribe) la pestaña del mes con **una
  fila por producto vendido** de todos los pedidos del mes, en cualquier estado
  (`archive_export.py`), verifica leyendo de vuelta cuántas filas quedaron y registra la
  bitácora `monthly_archive` como `EXPORTED`. Los pedidos no se borran.
- **`POST /archive/{AAAA-MM}/purge`**: solo meses fuera de la retención
  (`MONTH_WITHIN_RETENTION`). Reexporta el estado final, verifica y, en **la misma
  transacción**, borra exactamente los pedidos exportados (sus detalles caen por
  `ON DELETE CASCADE`), los clientes temporales que quedaron sin pedidos, los contadores
  diarios viejos y las sesiones vencidas; la bitácora pasa a `PURGED`. Si Google o la
  verificación fallan, no se borra nada (502). Un mes con días facturables **sin cierre
  exportado o con cambios posteriores a la exportación** se rechaza con 422
  `MONTH_NOT_CLOSED` (lista los días), porque sin los pedidos ya no se podría generar su
  cierre. Los `shift_closure` no se borran: quedan como registro de lo enviado a Siigo.
- **`GET /archive/`**: bitácora de meses exportados y purgados.

Exportación y purga se serializan con un `pg_advisory_xact_lock`: una a la vez. El servicio
depende del protocolo `SheetsWriter`, inyectado con `Depends(get_sheets_writer)`; en los
tests se reemplaza por `FakeSheetsWriter` y nunca se llama a Google.

### Ciclo de vida del pedido — máquina de estados

```
PENDING ──(/dispatch)──> DISPATCHED ──(/deliver)──> DELIVERED
   │                          │
   └──────── (reasignar conductor: PATCH, mientras no sea estado final) ────────┘

CANCELLED es estado terminal alcanzable desde los anteriores (gestión pendiente de endpoint dedicado)
```

- **`PATCH /orders/{id}`** (`GESTOR_COMERCIAL`): body `{"id_user_vehicle": <id> | null}`.
  Único campo editable (asignar, reasignar o desasignar conductor). Bloqueado si el pedido
  está en `DELIVERED` o `CANCELLED` (estados finales).
- **`POST /orders/{id}/dispatch`** (`GESTOR_COMERCIAL`): valida `state == PENDING`, cambia a
  `DISPATCHED`, registra `dispatch_time` (hora de Bogotá). No valida que haya conductor
  asignado — decisión de negocio explícita del cliente (empresa).
- **`GET /orders/{id}/receipt`** (`GESTOR_COMERCIAL`): genera el
  comprobante PDF de despacho (`PdfService.generate_dispatch_receipt`, formato tirilla 80mm
  con alto dinámico según cantidad de items). Separado del endpoint de despacho para permitir
  **reimpresión** sin reejecutar la transición de estado — si el pedido no tiene
  `dispatch_time`, rechaza con 422 antes de intentar generar nada. Fechas y horas impresas
  en hora de Bogotá; si no hay conductor imprime "SIN ASIGNAR". No incluye la dirección de
  entrega (decisión explícita: el domiciliario no la necesita impresa).
- **`POST /orders/{id}/deliver`** (solo `GESTOR_COMERCIAL`): valida `state == DISPATCHED`,
  cambia a `DELIVERED`, registra `delivery_time` (hora de Bogotá). Decisión explícita: por
  ahora confirma la entrega el mismo usuario que gestiona el pedido; roadmap: que el propio
  domiciliario lo ejecute desde una futura app móvil (requeriría validar que el
  `id_user_vehicle` del pedido corresponda al usuario autenticado).
- **Sin `DELETE /orders/{id}`**: un pedido no se elimina; se cancelará con su propio endpoint.

### Concurrencia — bloqueo de fila en transiciones de estado

Las operaciones que **validan el estado del pedido y luego lo cambian** leen el pedido con
`OrderService.get_for_update()` (→ `BaseRepository.get_for_update()`, un
`SELECT ... FOR UPDATE` con `populate_existing=True`): `dispatch_order`, `deliver_order`,
`sync_items` y el `PATCH` de reasignación de conductor (`OrderService.update`).

La fila queda bloqueada hasta el `commit()`/`rollback()` de esa petición. Si llegan dos
peticiones sobre el mismo pedido, la segunda **espera** y luego valida contra el estado ya
actualizado; por ejemplo, dos `/dispatch` simultáneos dan un 200 y un 422 ("Solo se pueden
despachar pedidos en estado 'PENDING'"), nunca dos despachos.

Se bloquea solo la fila de `sale_order` (sin joins en la consulta del bloqueo). Los
detalles quedan protegidos porque toda escritura sobre ellos pasa por `sync_items`, que
bloquea primero el pedido.

---

## 11. Pruebas automatizadas

`pytest` + `TestClient` de FastAPI contra una **BD PostgreSQL de pruebas** (no SQLite: el
código usa `func.timezone`, `string_agg`, `to_char` y `FOR UPDATE`, propios de Postgres).
Cómo ejecutarlas: ver `README.md`.

- **`tests/conftest.py`**: exige `TEST_DATABASE_URL` (y que el nombre de la BD contenga
  `test`), la inyecta como `DATABASE_URL` antes de importar `app`, aplica
  `alembic upgrade head` al iniciar la suite y crea los datos base de cada test.
- **Aislamiento:** cada test abre una transacción externa y usa una `Session` con
  `join_transaction_mode="create_savepoint"`; los `commit()` de los services solo liberan
  un SAVEPOINT y todo se revierte al final del test. Los overrides de `get_db` replican el
  `rollback()` ante error del `get_db` real.
- **Autenticación:** `get_current_user` se reemplaza por un usuario `GESTOR_COMERCIAL`;
  los flujos se prueban sin pasar por JWT.
- **Fixtures** (`conftest.py`): `db`, `data` (zona, barrio, 3 productos, cliente registrado,
  gestor y conductor con código `99`), `client` (GESTOR), `admin` (ADMINISTRADOR),
  `create_order`, `writer` (`FakeSheetsWriter`) y `default_seller` (vendedor por defecto
  `09`, con `DEFAULT_SELLER_CODE` parcheado).
- **Cobertura:** registro de pedidos (cliente nuevo/existente, totales, productos
  repetidos o inexistentes), máquina de estados (dispatch/deliver), `PATCH` de conductor,
  `sync_items`, detalle y PDF sin conductor, dashboards por estado, día y hora de Bogotá,
  endpoints retirados (`DELETE /orders`, escritura en `/orders_details`) y
  `BaseRepository.update` sobre objetos expirados, rutas y pedidos por ruta, consecutivo
  diario, filtros por rango de fechas, histórico, archivado (exportación, verificación y
  purga) y cierre (resumen, Excel, reexportación y bloqueo de la purga) — incluye la
  regresión de cada bug corregido.

---

## 12. Pendientes / Roadmap

- **Plantilla definitiva de Siigo**: el Excel del cierre usa un formato provisional; ajustar
  `closure_export.py` cuando Siigo defina columnas y códigos.
- **Cancelación de pedido**: no existe aún un endpoint `CANCELLED` explícito con sus propias
  reglas de transición.
- **Refresh token en cookie `httpOnly`**: Cookie `httpOnly` + `Secure`, configurar CORS 
  con `allow_credentials=True` y orígenes explícitos, decidir `SameSite` según si frontend/backend 
  comparten dominio (detalle en el `README.md`). En esa configuración de CORS, exponer `Content-Disposition` (`expose_headers`) para que el frontend lea el nombre de los archivos descargados (Excel del cierre, PDF).
- **Unificar formato de error 422 de Pydantic** con el formato uniforme de `BusinessError`
  (o resolverlo del lado del frontend con un segundo handler).
- **Rol de domiciliario operando sus propios pedidos** (marcar entrega desde app móvil).
- **Validación y auditoría de `unit_price`** frente a `effective_price`.

---

## 13. Estándares para nuevas funcionalidades

1. Un archivo por entidad en `models/`, `schemas/`, `repositories/`, `services/`,
   `api/routers/`, agrupado por el mismo módulo de dominio
   (`securityModule` / `coreModule` / `parametersModule`). Lo transversal (no-entidad) va
   fuera de esa agrupación, en su propia carpeta temática.
2. Toda FK: columna `ForeignKey` + `relationship` con `back_populates` verificado en ambos
   lados + referencia cruzada dentro de `if TYPE_CHECKING:`.
3. Dinero → `Numeric(12, 2)` / `Decimal`. Nunca `Float`.
4. Timestamps de auditoría → `server_default=func.now()` + `DateTime(timezone=True)`.
   Horas de eventos de negocio → `Time`, sin default, asignadas explícitamente en el
   service usando `BOGOTA_TZ`. Todo cálculo de "hoy"/"ahora" o de fecha local en SQL pasa
   por `app/core/timezone.py` (ver tabla en sección 4).
5. Enums nuevos → en `app/utils/enums/`. De texto → `Enum(EnumClass, native_enum=False,
   values_callable=...)`. Numéricos → `IntEnumType(EnumClass)`.
6. Cada nueva entidad se agrega a su `__init__.py` de módulo en `models/` (y, si necesita
   datos iniciales, a `SEEDS` en `app/db/seeds/registry.py` respetando el orden).
7. Schemas: patrón `Base → Create → Update (@partial_model o explícito si hay que
   restringir campos editables) → Response`, excluyendo de `Create` cualquier campo con
   `server_default` o valor inicial fijo. Texto que se normaliza → `UpperText`/`LowerText`
   en **todos** los schemas de entrada que lo reciban.
8. Antes de aplicar una migración autogenerada: revisarla siempre. Tipos personalizados
   requieren que `render_item` en `env.py` los conozca; cambios de tipo de columna pueden
   requerir `postgresql_using` o el patrón columna-temporal. Las migraciones importan
   enums y tipos desde `app/utils/enums` o `app/db/custom_types`, **nunca desde
   `app/models`**: los modelos cambian y una migración vieja debe seguir cargando tal como
   se escribió (Alembic carga todos los archivos de `versions/` en cada comando).
9. Cualquier operación que toque más de una tabla en una sola unidad de negocio (como el
   registro de pedido) usa `repository.add()` (flush, no commit) en cada paso, con un único
   `db.commit()` al final del método de service — nunca el `create()`/`update()` genérico
   de `BaseRepository` para este tipo de operación compuesta.
10. Todo router nuevo hereda de `SecuredRouter`; todo endpoint nuevo nace restringido a
    `ADMINISTRADOR` por defecto — se abre explícitamente con `roles=[...]` según la regla de
    negocio real. No exponer `DELETE` en entidades sin `active` ni regla de borrado clara.
11. Toda operación que valide el estado actual de un registro antes de cambiarlo (máquina
    de estados, sincronizaciones) lo lee con `get_for_update()` en el service, no con
    `get()`.
12. Rutas literales (`/catalog`, `/search`, `/dashboard-summary`, `/history`, `/summary`)
    siempre declaradas antes que rutas con parámetro de posición equivalente (`/{id}`) en el mismo archivo de router
    — el *routing* de FastAPI/Starlette evalúa en orden y se queda con la primera
    coincidencia.
13. Todo flujo nuevo o bug corregido llega con su test en `tests/` (los bugs, como
    regresión que reproduce el caso que fallaba).
14. Filtros por fecha sobre `TIMESTAMPTZ` → helpers de `repositories/time_filters.py`
    (rango de instantes), nunca funciones aplicadas a la columna en el `WHERE`.
15. Servicios externos (Google Sheets) detrás de un `Protocol` inyectado con `Depends`,
    para reemplazarlos en los tests; sus fallas se traducen a `ExternalServiceError` (502).
16. Operaciones que no deben correr dos a la vez sobre el mismo recurso global (archivado)
    → `pg_advisory_xact_lock`; sobre una fila → `get_for_update()`.
