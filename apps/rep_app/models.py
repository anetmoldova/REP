from django.db import models

# Create your models here.

class Product(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='uploads/')

class ChatSession(models.Model):
    user_id = models.CharField(max_length=100)  # or models.ForeignKey to auth.User
    summary = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session {self.id} for {self.user_id}"

class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10)  # 'user' or 'ai'
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)