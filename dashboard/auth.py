from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path


USERS_FILE = Path(".streamlit/users.json")
REMEMBER_FILE = Path(".streamlit/remembered_login.json")
OAUTH_STATE_FILE = Path(".streamlit/oauth_states.json")
PASSWORD_RESET_FILE = Path(".streamlit/password_reset_tokens.json")
LOGO_PATH = Path("assets/mercado-livre-logo.png")
EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_PATTERN = re.compile(r"^\+?[0-9][0-9\s\-()]{7,16}$")


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save_json(path: Path, payload) -> None:
    _ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_users() -> dict[str, dict]:
    return _load_json(USERS_FILE, {})


def save_users(users: dict[str, dict]) -> None:
    _save_json(USERS_FILE, users)


def remembered_login() -> str:
    payload = _load_json(REMEMBER_FILE, {})
    return str(payload.get("identifier", ""))


def set_remembered_login(identifier: str) -> None:
    _save_json(REMEMBER_FILE, {"identifier": identifier})


def clear_remembered_login() -> None:
    if REMEMBER_FILE.exists():
        REMEMBER_FILE.unlink()


def store_oauth_state(state_token: str, provider: str) -> None:
    states = _load_json(OAUTH_STATE_FILE, {})
    states[state_token] = provider
    _save_json(OAUTH_STATE_FILE, states)


def consume_oauth_state(state_token: str) -> str:
    states = _load_json(OAUTH_STATE_FILE, {})
    provider = str(states.pop(state_token, ""))
    _save_json(OAUTH_STATE_FILE, states)
    return provider


def normalize_identifier(value: str) -> str:
    return value.strip().lower()


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_PATTERN.match(email.strip()))


def normalize_phone(phone: str) -> str:
    return "".join(ch for ch in phone if ch.isdigit() or ch == "+")


def is_valid_phone(phone: str) -> bool:
    candidate = phone.strip()
    return bool(PHONE_PATTERN.match(candidate))


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120000,
    ).hex()


def _password_record(password: str) -> tuple[str, str]:
    salt = secrets.token_hex(16)
    return salt, _hash_password(password, salt)


def _find_user_key(identifier: str, users: dict[str, dict]) -> str | None:
    normalized = normalize_identifier(identifier)
    for key, user in users.items():
        if (
            key == normalized
            or normalize_identifier(user.get("email", "")) == normalized
            or normalize_phone(user.get("phone", "")) == normalize_phone(identifier)
        ):
            return key
    return None


def create_user(phone: str, email: str, password: str) -> tuple[bool, str]:
    users = load_users()
    phone_key = normalize_phone(phone)
    email_key = normalize_identifier(email)

    if not phone_key or not email_key:
        return False, "Phone number and email are required."
    if not is_valid_phone(phone):
        return False, "The phone number is not correct. Use a valid phone number."
    if not is_valid_email(email):
        return False, "The email is not correct. Use a valid email address."
    if phone_key in users or _find_user_key(email, users):
        return (
            False,
            "An account with that email or phone number already exists. Use a different email address and phone number, or sign in instead.",
        )
    if len(password) < 8:
        return False, "Use a password with at least 8 characters."

    salt, password_hash = _password_record(password)
    users[phone_key] = {
        "phone": phone.strip(),
        "email": email.strip(),
        "salt": salt,
        "password_hash": password_hash,
    }
    save_users(users)
    return True, "Your account has been created. Please sign in."


def authenticate_user(identifier: str, password: str) -> tuple[bool, str, dict | None]:
    users = load_users()
    user_key = _find_user_key(identifier, users)
    if not user_key:
        return (
            False,
            "We couldn't find an account for that phone number or email. Create an account first, then sign in.",
            None,
        )

    user = users[user_key]
    if not user.get("password_hash") or not user.get("salt"):
        provider = str(user.get("auth_provider", "external account")).title()
        return False, f"This account uses {provider} sign-in. Use the provider button instead.", None
    attempted_hash = _hash_password(password, user["salt"])
    if attempted_hash != user["password_hash"]:
        return False, "Incorrect password. Please try again and check Caps Lock.", None
    return True, "Login successful.", user


