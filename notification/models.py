from django.db import models


class NotificationLog(models.Model):
	event_id = models.CharField(max_length=64, unique=True)
	event_type = models.CharField(max_length=80)
	target_email = models.EmailField()
	status = models.CharField(max_length=32, default="PENDING")
	detail = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		app_label = "notification"
