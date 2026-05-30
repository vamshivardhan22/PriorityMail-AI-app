from dataclasses import dataclass
from email.utils import parseaddr


@dataclass(frozen=True)
class ClassificationResult:
    category: str
    priority: str
    confidence: float
    reason: str


JOB_SENDERS = (
    'internshala.com',
    'unstop.com',
    'unstop.news',
    'naukri.com',
    'linkedin.com',
    'foundit.in',
    'indeed.com',
    'glassdoor.com',
    'workdayjobs.com',
    'greenhouse.io',
    'lever.co',
    'nxtwave.co.in',
    'nxtwave.in',
)

NEWSLETTER_SENDERS = (
    'beehiiv.com',
    'substack.com',
    'medium.com',
)

SOCIAL_SENDERS = (
    'facebookmail.com',
    'instagram.com',
    'twitter.com',
    'x.com',
)

JOB_KEYWORDS = (
    'interview',
    'assessment',
    'hiring',
    'job',
    'internship',
    'shortlisted',
    'application',
    'recruiter',
    'resume',
    'career',
    'opening',
    'opportunities',
    'invitation',
    'confirm your spot',
    'role',
    'offer letter',
)

PLACEMENT_KEYWORDS = (
    'placement',
    'campus drive',
    'recruitment drive',
    'training and placement',
    'tpo',
    'eligible students',
    'pre-placement',
)

FINANCE_PURCHASE_KEYWORDS = (
    'invoice',
    'receipt',
    'payment',
    'transaction',
    'debited',
    'credited',
    'statement',
    'refund',
    'order',
    'purchase',
    'booking',
    'ticket',
    'delivered',
    'shipped',
)

ADVERTISEMENT_KEYWORDS = (
    'sale',
    'discount',
    'deal',
    'offer',
    'coupon',
    'lowest price',
    'limited time',
    'save',
    'price drop',
    'flights now from',
)

IMPORTANT_KEYWORDS = (
    'urgent',
    'important',
    'action required',
    'deadline',
    'verification',
    'security alert',
    'password',
    'otp',
)

SPAM_KEYWORDS = (
    'lottery',
    'winner',
    'claim now',
    'free money',
    'crypto giveaway',
    'congratulations you won',
)


def _clean_text(*parts):
    return ' '.join(part or '' for part in parts).casefold()


def _sender_domain(sender):
    email_address = parseaddr(sender)[1].casefold()
    if '@' not in email_address:
        return ''

    return email_address.rsplit('@', 1)[1]


def _contains_any(text, keywords):
    for keyword in keywords:
        if keyword in text:
            return keyword

    return None


def _domain_matches(domain, known_domains):
    return any(domain == known or domain.endswith(f'.{known}') for known in known_domains)


def classify_email(sender, subject, snippet=''):
    text = _clean_text(sender, subject, snippet)
    domain = _sender_domain(sender)

    placement_match = _contains_any(text, PLACEMENT_KEYWORDS)
    if placement_match:
        return ClassificationResult(
            category='placement',
            priority='high',
            confidence=0.95,
            reason=f"Matched placement keyword: {placement_match}",
        )

    job_match = _contains_any(text, JOB_KEYWORDS)
    if job_match and (_domain_matches(domain, JOB_SENDERS) or job_match in ('interview', 'assessment', 'shortlisted')):
        return ClassificationResult(
            category='job',
            priority='high',
            confidence=0.92,
            reason=f"Matched job signal: {job_match}",
        )

    important_match = _contains_any(text, IMPORTANT_KEYWORDS)
    if important_match:
        return ClassificationResult(
            category='important',
            priority='high',
            confidence=0.88,
            reason=f"Matched important keyword: {important_match}",
        )

    spam_match = _contains_any(text, SPAM_KEYWORDS)
    if spam_match:
        return ClassificationResult(
            category='spam',
            priority='low',
            confidence=0.9,
            reason=f"Matched spam keyword: {spam_match}",
        )

    finance_match = _contains_any(text, FINANCE_PURCHASE_KEYWORDS)
    if finance_match:
        return ClassificationResult(
            category='finance_purchase',
            priority='medium',
            confidence=0.84,
            reason=f"Matched finance/purchase keyword: {finance_match}",
        )

    ad_match = _contains_any(text, ADVERTISEMENT_KEYWORDS)
    if ad_match:
        return ClassificationResult(
            category='advertisement',
            priority='low',
            confidence=0.82,
            reason=f"Matched advertisement keyword: {ad_match}",
        )

    if _domain_matches(domain, NEWSLETTER_SENDERS):
        return ClassificationResult(
            category='newsletter',
            priority='low',
            confidence=0.8,
            reason=f"Matched newsletter sender: {domain}",
        )

    if _domain_matches(domain, SOCIAL_SENDERS):
        return ClassificationResult(
            category='social',
            priority='low',
            confidence=0.78,
            reason=f"Matched social sender: {domain}",
        )

    if domain.endswith('linkedin.com'):
        return ClassificationResult(
            category='professional',
            priority='medium',
            confidence=0.76,
            reason=f"Matched professional sender: {domain}",
        )

    return ClassificationResult(
        category='other',
        priority='normal',
        confidence=0.35,
        reason='No strong rule matched',
    )
