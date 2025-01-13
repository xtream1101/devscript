# Vars
db_name := "snippet-manager-db"
project_dir := justfile_dir()

# Start all Servers
start:
    @echo "Starting all servers"
    just --justfile {{ justfile() }} db-start
    just --justfile {{ justfile() }} docs-start &
    just --justfile {{ justfile() }} server-start

# Run fast api dev server
server-start:
    @cd "{{ project_dir }}"; alembic upgrade head
    @cd "{{ project_dir }}"; uv run fastapi dev app/app.py

# Clear db and start all services
fresh-start:
    @echo "Clearing database and starting all servers"
    just --justfile {{ justfile() }} db-stop
    just --justfile {{ justfile() }} start

# Start the mkdocs server
docs-start:
    @cd "{{ project_dir }}"; mkdocs serve -a 0.0.0.0:8080

# Start the postgres db
db-start:
    @echo "Starting database"
    # TODO: Better way to check if the container is already running
    docker run --name {{ db_name }} -e POSTGRES_PASSWORD=postgres -d -p 5432:5432 postgres || true

# Stop the postgres db
db-stop:
    @echo "Stopping database"
    docker stop {{ db_name }} || true
    docker rm {{ db_name }} || true

# Npm watch styles
npm-watch:
    @cd "{{ project_dir }}"; npm run watch-styles
