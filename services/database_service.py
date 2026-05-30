import os
import sqlite3


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'prioritymail.db')


def get_connection():
    os.makedirs(DATA_DIR, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS emails (
                gmail_message_id TEXT PRIMARY KEY,
                thread_id TEXT,
                sender TEXT NOT NULL,
                subject TEXT NOT NULL,
                snippet TEXT,
                received_at TEXT,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                confidence REAL NOT NULL,
                classification_reason TEXT NOT NULL,
                gmail_label_name TEXT,
                gmail_label_applied_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        ensure_column(connection, 'emails', 'gmail_label_name', 'TEXT')
        ensure_column(connection, 'emails', 'gmail_label_applied_at', 'TEXT')
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_emails_category
            ON emails(category)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_emails_priority
            ON emails(priority)
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS career_events (
                gmail_message_id TEXT PRIMARY KEY,
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                stage TEXT NOT NULL,
                deadline_text TEXT,
                deadline_date TEXT,
                compensation TEXT,
                confidence REAL NOT NULL,
                notes TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (gmail_message_id)
                    REFERENCES emails(gmail_message_id)
                    ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_career_events_deadline
            ON career_events(deadline_date)
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                gmail_message_id TEXT PRIMARY KEY,
                alert_type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'unread',
                sender TEXT NOT NULL,
                subject TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                read_at TEXT,
                whatsapp_sent_at TEXT,
                whatsapp_error TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (gmail_message_id)
                    REFERENCES emails(gmail_message_id)
                    ON DELETE CASCADE
            )
            """
        )
        ensure_column(connection, 'alerts', 'whatsapp_sent_at', 'TEXT')
        ensure_column(connection, 'alerts', 'whatsapp_error', 'TEXT')
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_alerts_status
            ON alerts(status)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_alerts_severity
            ON alerts(severity)
            """
        )


def ensure_column(connection, table_name, column_name, column_definition):
    columns = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    existing_columns = {column['name'] for column in columns}

    if column_name not in existing_columns:
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        )


def save_classified_email(email_data):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO emails (
                gmail_message_id,
                thread_id,
                sender,
                subject,
                snippet,
                received_at,
                category,
                priority,
                confidence,
                classification_reason
            )
            VALUES (
                :gmail_message_id,
                :thread_id,
                :sender,
                :subject,
                :snippet,
                :received_at,
                :category,
                :priority,
                :confidence,
                :classification_reason
            )
            ON CONFLICT(gmail_message_id) DO UPDATE SET
                thread_id = excluded.thread_id,
                sender = excluded.sender,
                subject = excluded.subject,
                snippet = excluded.snippet,
                received_at = excluded.received_at,
                category = excluded.category,
                priority = excluded.priority,
                confidence = excluded.confidence,
                classification_reason = excluded.classification_reason,
                updated_at = CURRENT_TIMESTAMP
            """,
            email_data,
        )


def get_category_counts():
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT category, COUNT(*) AS total
            FROM emails
            GROUP BY category
            ORDER BY total DESC, category ASC
            """
        ).fetchall()

    return {row['category']: row['total'] for row in rows}


