import pandas as pd
from kripton.datasources.clickhouse import client

def load_csv_to_clickhouse(file_path, table_name):
    df = pd.read_csv(file_path)

    # создать таблицу
    columns = ", ".join([f"{col} String" for col in df.columns])
    client.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns}) ENGINE = MergeTree ORDER BY tuple()")

    # загрузить данные
    client.execute(
        f"INSERT INTO {table_name} VALUES",
        df.to_dict('records')
    )

    return df.head(50)
