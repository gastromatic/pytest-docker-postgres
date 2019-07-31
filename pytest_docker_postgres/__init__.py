import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy_utils.functions import create_database, drop_database


# We can either be on the host or in the docker-compose network
def pytest_addoption(parser):
    parser.addoption(
        "--in-docker-compose",
        action="store",
        default="",
        help="Assume inside a docker network",
    )


@pytest.fixture(scope="session")
def in_docker_compose(request):
    return request.config.getoption("--in-docker-compose")


@pytest.fixture(scope="session")
def docker_compose_files(in_docker_compose, pytestconfig):
    dc_type = f".{in_docker_compose}" if in_docker_compose else ""

    dc_file = f"docker-compose{dc_type}.yml"
    return [os.path.join(os.path.dirname(__file__), dc_file)]


def make_url(host: str, port: int, database: str) -> URL:
    return URL(
        "postgresql+psycopg2",
        username="postgres",
        host=host,
        port=port,
        database=database,
    )


def wait_for_db(host: str, port: int) -> bool:
    url = make_url(host=host, port=port, database="")
    engine = create_engine(url)
    try:
        engine.connect()
        return True
    except Exception:
        return False


@pytest.fixture(scope="function")
def db_engine(in_docker_compose, docker_services):
    docker_services.start("db")
    if in_docker_compose:
        port = 5432
        # Ugly but lovely-pytest-docker throws unnecessary exceptions
        docker_services.wait_until_responsive(
            timeout=30.0, pause=0.1, check=lambda: wait_for_db("db", port)
        )
    else:
        port = docker_services.wait_for_service("db", 5432, check_server=wait_for_db)
    host = "localhost" if not in_docker_compose else "db"
    url = make_url(host=host, port=port, database="test")
    create_database(url)
    yield create_engine(url)
    drop_database(url)
