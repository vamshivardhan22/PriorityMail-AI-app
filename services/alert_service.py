try:
    from .career_extractor import extract_career_details
    from .database_service import (
        delete_alert_for_email,
        get_emails,
        save_alert,
    )
except ImportError:
    from career_extractor import extract_career_details
    from database_service import (
        delete_alert_for_email,
        get_emails,
        save_alert,
    )


ALERT_CATEGORIES = ('job', 'placement', 'important')


def should_alert(email_data):
    return (
        email_data['category'] in ALERT_CATEGORIES
        or email_data['priority'] == 'high'
    )


def build_career_alert(email_data, career_details):
    company = career_details.company
    role = career_details.role

    if company != 'Unknown' and role != 'Unknown':
        title = f"{company} - {role}"
    elif company != 'Unknown':
        title = company
    elif role != 'Unknown':
        title = role
    else:
        title = email_data['subject']

    details = [career_details.stage]
    if career_details.deadline_date:
        details.append(f"deadline {career_details.deadline_date}")
    if career_details.compensation:
        details.append(career_details.compensation)

    return {
        'alert_type': 'career',
        'title': title,
        'message': ' | '.join(details),
        'severity': 'high',
    }


def build_priority_alert(email_data):
    return {
        'alert_type': email_data['category'],
        'title': email_data['subject'],
        'message': email_data['classification_reason'],
        'severity': email_data['priority'],
    }


def sync_alert_for_email(email_data, career_details=None):
    if not should_alert(email_data):
        delete_alert_for_email(email_data['gmail_message_id'])
        return None

    if email_data['category'] in ('job', 'placement'):
        details = career_details or extract_career_details(
            sender=email_data['sender'],
            subject=email_data['subject'],
            snippet=email_data.get('snippet', ''),
        )
        alert_data = build_career_alert(email_data, details)
    else:
        alert_data = build_priority_alert(email_data)

    alert_data.update({
        'gmail_message_id': email_data['gmail_message_id'],
        'sender': email_data['sender'],
        'subject': email_data['subject'],
    })
    save_alert(alert_data)
    return alert_data


def rebuild_alerts():
    emails = get_emails()
    synced_count = 0

    for email in emails:
        alert = sync_alert_for_email(email)
        if alert:
            synced_count += 1

    return synced_count
