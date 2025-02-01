# Self-Hosting


## Running via docker-compose

1. Clone this repository (or just copy the docker-compose.yml file)
2. Copy the `.env.example` file to `.env` and fill in the required environment variables
    - **TODO** link to docs configuration page for all env vars and what they do
    - If not using the email server, set `SMTP_LOCAL_DEV=true` to prevent sending emails.
      They will be printed to the console instead.

3. Run `docker compose up` to start the application
4. Access the application at <http://localhost:8000>
