from typing import Annotated

from pydantic import StringConstraints

# El strip y el cambio de caja ocurren ANTES de validar min/max_length,
# así que "   " se rechaza como vacío.
UpperText = Annotated[
    str, StringConstraints(strip_whitespace=True, to_upper=True, min_length=1)
]
LowerText = Annotated[
    str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=1)
]
