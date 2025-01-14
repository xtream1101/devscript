# Snippet Manager


## Features

- Quick lookup of saved code snippets
- Run scripts on the cli. (See [CLI Usage](#cli-usage) below)
- Fork a snippet into your private collection
- Tag snippets for quick lookups and grouping
- No commenting on snippets, this is not a social platform, but a tool to store and run code snippets.


## Development


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


## CLI Usage

Run your snippet on the command line. This is useful so you do not have to deploy or update the snippet on each
system you want to run it on. I find this most useful when I have a commly used command to run on a remote server.

For security reasons, you can only run snippets that you have created.
This is to prevent someone editing a snippet to run malicious code as only you can edit your own snippets.

Here are some examples of how to run a snippet directly from the command line:

```bash
# Bash script example
bash <(curl -s curl -H "X-API-Key: your_api_key_here" \
http://localhost:8000/api/snippets/command/testA)

# Python script example
wget -qO- --header "X-API-Key: your_api_key_here" \
http://localhost:8000/api/snippets/command/py-a  | python -
```

If you find yourself running snippets often, you can create a bash function to make it easier to run snippets.

Update the `command_map` to include the command to run the snippet for each language you want to support.
The script will be "piped" into that command. So for most commands, you just need to add a `-` to the end of the
command like in the examples below.

```bash
function smc(){
    declare -A command_map
    # bash is supported by default
    # Update to use the expected command for each language on your system
    command_map["python"]="python -"
    command_map["javascript"]="node -"

    # This can be declared anywhere you normally handle your env vars. But its fine to keep here too.
    SM_API_KEY="YOUR_API_KEY_HERE"

    # Get the language of the snippet
    snippetLang=$(curl -I -s -o /dev/null -w '%header{X-Snippet-Lang}' -H "X-API-Key: ${SM_API_KEY}" http://localhost:8000/api/snippets/command/${1})
    # Check if snippetLang was found in command_map, or its "bash"
    if [ -z ${command_map["$snippetLang"]} ] && [ "$snippetLang" != "bash" ]; then
        echo "Error: Unsupported language '$snippetLang'"
        return 1
    fi

    # Fetch the plain text content of the snippet
    script=$(curl -s curl -H "X-API-Key: ${SM_API_KEY}" http://localhost:8000/api/snippets/command/${1})

    if [[ "$snippetLang" == "bash" ]]; then
        bash -c "$script" ${@}
    else
        echo "$script" | eval ${command_map["$snippetLang"]} ${@:2}
    fi
    }
```

Now you can run a snippet with the following command:

```bash
smc testA arg1 arg2
```