def reset_password(identifier: str, new_password: str) -> tuple[bool, str]:
    users = load_users()
    user_key = _find_user_key(identifier, users)
    if not user_key:
        return False, "We couldn't find an account for that phone number or email."
    if not users[user_key].get("password_hash") or not users[user_key].get("salt"):
        provider = str(users[user_key].get("auth_provider", "external account")).title()
        return False, f"This account uses {provider} sign-in. Reset the password with that provider."
    if len(new_password) < 8:
        return False, "Use a password with at least 8 characters."
    if _hash_password(new_password, users[user_key]["salt"]) == users[user_key]["password_hash"]:
        return (
            False,
            "You can't use the old password to reset a new password. Choose a new password instead.",
        )

    salt, password_hash = _password_record(new_password)
    users[user_key]["salt"] = salt
    users[user_key]["password_hash"] = password_hash
    save_users(users)
    return True, "Your password has been updated. You can log in now."


def get_user(identifier: str) -> dict | None:
    users = load_users()
    user_key = _find_user_key(identifier, users)
    return users.get(user_key) if user_key else None


def create_or_update_oauth_user(provider: str, email: str, name: str = "") -> dict:
    if not is_valid_email(email):
        raise ValueError("OAuth provider did not return a valid email address.")

    users = load_users()
    existing_key = _find_user_key(email, users)
    email_key = normalize_identifier(email)
    user_key = existing_key or email_key

    existing_user = users.get(user_key, {})
    user = {
        "phone": existing_user.get("phone", ""),
        "email": email.strip(),
        "display_name": name.strip() or existing_user.get("display_name", ""),
        "auth_provider": provider.strip().lower(),
    }

    if existing_user.get("salt") and existing_user.get("password_hash"):
        user["salt"] = existing_user["salt"]
        user["password_hash"] = existing_user["password_hash"]

    users[user_key] = user
    save_users(users)
    return user


def _send_password_reset_email(
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_username: str,
    smtp_password: str,
    sender_email: str,
    recipient_email: str,
    reset_link: str,
) -> None:
    logo_cid = "mercado-livre-logo-reset"
    message = EmailMessage()
    message["Subject"] = "Reset your Mercado Livre Analytics Portal password"
    message["From"] = sender_email
    message["To"] = recipient_email
    text_body = (
        "We received a request to reset your Mercado Livre Analytics Portal password.\n\n"
        f"Use this link to create a new password:\n{reset_link}\n\n"
        "This reset link will expire in 1 hour.\n\n"
        "If you did not request this, you can ignore this email.\n\n"
        "Regards,\nMercado Livre Analytics Portal"
    )
    html_body = f"""
    <html>
      <body style="margin:0;padding:0;background:#f5f7fb;font-family:Segoe UI,Arial,sans-serif;color:#172033;">
        <div style="max-width:680px;margin:24px auto;background:#ffffff;border:1px solid #e5e7eb;border-radius:20px;overflow:hidden;box-shadow:0 18px 36px rgba(15,23,42,0.08);">
          <div style="background:linear-gradient(135deg,#101a6b 0%,#0f172a 100%);padding:28px 32px 22px;text-align:center;">
            <img src="cid:{logo_cid}" alt="Mercado Livre" style="width:110px;height:auto;background:#ffffff;border-radius:18px;padding:10px;border:1px solid rgba(255,255,255,0.35);" />
            <div style="font-family:Georgia,'Palatino Linotype',serif;font-size:28px;line-height:1.2;color:#fffdf6;margin-top:18px;">Reset Your Password</div>
            <div style="font-size:14px;line-height:1.6;color:rgba(248,244,234,0.86);margin-top:10px;">
              Mercado Livre Analytics Portal account recovery request.
            </div>
          </div>
          <div style="padding:28px 32px;">
            <p style="margin:0 0 16px;font-size:16px;line-height:1.7;color:#25324a;">
              We received a request to reset your Mercado Livre Analytics Portal password.
            </p>
            <div style="background:#f8f4ea;border:1px solid #e7dcc1;border-radius:16px;padding:16px 18px;margin:0 0 18px;">
              <div style="font-size:12px;text-transform:uppercase;letter-spacing:0.08em;color:#6b7280;margin-bottom:8px;">Security notice</div>
              <div style="font-size:15px;line-height:1.7;color:#172033;">Use the secure link below to create a new password.</div>
              <div style="font-size:15px;line-height:1.7;color:#172033;"><strong>Link expiry:</strong> 1 hour</div>
            </div>
            <div style="margin:0 0 20px;text-align:center;">
              <a href="{reset_link}" style="display:inline-block;background:#101a6b;color:#fffdf6;text-decoration:none;font-weight:700;padding:14px 24px;border-radius:14px;">Reset password</a>
            </div>
            <p style="margin:0 0 16px;font-size:14px;line-height:1.75;color:#475467;">
              If the button does not open correctly, use this link:
            </p>
            <p style="margin:0 0 16px;font-size:13px;line-height:1.7;word-break:break-all;">
              <a href="{reset_link}" style="color:#101a6b;">{reset_link}</a>
            </p>
            <div style="border-top:1px solid #e5e7eb;padding-top:16px;font-size:13px;line-height:1.7;color:#667085;">
              If you did not request this password reset, you can safely ignore this email.
            </div>
          </div>
          <div style="background:#f9fafb;border-top:1px solid #e5e7eb;padding:16px 32px;font-size:13px;color:#6b7280;">
            Sent by Mercado Livre Analytics Portal
          </div>
        </div>
      </body>
    </html>
    """
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")
    if LOGO_PATH.exists():
        mime_type, _ = mimetypes.guess_type(str(LOGO_PATH))
        maintype, subtype = (mime_type or "image/png").split("/", 1)
        with LOGO_PATH.open("rb") as logo_file:
            message.get_payload()[1].add_related(
                logo_file.read(),
                maintype=maintype,
                subtype=subtype,
                cid=f"<{logo_cid}>",
            )

    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as smtp:
        smtp.starttls()
        smtp.login(smtp_username, smtp_password)
        smtp.send_message(message)


