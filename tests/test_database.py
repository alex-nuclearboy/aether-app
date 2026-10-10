"""Integration tests for the configured database backend."""

import pytest
from django.db import connection


@pytest.mark.django_db
def test_database_backend_is_postgresql() -> None:
    """Use PostgreSQL as the Django test database backend."""
    assert connection.vendor == "postgresql"


@pytest.mark.django_db
def test_database_connection_executes_query() -> None:
    """Execute a query through the configured PostgreSQL connection."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        result = cursor.fetchone()

    assert result == (1,)
