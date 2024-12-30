# Snippet Manager


## Features

- Quick lookup of saved code snippets
- Run scripts on the cli.

    ```bash
    # Bash script example
    bash <(curl -s curl -H "X-API-Key: your_api_key_here" \
    http://localhost:8000/api/snippets/command/testA)

    # Python script example
    wget -qO- --header "X-API-Key: your_api_key_here" \
    http://localhost:8000/api/snippets/command/py-a  | python -
    ```

- Fork a snippet into your private collection
- Tag snippets for quick lookups and grouping
- No commenting on snippets, this is not a social platform, but a tool to store and run code snippets.


## Development


### TODO's

- Add versioning to snippets???
- Add search functionality to snippets
- Add username to user accounts that can be shown on snippets
- Create a bash alias for the curl command to make it easier to run snippets to put in the readme
    - Is there a way to know how to run the script returned? (bash, python, etc...)
- Ability to star/favorite a snippet (both public and private)
- Add SSO
    - Add self-hosted OIDC
    - Add Github
    - Add Google


### Setup

1. Install tools:
    - Install [uv](https://docs.astral.sh/uv/getting-started/installation/) to manage the python environment.
    - Install [pre-commit](https://pre-commit.com/) hooks:

        ```bash
        pre-commit install
        ```

2. Install dependencies:

    ```bash
    uv sync
    ```

3. Set up the database:

    ```bash
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
    uv run fastapi dev app/app.py
    ```
