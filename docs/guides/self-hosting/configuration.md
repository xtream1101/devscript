
# Configuration


## Environment Variables

These are the environment variables that can be set to configure the application.  
The defauls are shown as well as a short description of what they do.


### Core Settings


#### HOST

This is the domain name that you want tot access the application from.
This is used for generating links in emails and other places.  

If you are using a reverse proxy, this should be the domain name configured in the reverse proxy.

```bash
HOST="http://localhost:8000"
```

---


#### DOCS_HOST

This is the domain name that you want to access the documentation site from.  

If you are using a reverse proxy, this should be the domain name configured in the reverse proxy.

```bash
DOCS_HOST="http://localhost:8080"
```

---


#### SECRET_KEY

This is the secret key used by the app. This should be a long random string.  

**Change this in production!**

```bash
SECRET_KEY="your-secure-secret-key-here"
```

---


#### DISABLE_REGISTRATION

This is a boolean value that will disable registration on the site if set to `true`.

```bash
DISABLE_REGISTRATION=false
```

---


#### CORS_ORIGINS

This is a list of origins that are allowed to access the backend. Normally set to the `HOST` and `DOCS_HOST` values.  

> Must not end in a trailing slash

```bash
CORS_ORIGINS='["http://localhost:8000", "http://localhost:8080"]'
```

---


#### SUPPORT_EMAIL

This is the email address that will be used for support emails. This is a mailto link in the footer of the site.

```bash
SUPPORT_EMAIL=support@example.com
```

---


#### DEFAULT_CODE_THEME_LIGHT

This is the default code theme that will be used for syntax highlighting when in light mode.  
Users can overide their own default in their account settings.  

```bash
DEFAULT_CODE_THEME_LIGHT="atom-one-light"
```

---


#### DEFAULT_CODE_THEME_DARK

This is the default code theme that will be used for syntax highlighting when in dark mode.  
Users can overide their own default in their account settings.  

```bash
DEFAULT_CODE_THEME_DARK="atom-one-dark"
```

---


#### VALIDATION_LINK_EXPIRATION

This is the time in seconds that a validation link will be valid for.
This is used for account email verification links.

```bash
VALIDATION_LINK_EXPIRATION=900  # 15 minutes in seconds
```

---


#### PASSWORD_RESET_LINK_EXPIRATION

This is the time in seconds that a password reset link will be valid for.

```bash
PASSWORD_RESET_LINK_EXPIRATION=900  # 15 minutes in seconds
```

---


#### COOKIE_NAME

This is the name of the cookie that is used for the login auth sessions.

```bash
COOKIE_NAME="devscriptauth"
```

---


#### COOKIE_MAX_AGE

This is the time in seconds that the auth cookie will be valid for.

```bash
COOKIE_MAX_AGE=2592000  # 30 days in seconds
```

---


### Database Settings

These are the settings for the database connection. This app expects a PostgreSQL database.

```bash
DATABASE_USER="postgres"
DATABASE_PASSWORD="postgres"
DATABASE_HOST="db"
DATABASE_PORT=5432
DATABASE_NAME="postgres"
```

---


### Email

Email setup is optional, on registration all accounts are auto verified if email is disabled
and there is no forgot password flow.

```bash
# This will disable sending emails in development and output in the terminal instead
# To use this locally, just fill in fake values for the SMTP settings
SMTP_LOCAL_DEV=false

SMTP_HOST="smtp.example.com"
SMTP_PORT=587
SMTP_USER="hello@example.com"
SMTP_PASSWORD="your-password"
SMTP_STARTTLS=false
SMTP_SSL=false
SMTP_FROM="no-reply@example.com"
SMTP_FROM_NAME="devscript Snippet Manager"
# Enables debug output for sending the email
SMTP_DEBUG=false
```

---


### Logging & Monitoring


#### ENV

This is the environment that the application is running in.  
Currently only used if you have sentry enabled.  

Valid options are `dev`, `staging`, and `prod`.

```bash
ENV="dev"
```

---


#### LOGURU_LEVEL

