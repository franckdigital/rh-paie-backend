"""Helpers partagés pour l'export CSV dans les ViewSets DRF."""
import csv
from django.http import HttpResponse


def csv_response(filename: str, headers: list[str], rows) -> HttpResponse:
    """
    Construit une réponse CSV streamée.
    rows : itérable de listes/tuples dans le même ordre que headers.
    """
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return response
