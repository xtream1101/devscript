<div align="center">
  <p align="center">
    <a href="#">
      <img src="app/static/images/brand/dark/wordmark.svg" alt="Snippet Manager Wordmark" width="369" height="64">
    </a>
  </p>
</div>

<div>
  <h2 align="center">Self-hosted snippet manager</h2>
</div>


## Project Overview

This was built to be your own private snippet and script management tool.

Use for free at [devscript.host](https://devscript.host)  
or self-host it yourself using the [Quick Start Guide](#-quick-start-guide)

Additional documentation can be found at [docs.devscript.host](https://docs.devscript.host)

---


## 📦 Features

- Supports SSO logins
- Advanced search capabilities
- Tagging system
- Syntax highlighting
- Sharing and exploring snippets that are public
- Favorite snippets
- Fork a public snippet to make it your own
- Run your own snippet on the command line (TODO: link to docs on how to set this up)

---


## 🚀 Quick Start Guide


### Running via docker-compose

1. Clone this repository
2. Copy the `.env.example` file to `.env` and fill in the required environment variables
    - **TODO** link to docs configuration page for all env vars and what they do
    - If not using the email server, set `SMTP_LOCAL_DEV=true` to prevent sending emails.
      They will be printed to the console instead.

3. Run `docker compose up` to start the application
4. Access the application at <http://localhost:8000>

---


## 🧰 Development


### Setup

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


### Alebmic Commands

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


## 📝 Upcoming features

- Be able to disable registration, and have it be invite only
- Have the email (smtp) server as an optional setup
- Possiable vscode extention to add and view snippets directly in vscode


## 💬 Report a Bug or Feature Request

If you encounter any issues or have suggestions for improvements, file a new issue on our [GitHub issues page](https://github.com/xtream1101/devscript/issues).

If you find a security vulnerability, please do not create an issue. Instead, contact the maintainers directly at [security@devscript.host](mailto:security@devscript.host)


## 📜 License

This project is licensed under the [GPLv3](LICENSE).
