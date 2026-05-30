import pandas as pd
import streamlit as st

from services.database_service import (
    get_alert_counts,
    get_alerts,
    get_category_counts,
    get_career_event_counts,
    get_career_events,
    get_emails,
    get_filter_options,
    get_priority_counts,
    init_db,
    mark_alert_read,
    mark_alert_unread,
    mark_all_alerts_read,
)
from services.alert_service import rebuild_alerts
from services.automation_service import load_automation_config, run_once
from services.career_service import rebuild_career_tracker
from services.gmail_service import fetch_emails
from services.label_service import apply_labels_to_saved_emails
from services.whatsapp_service import (
    send_test_message,
    send_unsent_alerts_to_whatsapp,
    whatsapp_config_status,
)


st.set_page_config(
    page_title='PriorityMail AI',
    layout='wide',
)


def format_label(value):
    return value.replace('_', ' ').title()


def render_metric_row(category_counts, priority_counts, alert_counts):
    total_emails = sum(category_counts.values())
    high_priority = priority_counts.get('high', 0)
    job_emails = category_counts.get('job', 0) + category_counts.get('placement', 0)
    unread_alerts = alert_counts['unread']

    col1, col2, col3, col4 = st.columns(4)
    col1.metric('Saved Emails', total_emails)
    col2.metric('Career Signals', job_emails)
    col3.metric('High Priority', high_priority)
    col4.metric('Unread Alerts', unread_alerts)


def render_category_chart(category_counts):
    if not category_counts:
        st.info('No emails saved yet. Use Refresh Inbox to import Gmail messages.')
        return

    chart_data = pd.DataFrame(
        [
            {'category': format_label(category), 'total': total}
            for category, total in category_counts.items()
        ]
    )
    st.bar_chart(chart_data, x='category', y='total', height=260)


def render_email_list(emails):
    if not emails:
        st.warning('No emails match the current filters.')
        return

    for email in emails:
        with st.container(border=True):
            top_left, top_right = st.columns([0.72, 0.28])
            top_left.subheader(email['subject'])
            top_right.caption(email['received_at'] or 'No timestamp')

            st.write(email['sender'])

            badge_left, badge_mid, badge_right = st.columns([0.22, 0.2, 0.58])
            badge_left.markdown(f"**Category:** {format_label(email['category'])}")
            badge_mid.markdown(f"**Priority:** {format_label(email['priority'])}")
            badge_right.progress(
                min(max(float(email['confidence']), 0), 1),
                text=f"Confidence {float(email['confidence']):.0%}",
            )

            if email['snippet']:
                st.caption(email['snippet'])

            with st.expander('Classification reason'):
                st.write(email['classification_reason'])


def render_career_tracker(career_events):
    if not career_events:
        st.info('No career emails extracted yet.')
        return

    for event in career_events:
        with st.container(border=True):
            top_left, top_right = st.columns([0.72, 0.28])
            title = event['company']
            if event['role'] != 'Unknown':
                title = f"{event['company']} - {event['role']}"
            top_left.subheader(title)
            top_right.caption(event['deadline_date'] or 'No deadline found')

            detail_cols = st.columns([0.28, 0.24, 0.24, 0.24])
            detail_cols[0].markdown(f"**Stage:** {event['stage']}")
            detail_cols[1].markdown(f"**Role:** {event['role']}")
            detail_cols[2].markdown(f"**Comp:** {event['compensation'] or 'Unknown'}")
            detail_cols[3].progress(
                min(max(float(event['confidence']), 0), 1),
                text=f"{float(event['confidence']):.0%}",
            )

            st.caption(event['subject'])

            if event['snippet']:
                with st.expander('Email snippet'):
                    st.write(event['snippet'])

            st.caption(event['notes'])


def render_alerts(alerts):
    if not alerts:
        st.info('No alerts match the current filters.')
        return

    for alert in alerts:
        with st.container(border=True):
            top_left, top_right = st.columns([0.72, 0.28])
            top_left.subheader(alert['title'])
            top_right.caption(alert['status'].title())

            detail_cols = st.columns([0.2, 0.2, 0.6])
            detail_cols[0].markdown(f"**Type:** {format_label(alert['alert_type'])}")
            detail_cols[1].markdown(f"**Severity:** {format_label(alert['severity'])}")
            detail_cols[2].markdown(f"**Received:** {alert['received_at'] or 'Unknown'}")

            st.write(alert['message'])
            st.caption(alert['sender'])

            whatsapp_status = 'WhatsApp not sent'
            if alert.get('whatsapp_sent_at'):
                whatsapp_status = f"WhatsApp sent: {alert['whatsapp_sent_at']}"
            elif alert.get('whatsapp_error'):
                whatsapp_status = f"WhatsApp error: {alert['whatsapp_error']}"
            st.caption(whatsapp_status)

            if alert['snippet']:
                with st.expander('Email snippet'):
                    st.write(alert['snippet'])

            action_cols = st.columns([0.18, 0.82])
            if alert['status'] == 'unread':
                if action_cols[0].button(
                    'Mark read',
                    key=f"read-{alert['gmail_message_id']}",
                ):
                    mark_alert_read(alert['gmail_message_id'])
                    st.rerun()
            else:
                if action_cols[0].button(
                    'Mark unread',
                    key=f"unread-{alert['gmail_message_id']}",
                ):
                    mark_alert_unread(alert['gmail_message_id'])
                    st.rerun()