def get_priority_counts():
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT priority, COUNT(*) AS total
            FROM emails
            GROUP BY priority
            ORDER BY total DESC, priority ASC
            """
        ).fetchall()

    return {row['priority']: row['total'] for row in rows}


def get_filter_options():
    with get_connection() as connection:
        categories = connection.execute(
            "SELECT DISTINCT category FROM emails ORDER BY category"
        ).fetchall()
        priorities = connection.execute(
            "SELECT DISTINCT priority FROM emails ORDER BY priority"
        ).fetchall()

    return {
        'categories': [row['category'] for row in categories],
        'priorities': [row['priority'] for row in priorities],
    }


def get_emails(category='All', priority='All', search=''):
    query = """
        SELECT
            gmail_message_id,
            sender,
            subject,
            snippet,
            received_at,
            category,
            priority,
            confidence,
            classification_reason,
            gmail_label_name,
            gmail_label_applied_at,
            updated_at
        FROM emails
        WHERE 1 = 1
    """
    params = {}

    if category != 'All':
        query += " AND category = :category"
        params['category'] = category

    if priority != 'All':
        query += " AND priority = :priority"
        params['priority'] = priority

    if search:
        query += """
            AND (
                sender LIKE :search
                OR subject LIKE :search
                OR snippet LIKE :search
            )
        """
        params['search'] = f"%{search}%"

    query += " ORDER BY received_at DESC, updated_at DESC"

    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()

    return [dict(row) for row in rows]


def mark_email_labeled(gmail_message_id, label_name):
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE emails
            SET
                gmail_label_name = :label_name,
                gmail_label_applied_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE gmail_message_id = :gmail_message_id
            """,
            {
                'gmail_message_id': gmail_message_id,
                'label_name': label_name,
            },
        )


def save_career_event(gmail_message_id, details):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO career_events (
                gmail_message_id,
                company,
                role,
                stage,
                deadline_text,
                deadline_date,
                compensation,
                confidence,
                notes
            )
            VALUES (
                :gmail_message_id,
                :company,
                :role,
                :stage,
                :deadline_text,
                :deadline_date,
                :compensation,
                :confidence,
                :notes
            )
            ON CONFLICT(gmail_message_id) DO UPDATE SET
                company = excluded.company,
                role = excluded.role,
                stage = excluded.stage,
                deadline_text = excluded.deadline_text,
                deadline_date = excluded.deadline_date,
                compensation = excluded.compensation,
                confidence = excluded.confidence,
                notes = excluded.notes,
                updated_at = CURRENT_TIMESTAMP
            """,
            {
                'gmail_message_id': gmail_message_id,
                'company': details.company,
                'role': details.role,
                'stage': details.stage,
                'deadline_text': details.deadline_text,
                'deadline_date': details.deadline_date,
                'compensation': details.compensation,
                'confidence': details.confidence,
                'notes': details.notes,
            },
        )


def delete_career_event(gmail_message_id):
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM career_events WHERE gmail_message_id = :gmail_message_id",
            {'gmail_message_id': gmail_message_id},
        )


def get_career_events(search=''):
    query = """
        SELECT
            c.gmail_message_id,
            c.company,
            c.role,
            c.stage,
            c.deadline_text,
            c.deadline_date,
            c.compensation,
            c.confidence,
            c.notes,
            e.sender,
            e.subject,
            e.snippet,
            e.received_at
        FROM career_events c
        JOIN emails e ON e.gmail_message_id = c.gmail_message_id
        WHERE 1 = 1
    """
    params = {}

    if search:
        query += """
            AND (
                c.company LIKE :search
                OR c.role LIKE :search
                OR c.stage LIKE :search
                OR e.subject LIKE :search
                OR e.snippet LIKE :search
            )
        """
        params['search'] = f"%{search}%"

    query += """
        ORDER BY
            CASE WHEN c.deadline_date IS NULL OR c.deadline_date = '' THEN 1 ELSE 0 END,
            c.deadline_date ASC,
            e.received_at DESC
    """

    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()

    return [dict(row) for row in rows]


def get_career_event_counts():
    with get_connection() as connection:
        total = connection.execute(
            "SELECT COUNT(*) AS total FROM career_events"
        ).fetchone()['total']
        upcoming_deadlines = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM career_events
            WHERE deadline_date IS NOT NULL AND deadline_date != ''
            """
        ).fetchone()['total']
        unknown_companies = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM career_events
            WHERE company = 'Unknown'
            """
        ).fetchone()['total']
        unknown_roles = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM career_events
            WHERE role = 'Unknown'
            """
        ).fetchone()['total']

    return {
        'total': total,
        'upcoming_deadlines': upcoming_deadlines,
        'unknown_companies': unknown_companies,
        'unknown_roles': unknown_roles,
    }


