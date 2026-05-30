try:
    from .career_extractor import extract_career_details
    from .database_service import (
        delete_career_event,
        get_emails,
        save_career_event,
    )
except ImportError:
    from career_extractor import extract_career_details
    from database_service import (
        delete_career_event,
        get_emails,
        save_career_event,
    )


CAREER_CATEGORIES = ('job', 'placement')


def sync_career_event_for_email(email_data):
    if email_data['category'] not in CAREER_CATEGORIES:
        delete_career_event(email_data['gmail_message_id'])
        return None

    details = extract_career_details(
        sender=email_data['sender'],
        subject=email_data['subject'],
        snippet=email_data.get('snippet', ''),
    )
    save_career_event(email_data['gmail_message_id'], details)
    return details


def rebuild_career_tracker():
    emails = get_emails()
    synced_count = 0

    for email in emails:
        details = sync_career_event_for_email(email)
        if details:
            synced_count += 1

    return synced_count
