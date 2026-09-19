import csv
from django.http import HttpResponse
from .models import Notification

def send_system_notification(user, title, message, notification_type='ANNOUNCEMENT', link=''):
    """Utility function to create an in-app notification for a user."""
    if not user:
        return None
    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link
    )

def export_queryset_to_csv(queryset, field_names, header_labels, filename="export.csv"):
    """Export Django queryset dynamically into downloadable CSV file with UTF-8 encoding."""
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(header_labels)

    for obj in queryset:
        row = []
        for field in field_names:
            val = obj
            for part in field.split('__'):
                if hasattr(val, part):
                    val = getattr(val, part)
                    if callable(val):
                        val = val()
                else:
                    val = ''
                    break
            row.append(str(val) if val is not None else '')
        writer.writerow(row)

    return response
