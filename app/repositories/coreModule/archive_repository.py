from datetime import date
from typing import Any

from sqlalchemy import Date, case, cast, delete, exists, func, select
from sqlalchemy.orm import Session

from app.models.coreModule.archive_spreadsheet import ArchiveSpreadsheet
from app.models.coreModule.client import Client
from app.models.coreModule.daily_order_counter import DailyOrderCounter
from app.models.coreModule.monthly_archive import MonthlyArchive
from app.models.coreModule.order import Order
from app.models.securityModule.user_session import UserSession
from app.utils.enums.order_state import OrderState


class RepositoryArchiveSpreadsheet:
    def get(self, db: Session, year: int) -> ArchiveSpreadsheet | None:
        return db.get(ArchiveSpreadsheet, year)

    def get_all(self, db: Session) -> list[ArchiveSpreadsheet]:
        stmt = select(ArchiveSpreadsheet).order_by(ArchiveSpreadsheet.year.desc())
        return list(db.scalars(stmt).all())

    def upsert(
        self, db: Session, *, year: int, spreadsheet_id: str
    ) -> ArchiveSpreadsheet:
        row = self.get(db, year)
        if row is None:
            row = ArchiveSpreadsheet(year=year, spreadsheet_id=spreadsheet_id)
            db.add(row)
        else:
            row.spreadsheet_id = spreadsheet_id
        db.flush()
        return row


class RepositoryMonthlyArchive:
    def get(self, db: Session, archive_month) -> MonthlyArchive | None:
        return db.get(MonthlyArchive, archive_month)

    def get_all(self, db: Session) -> list[MonthlyArchive]:
        stmt = select(MonthlyArchive).order_by(MonthlyArchive.archive_month.desc())
        return list(db.scalars(stmt).all())

    def save_export(
        self, db: Session, *, archive_month: date, **values
    ) -> MonthlyArchive:
        """Crea o actualiza la fila del mes con los datos de la última exportación."""
        row = self.get(db, archive_month)
        if row is None:
            row = MonthlyArchive(archive_month=archive_month, **values)
            db.add(row)
        else:
            for field, value in values.items():
                setattr(row, field, value)
        db.flush()
        return row


class RepositoryArchiveOverview:
    def get_order_months(self, db: Session, *, before: date) -> list[Any]:
        """Pedidos por mes de entrega (delivery_date < `before`): mes (primer día),
        cantidad y ventas sin cancelados. La BD retiene pocos meses, así que
        agrupar es barato."""
        month = cast(func.date_trunc("month", Order.delivery_date), Date)
        sales = func.coalesce(
            func.sum(
                case(
                    (Order.state != OrderState.CANCELLED, Order.order_total), else_=0
                )
            ),
            0,
        )
        stmt = (
            select(
                month.label("month"),
                func.count(Order.id_order).label("orders_count"),
                sales.label("total_sales"),
            )
            .where(Order.delivery_date < before)
            .group_by("month")
        )
        return list(db.execute(stmt).all())


class RepositoryPurge:
    """Borrados masivos del archivado. Sin commit: los confirma el servicio."""

    def delete_orders(self, db: Session, order_ids: list[int]) -> int:
        # Los detalles se borran por ON DELETE CASCADE (order_detail.id_order)
        if not order_ids:
            return 0
        result = db.execute(
            delete(Order)
            .where(Order.id_order.in_(order_ids))
            .execution_options(synchronize_session=False)
        )
        return result.rowcount  # type: ignore

    def delete_orphan_temporary_clients(self, db: Session) -> int:
        """Clientes temporales (is_registered=False) que ya no tienen pedidos."""
        has_orders = exists().where(Order.id_client == Client.id_client)
        result = db.execute(
            delete(Client)
            .where(Client.is_registered.is_(False), ~has_orders)
            .execution_options(synchronize_session=False)
        )
        return result.rowcount  # type: ignore

    def delete_counters_before(self, db: Session, day: date) -> int:
        result = db.execute(
            delete(DailyOrderCounter)
            .where(DailyOrderCounter.counter_date < day)
            .execution_options(synchronize_session=False)
        )
        return result.rowcount  # type: ignore

    def delete_expired_sessions(self, db: Session) -> int:
        """Sesiones vencidas. Las revocadas que aún no vencen se conservan: sirven
        para detectar la reutilización de un refresh token robado."""
        result = db.execute(
            delete(UserSession)
            .where(UserSession.expires_at < func.now())
            .execution_options(synchronize_session=False)
        )
        return result.rowcount  # type: ignore


purge_repository = RepositoryPurge()
archive_overview_repository = RepositoryArchiveOverview()


# Clave fija del bloqueo de archivado: dos exportaciones/purgas no corren a la vez
ARCHIVE_LOCK_KEY = 7_401_202_601


def lock_archive(db: Session) -> None:
    """Bloqueo exclusivo hasta el fin de la transacción (pg_advisory_xact_lock)."""
    db.execute(select(func.pg_advisory_xact_lock(ARCHIVE_LOCK_KEY)))


archive_spreadsheet_repository = RepositoryArchiveSpreadsheet()
monthly_archive_repository = RepositoryMonthlyArchive()
