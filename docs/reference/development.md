
# 🛠️ Development


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

4. Setup Env vars

    - Option #1: Local `.env` file
        - `.env.example` contains all the env vars that can be set. The default value is listed there as well.
        - Create a file called `.env` and override any settings you wish to change
        - I would recommend at least setting `SMTP_LOCAL_DEV=true` to prevent sending emails during development

    - Option #2: Using [Infisical](https://infisical.com/) to manage secrets
        - Install the [infisical-cli](https://infisical.com/docs/cli/overview) tool
        - Run `infisical init` to setup the project

5. Run the development server:

    ```bash
    # If you have infisical setup it will run the correct commands
    just server-start
    ```

6. Access to the web interface at [http://localhost:8000](http://localhost:8000)

7. [Optional] Run the command to automatically process the css files w/ tailwindcss:

    ```bash
    just npm-watch
    ```

8. [Optional] check out the available `just` commands:

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

---
