# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/)


## [Unreleased]

...


## [1.1.0] - 2025-02-06


### Added

- `is:command` filter to search for snippets with a command name set
- Archive/unarchive your own snippets
- `is:archived` filter to search for archived snippets
    - By default, archived snippets do not show up in search results
- Option to disable registration using the env var `DISABLE_REGISTRATION=true`
    - When disabled, the admin user can manually invite users via the admin dashboard
- Email setup is now optional
    - All accounts are auto verified on registration if email is disabled
- Option to disable local auth and only use enabled sso providers
    - `DISABLE_LOCAL_AUTH=true` (default is `false`)


## [1.0.0] - 2025-02-05

First public release of the devscript Snippet Manager


### Added

- Initial release
