import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pytest-docker-postgres",
    version="0.0.8",
    author="Gastromatic",
    author_email="mjboamail@gmail.com",
    description="Pytest fixtures for postgres in docker",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gastromatic/pytest-docker-postgres",
    packages=setuptools.find_packages(),
    package_data={"pytest_docker_postgres": ["*.yml"]},
    python_requires=">=3.5",
    # These may be too strict, feel free to make a PR and change them
    install_requires=[
        "pytest>=5.0",
        "lovely-pytest-docker>=0.0.5",
        "sqlalchemy>=1.3.6",
        "sqlalchemy-utils>=0.34.1",
    ],
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Development Status :: 4 - Beta",
        "Operating System :: OS Independent",
    ],
    keywords="postgres pytest docker database",
    entry_points={"pytest11": ["docker_postgres = pytest_docker_postgres"]},
)
