from fastapi import HTTPException, status


class NotFoundError(Exception):
    """Raised when a requested entity does not exist."""


def raise_not_found(entity_name: str) -> None:
    """Raise a consistent 404 response."""

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{entity_name} not found.",
    )
