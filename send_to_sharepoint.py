#!/usr/bin/env python
"""Upload a local file to a SharePoint Online document library, via
Microsoft Graph.

Reuses the same Azure AD app registration and OAuth2 login flow as
send_email.py's Office 365 support (see oauth365.py) - that app just needs
the additional Graph delegated permission "Sites.ReadWrite.All". First run
opens an interactive browser login (2FA happens there); after that MSAL
silently refreshes the cached token, so unattended/scheduled runs don't
need to log in again until the refresh token itself expires.

Configure the destination site/folder in settings.py:
    sharepoint_hostname, sharepoint_site_path, sharepoint_folder

Usage:
    python send_to_sharepoint.py <local file> [--folder "Reports/2026"]

Files up to 4MB are uploaded in a single request. Larger files
automatically use Graph's chunked upload-session API instead.

Requires: pip install msal requests
"""

from __future__ import annotations

import argparse
import os
import sys

import requests

import settings_loader  # must run before `import settings` below
import settings
import oauth365

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

# Graph's limit for a single simple PUT upload - larger files must use an
# upload session instead.
SIMPLE_UPLOAD_MAX_BYTES = 4 * 1024 * 1024

# Chunk size for the upload-session path. Must be a multiple of 320 KiB
# (327,680 bytes) per Graph's requirements; this is the size Microsoft's
# own docs use as an example.
CHUNK_SIZE = 10 * 327680


def _get_access_token() -> str:
    scopes = getattr(settings, "sharepoint_scopes", ["https://graph.microsoft.com/Sites.ReadWrite.All"])
    username = getattr(settings, "sharepoint_username", "") or settings.sender_email
    if not username:
        raise ValueError("Set settings.sharepoint_username or settings.sender_email")
    return oauth365.get_access_token(settings.tenant_id, settings.client_id, scopes, username)


def _get_site_id(token: str) -> str:
    hostname = getattr(settings, "sharepoint_hostname", "")
    site_path = getattr(settings, "sharepoint_site_path", "")
    if not hostname or not site_path:
        raise ValueError("Set settings.sharepoint_hostname and settings.sharepoint_site_path")

    url = f"{GRAPH_BASE}/sites/{hostname}:{site_path}"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    return resp.json()["id"]


def _remote_path(local_path: str, folder: str) -> str:
    filename = os.path.basename(local_path)
    folder = (folder if folder is not None else getattr(settings, "sharepoint_folder", "")).strip("/")
    return f"{folder}/{filename}" if folder else filename


def _upload_small(token: str, site_id: str, remote_path: str, local_path: str) -> dict:
    url = f"{GRAPH_BASE}/sites/{site_id}/drive/root:/{remote_path}:/content"
    with open(local_path, "rb") as f:
        data = f.read()
    resp = requests.put(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/octet-stream"},
        data=data,
    )
    resp.raise_for_status()
    return resp.json()


def _upload_large(token: str, site_id: str, remote_path: str, local_path: str) -> dict:
    size = os.path.getsize(local_path)
    session_url = f"{GRAPH_BASE}/sites/{site_id}/drive/root:/{remote_path}:/createUploadSession"
    resp = requests.post(
        session_url,
        headers={"Authorization": f"Bearer {token}"},
        json={"item": {"@microsoft.graph.conflictBehavior": "replace"}},
    )
    resp.raise_for_status()
    upload_url = resp.json()["uploadUrl"]

    result = None
    with open(local_path, "rb") as f:
        start = 0
        while start < size:
            chunk = f.read(CHUNK_SIZE)
            end = start + len(chunk) - 1
            resp = requests.put(
                upload_url,
                headers={
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {start}-{end}/{size}",
                },
                data=chunk,
            )
            resp.raise_for_status()
            start += len(chunk)
            result = resp.json() if resp.content else result
    return result or {}


def upload_file(local_path: str, folder: str | None = None) -> str:
    """Upload local_path to SharePoint, returning the uploaded file's URL."""
    if not os.path.isfile(local_path):
        raise FileNotFoundError(local_path)

    token = _get_access_token()
    site_id = _get_site_id(token)
    remote_path = _remote_path(local_path, folder)

    size = os.path.getsize(local_path)
    if size <= SIMPLE_UPLOAD_MAX_BYTES:
        result = _upload_small(token, site_id, remote_path, local_path)
    else:
        result = _upload_large(token, site_id, remote_path, local_path)

    return result.get("webUrl", remote_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload a file to SharePoint via Microsoft Graph.")
    parser.add_argument("file", help="Path to the local file to upload")
    parser.add_argument(
        "-f", "--folder",
        default=None,
        help="Destination folder within the document library "
             "(default: settings.sharepoint_folder, or the library root)",
    )
    args = parser.parse_args()

    try:
        url = upload_file(args.file, args.folder)
    except Exception as e:
        print(f"Upload failed: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Uploaded: {url}")