def main():
    init_db()

    st.title('PriorityMail AI')

    with st.sidebar:
        st.header('Controls')
        if st.button('Refresh Inbox', use_container_width=True):
            with st.spinner('Fetching latest Gmail messages...'):
                try:
                    fetch_emails()
                except Exception as exc:
                    st.error(str(exc))
                else:
                    st.cache_data.clear()
                    st.success('Inbox refreshed.')

        options = get_filter_options()
        category = st.selectbox('Category', ['All'] + options['categories'])
        priority = st.selectbox('Priority', ['All'] + options['priorities'])
        search = st.text_input('Search', placeholder='Sender, subject, or snippet')

        if st.button('Rebuild Career Tracker', use_container_width=True):
            synced_count = rebuild_career_tracker()
            st.success(f"Career tracker synced: {synced_count} emails.")

        if st.button('Rebuild Alerts', use_container_width=True):
            synced_count = rebuild_alerts()
            st.success(f"Alerts synced: {synced_count} emails.")

        st.divider()
        st.subheader('Automation')
        automation_config = load_automation_config()
        st.metric('Interval Seconds', automation_config['interval_seconds'])
        st.metric('Max Results', automation_config['max_results'])
        if st.button('Run Once', use_container_width=True):
            with st.spinner('Running automation cycle...'):
                try:
                    automation_result = run_once(verbose=False)
                except Exception as exc:
                    st.error(str(exc))
                else:
                    st.success(
                        f"Fetched {automation_result['fetch']['fetched']} emails, "
                        f"synced {automation_result['alert_count']} alerts."
                    )

        st.divider()
        st.subheader('Gmail Labels')
        if st.button('Preview Labels', use_container_width=True):
            preview = apply_labels_to_saved_emails(
                category=category,
                priority=priority,
                dry_run=True,
            )
            st.session_state['label_preview'] = preview

        apply_labels = st.checkbox('Apply labels to Gmail')
        if st.button('Run Labeling', use_container_width=True, disabled=not apply_labels):
            with st.spinner('Applying Gmail labels...'):
                result = apply_labels_to_saved_emails(
                    category=category,
                    priority=priority,
                    dry_run=False,
                )
            st.session_state['label_result'] = result
            st.success(f"Applied labels to {result['applied_count']} emails.")

    category_counts = get_category_counts()
    priority_counts = get_priority_counts()
    alert_counts = get_alert_counts()
    career_counts = get_career_event_counts()
    emails = get_emails(category=category, priority=priority, search=search.strip())
    career_events = get_career_events(search=search.strip())
    alerts = get_alerts(search=search.strip())

    render_metric_row(category_counts, priority_counts, alert_counts)

    overview_tab, alerts_tab, career_tab, emails_tab = st.tabs([
        'Overview',
        'Alerts',
        'Career Tracker',
        'Saved Emails',
    ])

    with overview_tab:
        left, right = st.columns([0.38, 0.62])
        with left:
            st.subheader('Category Overview')
            render_category_chart(category_counts)

        with right:
            st.subheader('Career Summary')
            career_cols = st.columns(4)
            career_cols[0].metric('Tracked', career_counts['total'])
            career_cols[1].metric('Deadlines Found', career_counts['upcoming_deadlines'])
            career_cols[2].metric('Unknown Companies', career_counts['unknown_companies'])
            career_cols[3].metric('Unknown Roles', career_counts['unknown_roles'])
            render_career_tracker(career_events[:3])

    with alerts_tab:
        st.subheader('Alerts')
        alert_cols = st.columns(4)
        alert_cols[0].metric('Total', alert_counts['total'])
        alert_cols[1].metric('Unread', alert_counts['unread'])
        alert_cols[2].metric('High', alert_counts['high'])
        alert_cols[3].metric('Career', alert_counts['career'])

        status = st.selectbox('Alert status', ['All', 'unread', 'read'])
        if st.button('Mark all read', disabled=alert_counts['unread'] == 0):
            mark_all_alerts_read()
            st.rerun()

        st.divider()
        st.subheader('WhatsApp')
        whatsapp_status = whatsapp_config_status()
        if whatsapp_status['configured']:
            st.success('WhatsApp is configured.')
        else:
            st.warning('Missing: ' + ', '.join(whatsapp_status['missing']))

        whatsapp_cols = st.columns([0.2, 0.8])
        if whatsapp_cols[0].button(
            'Send test',
            disabled=not whatsapp_status['configured'],
        ):
            try:
                send_test_message()
            except Exception as exc:
                st.error(str(exc))
            else:
                st.success('Test message sent.')

        if whatsapp_cols[1].button(
            'Send unread alerts to WhatsApp',
            disabled=not whatsapp_status['configured'] or alert_counts['unread'] == 0,
        ):
            result = send_unsent_alerts_to_whatsapp()
            if result['failed']:
                st.error(f"Sent {result['sent_count']} alerts; {len(result['failed'])} failed.")
                with st.expander('WhatsApp failures'):
                    for failure in result['failed']:
                        st.write(f"{failure['title']}: {failure['error']}")
            else:
                st.success(
                    f"Sent {result['sent_count']} alerts. "
                    f"Skipped {result['skipped_count']} already-sent alerts."
                )
            st.rerun()

        render_alerts(get_alerts(status=status, search=search.strip()))

    with career_tab:
        st.subheader('Career Tracker')
        render_career_tracker(career_events)

    with emails_tab:
        st.subheader('Saved Emails')
        if 'label_preview' in st.session_state:
            preview = st.session_state['label_preview']
            st.info(f"Preview: {preview['planned_count']} emails would be labeled.")

        if 'label_result' in st.session_state:
            result = st.session_state['label_result']
            st.success(
                f"Labels applied: {result['applied_count']} | "
                f"Skipped: {result['skipped_count']} | "
                f"Created labels: {len(result['created_labels'])}"
            )

        render_email_list(emails)


if __name__ == '__main__':
    main()
