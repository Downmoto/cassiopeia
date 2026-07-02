from cassiopeia.storage import (
    ConstraintViolationError,
    NotFoundError,
    RetryableWriteConflictError,
    RetryPolicy,
    SchemaError,
    StorageConnectionError,
    StorageError,
    retry_storage_write,
)
from cassiopeia.storage.ports import Repository


def test_storage_package_exports_initial_boundary() -> None:
    assert issubclass(StorageConnectionError, StorageError)
    assert issubclass(SchemaError, StorageError)
    assert issubclass(NotFoundError, StorageError)
    assert issubclass(ConstraintViolationError, StorageError)
    assert issubclass(RetryableWriteConflictError, StorageError)
    assert RetryPolicy().max_attempts == 3
    assert retry_storage_write is not None
    assert Repository is not None