def request_password_reset(
    email: str,
    *,
    app_base_url: str,
    smtp_host: str,
    smtp_port: int,
    smtp_username: str,
    smtp_password: str,
    sender_email: str,
) -> tuple[bool, str]:
    normalized_email = normalize_identifier(email)
    if not is_valid_email(normalized_email):
        return False, "The email is not correct. Use a valid email address."

    users = load_users()
    user_key = _find_user_key(normalized_email, users)
    if not user_key:
        return False, "We couldn't find an account for that email address."

    user = users[user_key]
    if normalize_identifier(user.get("email", "")) != normalized_email:
        return False, "Please use the email address linked to the account."
    if not user.get("password_hash") or not user.get("salt"):
        provider = str(user.get("auth_provider", "external account")).title()
        return False, f"This account uses {provider} sign-in. Reset the password with that provider."
    if not all([app_base_url, smtp_host, smtp_port, smtp_username, smtp_password, sender_email]):
        return False, "Email reset is not configured yet. Add SMTP settings first."

    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    tokens = _load_json(PASSWORD_RESET_FILE, {})
    tokens[token] = {"user_key": user_key, "expires_at": expires_at}
    _save_json(PASSWORD_RESET_FILE, tokens)

    reset_link = f"{app_base_url.rstrip('/')}/?reset_token={token}"
    _send_password_reset_email(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_username=smtp_username,
        smtp_password=smtp_password,
        sender_email=sender_email,
        recipient_email=user["email"],
        reset_link=reset_link,
    )
    return True, "A password reset link has been sent to your email address."


def _consume_password_reset_token(token: str) -> str | None:
    tokens = _load_json(PASSWORD_RESET_FILE, {})
    payload = tokens.get(token)
    if not payload:
        return None

    expires_at = payload.get("expires_at", "")
    try:
        expiry = datetime.fromisoformat(expires_at)
    except ValueError:
        expiry = datetime.now(timezone.utc) - timedelta(seconds=1)

    if expiry < datetime.now(timezone.utc):
        tokens.pop(token, None)
        _save_json(PASSWORD_RESET_FILE, tokens)
        return None

    user_key = str(payload.get("user_key", ""))
    tokens.pop(token, None)
    _save_json(PASSWORD_RESET_FILE, tokens)
    return user_key or None


def reset_password_with_token(token: str, new_password: str) -> tuple[bool, str]:
    if len(new_password) < 8:
        return False, "Use a password with at least 8 characters."

    user_key = _consume_password_reset_token(token)
    if not user_key:
        return False, "This password reset link is invalid or has expired."

    users = load_users()
    if user_key not in users:
        return False, "We couldn't find the account for this reset link."
    if _hash_password(new_password, users[user_key]["salt"]) == users[user_key]["password_hash"]:
        return (
            False,
            "You can't use the old password to reset a new password. Choose a new password instead.",
        )

    salt, password_hash = _password_record(new_password)
    users[user_key]["salt"] = salt
    users[user_key]["password_hash"] = password_hash
    save_users(users)
    return True, "Your password has been reset. You can sign in now."

def generate_magic_link_token() -> str:
    return secrets.token_urlsafe(18)
