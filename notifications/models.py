from django.db import models


class Notification(models.Model):
    TYPE_CHOICES = [
        ('info',     'Information'),
        ('success',  'Succès'),
        ('warning',  'Avertissement'),
        ('danger',   'Urgent'),
        ('conge',    'Congé'),
        ('paie',     'Paie'),
        ('pointage', 'Pointage'),
        ('planning', 'Planning'),
    ]
    user       = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='notifications')
    titre      = models.CharField(max_length=200)
    message    = models.TextField()
    type       = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    lu         = models.BooleanField(default=False)
    url        = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering     = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"{self.user.username}: {self.titre}"


class PushToken(models.Model):
    user       = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='push_tokens')
    token      = models.CharField(max_length=300)
    platform   = models.CharField(max_length=20, default='expo')
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together  = ('user', 'token')
        verbose_name     = 'Push Token'
        verbose_name_plural = 'Push Tokens'

    def __str__(self):
        return f"{self.user.username}: {self.token[:40]}..."
