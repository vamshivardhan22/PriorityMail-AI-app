import html
import re
from dataclasses import dataclass

from dateparser.search import search_dates


STAGE_KEYWORDS = (
    ('interview', 'Interview'),
    ('assessment', 'Assessment'),
    ('invitation', 'Invitation'),
    ('shortlisted', 'Shortlisted'),
    ('confirm your spot', 'Invitation'),
    ('confirm your application', 'Application Confirmation'),
    ('application', 'Application Update'),
    ('hiring', 'Hiring Opportunity'),
    ('opportunities', 'Opportunity Digest'),
    ('opportunity', 'Opportunity'),
    ('placement', 'Placement Update'),
)

COMPENSATION_PATTERN = re.compile(
    r'\b(?:INR|₹|Rs\.?)\s?[\d,.]+\s?(?:LPA|lakhs?|k|thousand|per annum)?\b',
    re.IGNORECASE,
)

MONTH_PATTERN = re.compile(
    r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)',
    re.IGNORECASE,
)
DATE_SEPARATOR_PATTERN = re.compile(r'\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b')
DEADLINE_CONTEXT_PATTERN = re.compile(
    r'\b(?:deadline|last date|expires|expiry|before|by|interview|assessment|test|drive)\b',
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CareerDetails:
    company: str
    role: str
    stage: str
    deadline_text: str
    deadline_date: str
    compensation: str
    confidence: float
    notes: str


def clean_text(*parts):
    text = ' '.join(part or '' for part in parts)
    text = html.unescape(text)
    text = re.sub(r'[\u200b-\u200f\ufeff]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_stage(text):
    lowered = text.casefold()

    for keyword, stage in STAGE_KEYWORDS:
        if keyword in lowered:
            return stage

    return 'Career Update'


def extract_role(text):
    patterns = (
        r"for ['\"](?P<role>[^'\"]+)['\"] role",
        r'for (?P<role>[A-Za-z][A-Za-z0-9 &/+.-]{2,60}) role',
        r'job (?P<role>[A-Za-z][A-Za-z0-9 &/+.-]{2,60})',
        r'(?P<role>[A-Za-z][A-Za-z0-9 &/+.-]{2,60}) role',
    )

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group('role').strip()

    return 'Unknown'


def extract_company(subject, sender):
    subject = clean_text(subject)

    patterns = (
        r'Career Update:\s*(?P<company>.+?)\s+is\s+Hiring',
        r'(?P<company>[A-Z][A-Za-z0-9 .&-]{1,60})\s+is\s+hiring',
        r'Interview Invitation\s*[-:]\s*(?P<company>[A-Z][A-Za-z0-9 .&-]{1,60})',
        r'Assessment\s*[-:]\s*(?P<company>[A-Z][A-Za-z0-9 .&-]{1,60})',
    )

    for pattern in patterns:
        match = re.search(pattern, subject, flags=re.IGNORECASE)
        if match:
            return match.group('company').strip(' |:-')

    sender_name = sender.split('<', 1)[0].strip()
    if sender_name and sender_name.lower() not in ('internshala', 'linkedin'):
        return sender_name

    return 'Unknown'


def extract_deadline(text):
    date_matches = search_dates(
        text,
        settings={
            'PREFER_DATES_FROM': 'future',
            'RETURN_AS_TIMEZONE_AWARE': False,
        },
    )

    if not date_matches:
        return '', ''

    for matched_text, parsed_date in date_matches:
        matched = matched_text.strip()
        matched_lower = matched.casefold()

        if matched_lower in ('now', 'today') or matched.isdigit():
            continue

        has_explicit_date = (
            MONTH_PATTERN.search(matched)
            or DATE_SEPARATOR_PATTERN.search(matched)
        )
        has_deadline_context = DEADLINE_CONTEXT_PATTERN.search(text)

        if has_explicit_date or has_deadline_context:
            return matched, parsed_date.date().isoformat()

    return '', ''


def extract_compensation(text):
    match = COMPENSATION_PATTERN.search(text)
    if not match:
        return ''

    return match.group(0).strip()


def score_details(company, role, deadline_date, compensation, stage):
    score = 0.45

    if company != 'Unknown':
        score += 0.18
    if role != 'Unknown':
        score += 0.16
    if deadline_date:
        score += 0.08
    if compensation:
        score += 0.08
    if stage != 'Career Update':
        score += 0.05

    return min(score, 0.95)


def extract_career_details(sender, subject, snippet):
    text = clean_text(subject, snippet, sender)
    company = extract_company(subject, sender)
    role = extract_role(text)
    stage = extract_stage(text)
    deadline_text, deadline_date = extract_deadline(text)
    compensation = extract_compensation(text)
    confidence = score_details(company, role, deadline_date, compensation, stage)

    missing = []
    if company == 'Unknown':
        missing.append('company')
    if role == 'Unknown':
        missing.append('role')
    if not deadline_date:
        missing.append('deadline')

    notes = 'Missing: ' + ', '.join(missing) if missing else 'Key details extracted'

    return CareerDetails(
        company=company,
        role=role,
        stage=stage,
        deadline_text=deadline_text,
        deadline_date=deadline_date,
        compensation=compensation,
        confidence=confidence,
        notes=notes,
    )
