"""Input validation utilities."""


def validate_positive_float(value, name: str) -> float:
    try:
        v = float(value)
        if v <= 0:
            raise ValueError(f"{name} must be positive")
        return v
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a positive number")


def validate_float(value, name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number")


def validate_non_empty_string(value, name: str) -> str:
    if not value or not str(value).strip():
        raise ValueError(f"{name} cannot be empty")
    return str(value).strip()


def validate_coordinates(x, y) -> tuple:
    x_val = validate_float(x, "X coordinate")
    y_val = validate_float(y, "Y coordinate")
    return x_val, y_val
