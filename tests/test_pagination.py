"""Paginación en el servidor: helper `paginate` y schema genérico `Page`."""

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.models.coreModule.product import Product
from app.repositories.pagination import count_rows, paginate
from app.schemas.common.page_schema import Page, PageParams

TEST_CODES = ("Z91", "Z92", "Z93")  # productos del fixture `data`


def _products_stmt():
    return (
        select(Product)
        .where(Product.code.in_(TEST_CODES))
        .order_by(Product.code, Product.id_product)
    )


class _ProductRow(BaseModel):
    code: str
    name: str

    model_config = ConfigDict(from_attributes=True)


def test_page_params_calcula_el_offset():
    assert PageParams().offset == 0
    assert PageParams(page=3, page_size=25).offset == 50


def test_paginate_devuelve_la_pagina_y_el_total(db, data):
    first, total = paginate(db, _products_stmt(), PageParams(1, 2), scalars=True)
    second, _ = paginate(db, _products_stmt(), PageParams(2, 2), scalars=True)

    assert total == 3
    assert [p.code for p in first] == ["Z91", "Z92"]
    assert [p.code for p in second] == ["Z93"]


def test_paginate_mas_alla_del_final_trae_vacio_con_el_total(db, data):
    rows, total = paginate(db, _products_stmt(), PageParams(5, 2), scalars=True)

    assert rows == []
    assert total == 3


def test_paginate_sin_resultados(db, data):
    stmt = select(Product).where(Product.code == "NOPE").order_by(Product.id_product)

    rows, total = paginate(db, stmt, PageParams())

    assert (rows, total) == ([], 0)


def test_paginate_filas_con_columnas(db, data):
    stmt = (
        select(Product.code, Product.name)
        .where(Product.code.in_(TEST_CODES))
        .order_by(Product.code)
    )

    rows, total = paginate(db, stmt, PageParams(1, 10))

    assert total == 3
    assert rows[0].code == "Z91"
    assert rows[0].name == "BOLSA HIELO 2KG"


def test_paginate_con_conteo_liviano(db, data):
    count_stmt = select(Product.id_product).where(Product.code.in_(TEST_CODES))

    rows, total = paginate(
        db, _products_stmt(), PageParams(1, 1), scalars=True, count_stmt=count_stmt
    )

    assert total == 3
    assert len(rows) == 1


def test_count_rows_ignora_el_orden(db, data):
    assert count_rows(db, _products_stmt()) == 3


def test_page_build_calcula_paginas(db, data):
    params = PageParams(page=1, page_size=2)
    rows, total = paginate(db, _products_stmt(), params, scalars=True)

    page = Page[_ProductRow].build(
        [_ProductRow.model_validate(r) for r in rows], total=total, params=params
    )

    assert page.model_dump() == {
        "page": 1,
        "page_size": 2,
        "total": 3,
        "pages": 2,
        "items": [
            {"code": "Z91", "name": "BOLSA HIELO 2KG"},
            {"code": "Z92", "name": "BOLSA HIELO 5KG"},
        ],
    }


def test_page_vacia_tiene_cero_paginas():
    page = Page[_ProductRow].build([], total=0, params=PageParams())

    assert page.pages == 0
    assert page.items == []

