# Local Development


## Setup

1. Install tools:
    - Install [uv](https://docs.astral.sh/uv/getting-started/installation/) to manage the python environment.
    - Install [just](https://github.com/casey/just), this will make running common dev commands eaiser
        - To use some of the `just` commands, [docker](https://docs.docker.com/engine/install/) is required

2. Install dependencies:
    - Create a virtual environment:

        ```bash
        uv sync
        ```

    - Run pre-commit Install [pre-commit](https://pre-commit.com/) hooks:

        ```bash
        pre-commit install
        ```


3. Set up the database:

```bash
# Start the local postgres db
just db-start

# Create and upgrade the database to the latest migration
alembic upgrade head

# For future database changes:
# Create a new migration after modifying models
alembic revision --autogenerate -m "Description of changes"

# Apply the new migration
alembic upgrade head
```

4. Run the development server:

    ```bash
    just server-start
    ```

5. Access to the web interface at [http://localhost:8000](http://localhost:8000)

6. [Optional] Run the command to automatically process the css files w/ tailwindcss:

    ```bash
    just npm-watch
    ```

7. [Optional] check out the available `just` commands:

    ```bash
    just --list
    ```


## Alebmic Commands

- If you need to undo a migration, you can use the following commands:

    ```bash
    alembic downgrade -1
    ```

    Then you can manually delete the migration file from the `alembic/versions` directory.

- If you need to merge two heads, you can use the following command:

    ```bash
    alembic merge heads
    ```

    This will create a blank version file that combines the two heads. Nothing to do except now you can updated your db
