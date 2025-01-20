from fastapi_sso.sso.spotify import SpotifySSO

from app.settings import settings

sso = SpotifySSO(
    settings.SPOTIFY_CLIENT_ID,
    settings.SPOTIFY_CLIENT_SECRET,
    f"{settings.HOST}/auth/spotify/callback",  # Cant use url_for here as the routers have not been added yet
)

sso.is_trused_provider = settings.SPOTIFY_AUTO_VERIFY_EMAIL
sso.is_enabled = bool(settings.SPOTIFY_CLIENT_ID and settings.SPOTIFY_CLIENT_SECRET)
sso.button_text = "Login with Spotify"
