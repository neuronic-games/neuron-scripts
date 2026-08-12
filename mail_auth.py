# Provider-agnostic SMTP connect + authenticate helper.
#
# Reads settings_email.provider ("office365", "gmail", or "greengeeks") and
# returns a ready-to-send, authenticated smtplib server via connect().
#
#   - office365: OAuth2 / Modern Auth via oauth365.py (browser login,
#     handles 2FA, then silent token refresh). See oauth365.py for the
#     one-time Azure app registration steps.
#
#   - gmail: App Password. Requires 2-Step Verification to be turned on
#     for the Google account, then create an app password at
#     https://myaccount.google.com/apppasswords and put it in
#     settings_email.gmail_app_password. Google no longer allows plain
#     account passwords for SMTP, so this is the standard way to use
#     Gmail SMTP with 2FA enabled without a full OAuth2 setup.
#
#   - greengeeks: Plain username/password over an implicit-SSL connection
#     (port 465), which is what GreenGeeks' cPanel-based mail hosting
#     provides. GreenGeeks mail accounts don't support 2FA/OAuth on SMTP -
#     the account password over TLS is the only auth method the server
#     exposes. Set settings_email.smtp_host to your mail server
#     (usually mail.yourdomain.com - check cPanel > Email Accounts >
#     Connect Devices for the exact value) and
#     settings_email.greengeeks_password to the mailbox password.

import smtplib
import ssl
import settings_email
import oauth365

# host is provider-specific; None means "must be supplied via settings_email.smtp_host"
_SMTP_DEFAULTS = {
    "office365": {"host": "smtp.office365.com", "port": 587, "mode": "starttls"},
    "gmail": {"host": "smtp.gmail.com", "port": 587, "mode": "starttls"},
    "greengeeks": {"host": None, "port": 465, "mode": "ssl"},
}


def _get_provider_and_config():
    provider = getattr(settings_email, "provider", "office365").lower()
    if provider not in _SMTP_DEFAULTS:
        raise ValueError(
            "Unknown settings_email.provider %r (expected 'office365', 'gmail', or 'greengeeks')"
            % provider
        )
    cfg = dict(_SMTP_DEFAULTS[provider])

    # Allow settings_email.smtp_host / smtp_port to override/supply the host,
    # since e.g. GreenGeeks' mail server name is account-specific.
    host_override = getattr(settings_email, "smtp_host", None)
    if host_override:
        cfg["host"] = host_override
    port_override = getattr(settings_email, "smtp_port", None)
    if port_override:
        cfg["port"] = port_override

    if not cfg["host"]:
        raise ValueError(
            "settings_email.smtp_host must be set when provider is %r" % provider
        )

    return provider, cfg


def get_smtp_server_and_port():
    _, cfg = _get_provider_and_config()
    return cfg["host"], cfg["port"]


def connect():
    """Open and fully authenticate an SMTP connection, ready for sendmail()."""
    provider, cfg = _get_provider_and_config()

    if cfg["mode"] == "ssl":
        server = smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=ssl.create_default_context())
    else:
        server = smtplib.SMTP(cfg["host"], cfg["port"])
        server.ehlo()
        server.starttls(context=ssl.create_default_context())

    server.ehlo()
    authenticate(server)
    return server


def authenticate(server):
    """Authenticate an already-connected/starttls'd smtplib.SMTP(_SSL)
    server using whatever method is configured for the selected provider."""
    provider, _ = _get_provider_and_config()

    if provider == "gmail":
        server.login(settings_email.sender_email, settings_email.gmail_app_password)

    elif provider == "office365":
        access_token = oauth365.get_access_token(
            settings_email.tenant_id,
            settings_email.client_id,
            settings_email.scopes,
            settings_email.sender_email,
        )
        oauth365.smtp_login_oauth2(server, settings_email.sender_email, access_token)

    elif provider == "greengeeks":
        server.login(settings_email.sender_email, settings_email.greengeeks_password)

    else:
        raise ValueError(
            "Unknown settings_email.provider %r (expected 'office365', 'gmail', or 'greengeeks')"
            % provider
        )