def save_alert(alert_data):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO alerts (
                gmail_message_id,
                alert_type,
                title,
                message,
                severity,
                sender,
                subject
            )
            VALUES (
                :gmail_message_id,
                :alert_type,
                :title,
                :message,
                :severity,
                :sender,
                :subject
            )
            ON CONFLICT(gmail_message_id) DO UPDATE SET
                alert_type = excluded.alert_type,
                title = excluded.title,
                message = excluded.message,
                severity = excluded.severity,
                sender = excluded.sender,
                subject = excluded.subject,
                updated_at = CURRENT_TIMESTAMP
            """,
            alert_data,
        )


def delete_alert_for_email(gmail_message_id):
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM alerts WHERE gmail_message_id = :gmail_message_id",
            {'gmail_message_id': gmail_message_id},
        )


def get_alerts(status='All', search=''):
    query = """
        SELECT
            a.gmail_message_id,
            a.alert_type,
            a.title,
            a.message,
            a.severity,
            a.status,
            a.sender,
            a.subject,
            a.created_at,
            a.read_at,
            a.whatsapp_sent_at,
            a.whatsapp_error,
            e.received_at,
            e.snippet,
            e.category
        FROM alerts a
        JOIN emails e ON e.gmail_message_id = a.gmail_message_id
        WHERE 1 = 1
    """
    params = {}

    if status != 'All':
        query += " AND a.status = :status"
        params['status'] = status

    if search:
        query += """
            AND (
                a.title LIKE :search
                OR a.message LIKE :search
                OR a.sender LIKE :search
                OR a.subject LIKE :search
                OR e.snippet LIKE :search
            )
        """
        params['search'] = f"%{search}%"

    query += """
        ORDER BY
            CASE a.status WHEN 'unread' THEN 0 ELSE 1 END,
            CASE a.severity WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
            e.received_at DESC
    """

    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()

    return [dict(row) for row in rows]


def get_alert_counts():
    with get_connection() as connection:
        total = connection.execute(
            "SELECT COUNT(*) AS total FROM alerts"
        ).fetchone()['total']
        unread = connection.execute(
            "SELECT COUNT(*) AS total FROM alerts WHERE status = 'unread'"
        ).fetchone()['total']
        high = connection.execute(
            "SELECT COUNT(*) AS total FROM alerts WHERE severity = 'high'"
        ).fetchone()['total']
        career = connection.execute(
            "SELECT COUNT(*) AS total FROM alerts WHERE alert_type = 'career'"
        ).fetchone()['total']

    return {
        'total': total,
        'unread': unread,
        'high': high,
        'career': career,
    }


def mark_alert_read(gmail_message_id):
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE alerts
            SET
                status = 'read',
                read_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE gmail_message_id = :gmail_message_id
            """,
            {'gmail_message_id': gmail_message_id},
        )


def mark_alert_unread(gmail_message_id):
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE alerts
            SET
                status = 'unread',
                read_at = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE gmail_message_id = :gmail_message_id
            """,
            {'gmail_message_id': gmail_message_id},
        )


def mark_all_alerts_read():
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE alerts
            SET
                status = 'read',
                read_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE status = 'unread'
            """
        )


def mark_alert_whatsapp_sent(gmail_message_id):
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE alerts
            SET
                whatsapp_sent_at = CURRENT_TIMESTAMP,
                whatsapp_error = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE gmail_message_id = :gmail_message_id
            """,
            {'gmail_message_id': gmail_message_id},
        )


def mark_alert_whatsapp_failed(gmail_message_id, error_message):
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE alerts
            SET
                whatsapp_error = :error_message,
                updated_at = CURRENT_TIMESTAMP
            WHERE gmail_message_id = :gmail_message_id
            """,
            {
                'gmail_message_id': gmail_message_id,
                'error_message': error_message[:500],
            },
        )
