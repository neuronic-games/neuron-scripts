# OAuth2 (Modern Auth) helper for Office 365 SMTP - supports MFA/2FA.
#
# Basic auth (plain username/password) no longer works for Office 365
# mailboxes with MFA enabled - Microsoft requires "modern auth" (OAuth2)
# for SMTP AUTH instead.
#
# First run opens an interactive browser login (this is where 2FA happens).
# The resulting refresh token is cached to disk (msal_token_cache.bin) and
# silently renewed by MSAL on later runs, so unattended/scheduled scripts
# don't need to log in again until the refresh token itself expires
# (Microsoft default: ~90 days of inactivity, longer with regular use).
#
# One-time setup required in Azure Portal (Entra ID):
#   1. App registrations > New registration
#        - Supported account types: Accounts in this organizational
#          directory only (single tenant) is fine for most cases
#        - Redirect URI: Public client/native (mobile & desktop)
#          -> http://localhost
#   2. API permissions > Add a permission > APIs my organization uses >
#        "Office 365 Exchange Online" > Delegated permissions > SMTP.Send
#        (grant admin consent if your tenant requires it)
#   3. Exchange admin center > the mailbox > make sure "Authenticated SMTP"
#        (SMTP AUTH) is enabled for that mailbox.
#   4. Put the app's Application (client) ID and Directory (tenant) ID
#        into settings.py.
#
# Requires: pip install msal

import os
import msal

_TOKEN_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "msal_token_cache.bin")


def _load_cache():
    cache = msal.SerializableTokenCache()
    if os.path.exists(_TOKEN_CACHE_FILE):
        with open(_TOKEN_CACHE_FILE, "r") as f:
            cache.deserialize(f.read())
    return cache


def _save_cache(cache):
    if cache.has_state_changed:
        with open(_TOKEN_CACHE_FILE, "w") as f:
            f.write(cache.serialize())


def get_access_token(tenant_id, client_id, scopes, username):
    """Return a valid OAuth2 access token, refreshing silently from the
    cache when possible, or prompting an interactive (MFA-capable) login
    when no usable cached token exists."""
    cache = _load_cache()
    app = msal.PublicClientApplication(
        client_id,
        authority="https://login.microsoftonline.com/%s" % tenant_id,
        token_cache=cache,
    )

    result = None
    accounts = app.get_accounts(username=username)
    if accounts:
        result = app.acquire_token_silent(scopes, account=accounts[0])

    if not result:
        # No cached/refreshable token -> interactive login (2FA happens here)
        result = app.acquire_token_interactive(scopes, login_hint=username)

    _save_cache(cache)

    if not result or "access_token" not in result:
        raise RuntimeError(
            "Could not acquire access token: %s - %s"
            % (result.get("error"), result.get("error_description"))
        )

    return result["access_token"]


def xoauth2_authobject(username, access_token):
    def _auth(challenge=None):
        return "user=%s\x01auth=Bearer %s\x01\x01" % (username, access_token)
    return _auth


def smtp_login_oauth2(server, username, access_token):
    """Authenticate an already-connected/starttls'd smtplib.SMTP server
    using XOAUTH2 instead of server.login(user, password)."""
    server.auth("XOAUTH2", xoauth2_authobject(username, access_token), initial_response_ok=True)
