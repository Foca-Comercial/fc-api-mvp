"""BaseRepository.update: actualización parcial sobre objetos expirados."""

from decimal import Decimal

import pytest
from sqlalchemy import inspect as sa_inspect

from app.repositories.coreModule.product_repository import product_repository
from app.schemas.coreModule.product_schema import ProductUpdate


def test_update_aplica_campos_en_objeto_expirado(db, data):
    """Regresión: tras un commit el objeto queda expirado y su __dict__ no trae
    las columnas; la versión anterior ignoraba los campos en silencio."""
    product = data.products[0]
    db.commit()  # expira todos los objetos de la sesión
    assert "name" in sa_inspect(product).expired_attributes

    product_repository.update(
        db,
        db_obj=product,
        obj_in=ProductUpdate(name="hielo premium"),  # type: ignore
    )

    db.expire_all()
    assert product.name == "HIELO PREMIUM"


def test_update_parcial_solo_toca_lo_enviado(db, data):
    product = data.products[1]
    original_price = product.base_price
    original_code = product.code

    product_repository.update(db, db_obj=product, obj_in=ProductUpdate(active=False))  # type: ignore

    db.expire_all()
    assert product.active is False
    assert product.base_price == original_price
    assert product.code == original_code


def test_update_con_dict_como_el_soft_delete(db, data):
    product = data.products[2]
    db.commit()

    product_repository.update(db, db_obj=product, obj_in={"active": False})

    db.expire_all()
    assert product.active is False


def test_update_rechaza_campos_que_no_son_columnas(db, data):
    product = data.products[0]
    price_before = product.base_price

    with pytest.raises(ValueError, match="no_existe"):
        product_repository.update(
            db, db_obj=product, obj_in={"base_price": Decimal("1.00"), "no_existe": 1}
        )

    db.expire_all()
    assert product.base_price == price_before  # no se aplicó nada
