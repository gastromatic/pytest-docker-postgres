import glob
import os
import filecmp
from typing import List, Set

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
    parser.addoption(
        "--load-sql",
        action="append",
        default=[],
        help="Path to load a database from a folder containing sql files",
    )
    parser.addoption(
        "--current-schema",
        help="Path to initialize a schema for comparison with --next-schema",
    )
    parser.addoption(
        "--next-schema",
        help="Path to initialize a schema for comparison with --current-schema",
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


def sql_from_folder_iter(path: str) -> List[str]:
    if not os.path.isdir(path):
        raise ValueError(f"Expected existing directory at {path}")
    sql_files = sorted(glob.glob(os.path.join(path, "**/*.sql"), recursive=True))
    if len(sql_files) == 0:
        raise ValueError(f"Expected at least one sql file in {path}")
    return sql_files


@pytest.fixture(scope="function")
def db_engine_load_sql(db_engine, request):
    sql_files = request.param
    with db_engine.connect() as conn:
        with conn.begin():
            for file_path in sql_files:
                with open(file_path) as file:
                    conn.connection.cursor().execute(file.read())
    yield db_engine


def get_diff(a: str, b: str) -> Set[str]:
    diffs = set()

    def sub_cmp(c: filecmp.dircmp):
        diffs.update(c.diff_files)
        for sub_c in c.subdirs.values():
            sub_cmp(sub_c)

    sub_cmp(filecmp.dircmp(a, b))
    diffs = {path for path in diffs if os.path.basename(path).endswith(".sql")}
    return diffs


def pytest_generate_tests(metafunc):
    if db_engine_load_sql.__name__ in metafunc.fixturenames:
        static_schema_paths = metafunc.config.getoption("--load-sql")
        if static_schema_paths:
            schema_paths = static_schema_paths
        else:
            current_schema = metafunc.config.getoption("--current-schema")
            next_schema = metafunc.config.getoption("--next-schema")
            schema_paths = [current_schema]
            if next_schema:
                if get_diff(current_schema, next_schema):
                    schema_paths.append(next_schema)
        sql_folder_iters = [sql_from_folder_iter(path) for path in schema_paths]
        metafunc.parametrize(
            db_engine_load_sql.__name__,
            [i for i in sql_folder_iters if len(i) > 0],
            indirect=True,
        )
