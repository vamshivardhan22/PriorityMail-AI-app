from .database_service import get_emails, mark_email_labeled
from .gmail_service import authenticate_gmail


CATEGORY_LABELS = {
    'advertisement': 'PriorityMail Advertisement',
    'finance_purchase': 'PriorityMail Finance Purchase',
    'important': 'PriorityMail Important',
    'job': 'PriorityMail Job',
    'newsletter': 'PriorityMail Newsletter',
    'other': 'PriorityMail Other',
    'placement': 'PriorityMail Placement',
    'professional': 'PriorityMail Professional',
    'social': 'PriorityMail Social',
    'spam': 'PriorityMail Spam',
}


def get_label_name(category):
    return CATEGORY_LABELS.get(category, 'PriorityMail Other')


def get_existing_labels(service):
    response = service.users().labels().list(userId='me').execute()
    labels = response.get('labels', [])
    return {label['name']: label['id'] for label in labels}


def create_label(service, label_name):
    label = {
        'name': label_name,
        'labelListVisibility': 'labelShow',
        'messageListVisibility': 'show',
    }
    created_label = service.users().labels().create(
        userId='me',
        body=label,
    ).execute()
    return created_label['id']


def ensure_label(service, label_name, label_cache):
    if label_name in label_cache:
        return label_cache[label_name], False

    label_id = create_label(service, label_name)
    label_cache[label_name] = label_id
    return label_id, True


def apply_label_to_message(service, message_id, label_id):
    service.users().messages().modify(
        userId='me',
        id=message_id,
        body={
            'addLabelIds': [label_id],
        },
    ).execute()


def apply_labels_to_saved_emails(category='All', priority='All', dry_run=True):
    emails = get_emails(category=category, priority=priority)
    planned = []

    for email in emails:
        label_name = get_label_name(email['category'])
        planned.append({
            'gmail_message_id': email['gmail_message_id'],
            'subject': email['subject'],
            'category': email['category'],
            'label_name': label_name,
            'already_marked': bool(email.get('gmail_label_applied_at')),
        })

    if dry_run:
        return {
            'dry_run': True,
            'planned_count': len(planned),
            'created_labels': [],
            'applied_count': 0,
            'skipped_count': 0,
            'planned': planned,
        }

    service = authenticate_gmail()
    label_cache = get_existing_labels(service)
    created_labels = []
    applied_count = 0
    skipped_count = 0

    for item in planned:
        if item['already_marked']:
            skipped_count += 1
            continue

        label_id, created = ensure_label(service, item['label_name'], label_cache)
        if created:
            created_labels.append(item['label_name'])

        apply_label_to_message(service, item['gmail_message_id'], label_id)
        mark_email_labeled(item['gmail_message_id'], item['label_name'])
        applied_count += 1

    return {
        'dry_run': False,
        'planned_count': len(planned),
        'created_labels': created_labels,
        'applied_count': applied_count,
        'skipped_count': skipped_count,
        'planned': planned,
    }
