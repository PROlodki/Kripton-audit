# Подключение ClickHouse к Django (Kripton-audit)

## Зачем нужен ClickHouse в этом проекте

ClickHouse — колоночная СУБД для **аналитики и больших объёмов записей**. В Kripton-audit он уже используется для:
- загрузки и предпросмотра данных из CSV (datasources);
- хранения ссылок на таблицы/запросы в отчётах (`Report.clickhouse_table`, `Report.clickhouse_query`).

Дополнительно в ClickHouse логично хранить:
- **Логи аудита** (`AuditLog`) — много записей, частые выборки по времени и типу действия;
- **Сырые данные отчётов** — большие выборки для дашбордов и экспорта.

---

## 1. Что нужно сделать

### 1.1 Установить ClickHouse

**Windows (через Docker, рекомендуется):**
```bash
docker run -d --name clickhouse-server -p 8123:8123 -p 9000:9000 clickhouse/clickhouse-server
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install -y apt-transport-https ca-certificates dirmngr
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 8919F6BD2B48D754
echo "deb https://packages.clickhouse.com/deb stable main" | sudo tee /etc/apt/sources.list.d/clickhouse.list
sudo apt-get update && sudo apt-get install -y clickhouse-server clickhouse-client
sudo service clickhouse-server start
```

Проверка: открыть в браузере `http://localhost:8123` — должна вернуться строка `Ok`.

### 1.2 Зависимости Python (уже есть в `requirements.txt`)

- `clickhouse-driver` — нативный клиент (у вас уже используется в `kripton/datasources/clickhouse.py`).
- `django-clickhouse` — опционально, если нужны модели ClickHouse в стиле Django ORM и миграции.

Для текущей схемы достаточно **clickhouse-driver**.

### 1.3 Настройки Django

В `kripton/settings.py` заданы переменные (можно переопределить через переменные окружения):

```python
CLICKHOUSE_HOST = os.environ.get('CLICKHOUSE_HOST', 'localhost')
CLICKHOUSE_PORT = int(os.environ.get('CLICKHOUSE_PORT', '9000'))
CLICKHOUSE_USER = os.environ.get('CLICKHOUSE_USER', 'default')
CLICKHOUSE_PASSWORD = os.environ.get('CLICKHOUSE_PASSWORD', '')
CLICKHOUSE_DB = os.environ.get('CLICKHOUSE_DB', 'default')
```

### 1.4 Подключение и таблицы в коде

- **Клиент:** `kripton/datasources/clickhouse.py` — `get_client()`, `client` (ленивый), `execute_safe()` для запросов без падения при недоступности CH.
- **Схема таблиц:** `kripton/clickhouse_schema.py` — DDL для `audit_log` и `report_request_events`.
- **Создание таблиц:** выполнить один раз после запуска ClickHouse:
  ```bash
  python manage.py clickhouse_init
  ```
- **Запись данных:**
  - Логи аудита дублируются в ClickHouse из `log_audit()` (с полями подразделения при передаче `department_id`, `department_name`, `department_code`).
  - Заявки на отчёты пишутся в `report_request_events` по сигналу `post_save` модели `ReportRequest` (см. `Reports/signals.py`).

Для продакшена вынесите их в `.env` и читайте через `os.environ` / `python-dotenv`, например:

```python
import os
CLICKHOUSE_HOST = os.getenv('CLICKHOUSE_HOST', 'localhost')
CLICKHOUSE_PORT = int(os.getenv('CLICKHOUSE_PORT', 9000))
CLICKHOUSE_USER = os.getenv('CLICKHOUSE_USER', 'default')
CLICKHOUSE_PASSWORD = os.getenv('CLICKHOUSE_PASSWORD', '')
CLICKHOUSE_DB = os.getenv('CLICKHOUSE_DB', 'default')
```

### 1.4 Единая точка подключения (как у вас сейчас)

Файл `kripton/datasources/clickhouse.py` создаёт один клиент при импорте. Для продакшена можно добавить порт и таймаут:

```python
from clickhouse_driver import Client
from django.conf import settings

client = Client(
    host=settings.CLICKHOUSE_HOST,
    port=getattr(settings, 'CLICKHOUSE_PORT', 9000),
    user=settings.CLICKHOUSE_USER,
    password=settings.CLICKHOUSE_PASSWORD,
    database=settings.CLICKHOUSE_DB,
    connect_timeout=10,
)
```

Если ClickHouse недоступен, импорт упадёт. Чтобы приложение стартовало и без ClickHouse, можно создавать клиент лениво или оборачивать вызовы в try/except и возвращать пустой результат (как отмечено в комментарии в settings).

---

## 2. Какие данные хранить в ClickHouse

| Данные | Где сейчас | Рекомендация |
|--------|------------|--------------|
| **Логи аудита** | PostgreSQL/SQLite (`AuditLog`) | Дублировать или перенести в ClickHouse для быстрой аналитики по времени, пользователю, типу действия. |
| **Таблицы из CSV (datasources)** | Только ClickHouse | Оставить как есть: загрузка через `load_csv_to_clickhouse`, предпросмотр через `preview_table`. |
| **Результаты отчётов** | `Report.data` (JSON), `Report.file`, плюс `clickhouse_table` / `clickhouse_query` | Объёмные выборки держать в ClickHouse; в Django хранить только ссылку (таблица/запрос) и метаданные. |
| **Пользователи, отделы, отчёты, запросы** | Django (PostgreSQL/SQLite) | Оставить в основной БД — это операционные данные, не аналитика. |

### 2.1 Пример: таблица логов аудита в ClickHouse

Создать таблицу (один раз, вручную или миграцией/скриптом):

```sql
CREATE TABLE IF NOT EXISTS audit_log (
    timestamp DateTime64(3),
    user_id Nullable(Int64),
    action_type String,
    resource_type String,
    resource_id String,
    details String,
    ip_address Nullable(String),
    user_agent String
) ENGINE = MergeTree()
ORDER BY (timestamp, action_type)
TTL timestamp + INTERVAL 1 YEAR;
```

Дублирование из Django в ClickHouse — в сигнале `post_save` модели `AuditLog` или в сервисе логирования: формировать строку и делать `client.execute('INSERT INTO audit_log ...', [row])`. Либо писать в очередь (Redis/Celery), а воркер — в ClickHouse.

### 2.2 Данные отчётов

- В Django в `Report` хранить: `clickhouse_table`, `clickhouse_query`, метаданные (название, тип, кто создал, даты).
- Большие результаты отчётов держать в таблицах ClickHouse (как сейчас загружаются CSV в `datasource_{pk}`). При открытии отчёта выполнять `clickhouse_query` и отдавать данные в API или в файл.

---

## 3. Краткий чеклист

1. Установить и запустить ClickHouse (Docker или пакетами).
2. Проверить настройки `CLICKHOUSE_*` в `settings.py` (при необходимости вынести в `.env`).
3. Убедиться, что `kripton/datasources/clickhouse.py` подключается (например, выполнить `client.execute('SELECT 1')`).
4. Решить, что именно хранить в ClickHouse:
   - уже хранятся: таблицы datasources, ссылки в отчётах;
   - при необходимости добавить: копию логов аудита, большие результаты отчётов.
5. Для продакшена: порт, таймауты, обработка недоступности ClickHouse и секреты из переменных окружения.

После этого подключение ClickHouse к Django в вашем проекте будет полностью настроено, а решение «что хранить» — согласовано с текущей архитектурой (операционные данные в Django, аналитика и объёмные данные в ClickHouse).
