# эндпоинт для предпросмотра

from .clickhouse import client

def preview_table(table_name, limit=50):
    query = f"SELECT * FROM {table_name} LIMIT {limit}"
    return client.execute(query)


class PreviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        datasource = DataSource.objects.get(pk=pk, user=request.user)
        table = f"datasource_{pk}"

        rows = preview_table(table)
        return Response({"rows": rows})
