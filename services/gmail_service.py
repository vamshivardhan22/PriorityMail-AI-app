from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timezone
import json
import os
import sys

try:
    from .alert_service import sync_alert_for_email
    from .career_service import sync_career_event_for_email
    from .database_service import get_category_counts, init_db, save_classified_email
    from .email_classifier import classify_email
except ImportError:
    from alert_service import sync_alert_for_email
    from career_service import sync_career_event_for_email
    from database_service import get_category_counts, init_db, save_classified_email
    from email_classifier import classify_email

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Gmail permission for reading messages and applying labels.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_PATH = os.path.join(BASE_DIR, 'credentials', 'credentials.json')
TOKEN_PATH = os.path.join(BASE_DIR, 'token.json')
SESSION_TOKEN_KEY = 'gmail_token_info'


def get_streamlit_gmail_secret(name):
    try:
        import streamlit as st
    except Exception:
        return ''

    try:
        gmail_secrets = st.secrets.get('gmail', {})
    except Exception:
        return ''

    return gmail_secrets.get(name, '')


def get_streamlit_session_token_info():
    try:
        import streamlit as st
    except Exception:
        return None

    token_info = st.session_state.get(SESSION_TOKEN_KEY)
    if isinstance(token_info, dict):
        return dict(token_info)

    return None


def parse_json_value(value, source_name):
    if not value:
        return None

    if isinstance(value, dict):
        return dict(value)

    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{source_name} is not valid JSON.") from exc


def load_secret_token_info():
    return parse_json_value(
        get_streamlit_gmail_secret('token_json'),
        'Streamlit secret gmail.token_json',
    )


def load_session_token_info():
    return get_streamlit_session_token_info()


def load_token_info():
    return load_secret_token_info() or load_session_token_info()


def load_secret_credentials_info():
    return parse_json_value(
        get_streamlit_gmail_secret('credentials_json'),
        'Streamlit secret gmail.credentials_json',
    )


def format_gmail_timestamp(internal_date):
    if not internal_date:
        return None

    try:
        timestamp = int(internal_date) / 1000
    except (TypeError, ValueError):
        return None

    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def validate_credentials_file():
    if not os.path.exists(CREDENTIALS_PATH):
        raise FileNotFoundError(
            f"Gmail OAuth file not found at: {CREDENTIALS_PATH}"
        )

    if os.path.getsize(CREDENTIALS_PATH) == 0:
        raise ValueError(
            "credentials/credentials.json is empty. Download the OAuth client "
            "JSON from Google Cloud Console and replace this file."
        )

    try:
        with open(CREDENTIALS_PATH, 'r', encoding='utf-8') as credentials_file:
            client_config = json.load(credentials_file)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "credentials/credentials.json is not valid JSON. Replace it with "
            "the OAuth client JSON downloaded from Google Cloud Console."
        ) from exc

    if 'installed' not in client_config and 'web' not in client_config:
        raise ValueError(
            "credentials/credentials.json does not look like a Google OAuth "
            "client file. It should contain an 'installed' or 'web' section."
        )


def token_has_required_scopes():
    token_info = load_token_info()
    if token_info:
        return token_info_has_required_scopes(token_info)

    if not os.path.exists(TOKEN_PATH):
        return False

    try:
        with open(TOKEN_PATH, 'r', encoding='utf-8') as token_file:
            token_data = json.load(token_file)
    except json.JSONDecodeError:
        return False

    return token_info_has_required_scopes(token_data)


def token_info_has_required_scopes(token_data):
    scope_value = token_data.get('scope', '')
    granted_scopes = set(scope_value.split())
    granted_scopes.update(token_data.get('scopes', []))

    return all(scope in granted_scopes for scope in SCOPES)


def has_streamlit_token():
    token_info = load_secret_token_info()
    return bool(token_info and token_info_has_required_scopes(token_info))


def has_session_token():
    token_info = load_session_token_info()
    return bool(token_info and token_info_has_required_scopes(token_info))


def has_local_token():
    return os.path.exists(TOKEN_PATH) and token_has_required_scopes()


def reset_local_gmail_token():
    if os.path.exists(TOKEN_PATH):
        os.remove(TOKEN_PATH)
        return True

    return False


