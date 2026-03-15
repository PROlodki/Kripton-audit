"""
Схема таблиц ClickHouse для отчётов и дашбордов.
Создание таблиц: python manage.py clickhouse_init
"""
from kripton.datasources.clickhouse import get_client


# DDL для таблиц (ORDER BY и партиционирование под аналитические запросы по времени)
AUDIT_LOG_TABLE = "audit_log"
AUDIT_LOG_DDL = f"""
CREATE TABLE IF NOT EXISTS {AUDIT_LOG_TABLE} (
    timestamp DateTime64(3),
    user_id Nullable(Int64),
    username String DEFAULT '',
    action_type String,
    resource_type String DEFAULT '',
    resource_id String DEFAULT '',
    details String DEFAULT '{{}}',
    ip_address Nullable(String),
    user_agent String DEFAULT '',
    department_id Nullable(Int64),
    department_name String DEFAULT '',
    department_code String DEFAULT ''
) ENGINE = MergeTree()
ORDER BY (timestamp, action_type)
TTL timestamp + INTERVAL 2 YEAR
SETTINGS index_granularity = 8192;
"""

REPORT_REQUEST_EVENTS_TABLE = "report_request_events"
REPORT_REQUEST_EVENTS_DDL = f"""
CREATE TABLE IF NOT EXISTS {REPORT_REQUEST_EVENTS_TABLE} (
    event_date Date,
    created_at DateTime64(3),
    request_id Int64,
    requester_id Nullable(Int64),
    requester_name String DEFAULT '',
    department_id Nullable(Int64),
    department_name String DEFAULT '',
    department_code String DEFAULT '',
    report_type_id Nullable(Int64),
    report_type_name String DEFAULT '',
    report_type_code String DEFAULT '',
    status String,
    title String DEFAULT '',
    approved_at Nullable(DateTime64(3)),
    completed_at Nullable(DateTime64(3))
) ENGINE = MergeTree()
ORDER BY (event_date, department_id, status)
TTL event_date + INTERVAL 2 YEAR
SETTINGS index_granularity = 8192;
"""


def init_clickhouse_tables():
    """Создать все таблицы в ClickHouse. Вызывается из management command."""
    c = get_client()
    c.execute(AUDIT_LOG_DDL)
    c.execute(REPORT_REQUEST_EVENTS_DDL)
    return [AUDIT_LOG_TABLE, REPORT_REQUEST_EVENTS_TABLE]