Using [loguru](https://github.com/Delgan/loguru) for logging.  This value sets the log level for the application.  
You can find other configuration value thats can be set as env vars in the [loguru docs](https://loguru.readthedocs.io/en/stable/api/logger.html#loguru._logger.Logger).  
The values are prefixed with `LOGURU_`, and are all uppercase.

```bash
LOGURU_LEVEL="INFO"
```

---


#### SENTRY_DSN

Default this is disabled, but set the DSN value for any sentry compatible service to enable error tracking.

```bash
SENTRY_DSN=""
```

---


#### PLAUSIBLE_SITE_NAME

This site enables anylytics tracking with [Plausible](https://plausible.io/),
which is open source and can be self-hosted.  
This is the name of the site that is configured in Plausible.  
This is used for the main devscript app.

```bash
PLAUSIBLE_SITE_NAME=""
```

---


#### PLAUSIBLE_SCRIPT_URL

This site enables anylytics tracking with [Plausible](https://plausible.io/),
which is open source and can be self-hosted.  
This is the URL of the Plausible script that is used to track analytics.  
This is used for the main devscript app.

```bash
PLAUSIBLE_SCRIPT_URL=""
```

---


#### PLAUSIBLE_DOCS_SITE_NAME

This site enables anylytics tracking with [Plausible](https://plausible.io/),
which is open source and can be self-hosted.  
This is the name of the site that is configured in Plausible.  
This is used for the docs app.

```bash
PLAUSIBLE_DOCS_SITE_NAME=""
```

---


#### PLAUSIBLE_DOCS_SCRIPT_URL

This site enables anylytics tracking with [Plausible](https://plausible.io/),
which is open source and can be self-hosted.  
This is the URL of the Plausible script that is used to track analytics.  
This is used for the docs app.

```bash
PLAUSIBLE_DOCS_SCRIPT_URL=""
```

---


### SSO Provider Settings

These are the settings for the various SSO providers that are supported.  
They will only display on the login/register page if there are values configued for them.  

The `*_AUTO_VERIFY_EMAIL` setting will automatically verify the email address of the user if set to `true`.
Which is fine for all the major providers, but you may want to set this to `false` for custom OIDC providers.


#### Facebook


```bash
FACEBOOK_CLIENT_ID=""
FACEBOOK_CLIENT_SECRET=""
FACEBOOK_AUTO_VERIFY_EMAIL=true
```


#### Github

```bash
GITHUB_CLIENT_ID=""
GITHUB_CLIENT_SECRET=""
GITHUB_AUTO_VERIFY_EMAIL=true
```


#### Gitlab

```bash
GITLAB_CLIENT_ID=""
GITLAB_CLIENT_SECRET=""
GITLAB_AUTO_VERIFY_EMAIL=true
```


#### Google

```bash
GOOGLE_CLIENT_ID=""
GOOGLE_CLIENT_SECRET=""
GOOGLE_AUTO_VERIFY_EMAIL=true
```


#### Linkedin

```bash
LINKEDIN_CLIENT_ID=""
LINKEDIN_CLIENT_SECRET=""
LINKEDIN_AUTO_VERIFY_EMAIL=true
```


#### Microsoft

```bash
MICROSOFT_CLIENT_ID=""
MICROSOFT_CLIENT_SECRET=""
MICROSOFT_AUTO_VERIFY_EMAIL=true
```


#### Spotify

```bash
SPOTIFY_CLIENT_ID=""
SPOTIFY_CLIENT_SECRET=""
SPOTIFY_AUTO_VERIFY_EMAIL=true
```


#### Twitter (X)

```bash
XTWITTER_CLIENT_ID=""
XTWITTER_CLIENT_SECRET=""
XTWITTER_AUTO_VERIFY_EMAIL=true
```


#### Custom OIDC Provider

Callback to set in the OIDC provider will be `/auth/{GENERIC_OIDC_NAME}/callback`

```bash
GENERIC_OIDC_DISCOVERY_URL=""
GENERIC_OIDC_NAME=""
GENERIC_OIDC_CLIENT_ID=""
GENERIC_OIDC_CLIENT_SECRET=""
GENERIC_OIDC_ALLOW_INSECURE_HTTP=false
GENERIC_OIDC_AUTO_VERIFY_EMAIL=false
```