def set_session_gmail_token(token_value):
    token_info = parse_json_value(token_value, 'Gmail token')
    if not token_info:
        raise ValueError('Paste or upload a Gmail token JSON file.')

    if not token_info_has_required_scopes(token_info):
        raise ValueError(
            'This Gmail token does not include the required Gmail modify scope.'
        )

    try:
        import streamlit as st
    except Exception as exc:
        raise RuntimeError('Streamlit session storage is not available.') from exc

    st.session_state[SESSION_TOKEN_KEY] = token_info
    return token_info


def clear_session_gmail_token():
    try:
        import streamlit as st
    except Exception:
        return False

    if SESSION_TOKEN_KEY in st.session_state:
        del st.session_state[SESSION_TOKEN_KEY]
        return True

    return False


def get_gmail_token_source():
    if has_streamlit_token():
        return 'Streamlit secrets'
    if has_session_token():
        return 'current app session'
    if has_local_token():
        return 'local token.json'

    return ''


def get_configured_gmail_account():
    source = get_gmail_token_source()
    if not source:
        return {
            'configured': False,
            'email': '',
            'source': '',
            'error': '',
        }

    try:
        service = authenticate_gmail()
        profile = service.users().getProfile(userId='me').execute()
    except Exception as exc:
        return {
            'configured': True,
            'email': '',
            'source': source,
            'error': str(exc),
        }

    return {
        'configured': True,
        'email': profile.get('emailAddress', ''),
        'source': source,
        'error': '',
    }


def authenticate_gmail():
    creds = None
    token_info = load_token_info()
    secret_credentials_info = load_secret_credentials_info()

    if token_info and token_info_has_required_scopes(token_info):
        creds = Credentials.from_authorized_user_info(token_info, SCOPES)
    elif token_has_required_scopes():
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # Login if no valid credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif token_info or secret_credentials_info:
            raise RuntimeError(
                "Gmail is not fully configured for Streamlit Cloud. Add a "
                "valid gmail.token_json secret generated from your local "
                "token.json file."
            )
        else:
            validate_credentials_file()

            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH,
                SCOPES
            )
            creds = flow.run_local_server(port=0)

        if not token_info:
            with open(TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)

    return service


def fetch_emails(max_results=10, verbose=True):
    service = authenticate_gmail()
    init_db()

    try:
        results = service.users().messages().list(
            userId='me',
            maxResults=max_results
        ).execute()
    except HttpError as exc:
        if exc.resp.status == 403:
            raise RuntimeError(
                "Gmail API is disabled for this Google Cloud project. Enable "
                "Gmail API in Google Cloud Console, wait a minute, then run "
                "this script again."
            ) from exc
        raise

    messages = results.get('messages', [])

    if not messages:
        if verbose:
            print("No messages found.")
        return {
            'fetched': 0,
            'saved': 0,
            'category_counts': get_category_counts(),
        }

    saved_count = 0

    for msg in messages:
        msg_data = service.users().messages().get(
            userId='me',
            id=msg['id']
        ).execute()

        headers = msg_data['payload'].get('headers', [])
        snippet = msg_data.get('snippet', '')

        subject = "No Subject"
        sender = "Unknown"

        for header in headers:
            if header['name'] == 'Subject':
                subject = header['value']

            if header['name'] == 'From':
                sender = header['value']

        classification = classify_email(sender, subject, snippet)
        email_data = {
            'gmail_message_id': msg_data['id'],
            'thread_id': msg_data.get('threadId'),
            'sender': sender,
            'subject': subject,
            'snippet': snippet,
            'received_at': format_gmail_timestamp(msg_data.get('internalDate')),
            'category': classification.category,
            'priority': classification.priority,
            'confidence': classification.confidence,
            'classification_reason': classification.reason,
        }
        save_classified_email(email_data)
        career_details = sync_career_event_for_email(email_data)
        sync_alert_for_email(email_data, career_details)
        saved_count += 1

        if verbose:
            print("=" * 50)
            print(f"From: {sender}")
            print(f"Subject: {subject}")
            print(f"Category: {classification.category}")
            print(f"Priority: {classification.priority}")
            print(f"Confidence: {classification.confidence:.0%}")
            print(f"Reason: {classification.reason}")

    category_counts = get_category_counts()

    if verbose:
        print("=" * 50)
        print(f"Saved emails: {saved_count}")
        print("Category totals:")
        for category, total in category_counts.items():
            print(f"- {category}: {total}")

    return {
        'fetched': len(messages),
        'saved': saved_count,
        'category_counts': category_counts,
    }


if __name__ == "__main__":
    fetch_emails()
