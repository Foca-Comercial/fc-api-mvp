import enum


class DeletionType(str, enum.Enum):
    SOFT = "SOFT"
    HARD = "HARD"
