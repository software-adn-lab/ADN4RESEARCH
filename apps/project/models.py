from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Project(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_projects')
    research_framework = models.ForeignKey(
        'design.ResearchFramework', 
        on_delete=models.PROTECT, 
        related_name='projects', 
        null=True, 
        blank=True
    )

    def __str__(self):
        return self.name
    
    def add_member(self, user, role):
        try:
            # Puedo verificar que no se agregue dos veces el mismo usuario al proyecto
            if not Membership.objects.filter(project=self, user=user).exists():
                Membership.objects.create(project=self, user=user, role=role)
        except Exception as e:
            print(f"Error adding member: {e}")
    
    def get_members(self):
        return Membership.objects.filter(project=self)

        
class Membership(models.Model):
    ROLE_CHOICES = [
        ('OWNER', 'Owner'),
        ('RESEARCHER', 'Researcher'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project', 'user')

class Stage(models.Model):
    class Status(models.TextChoices):
        INACTIVE = 'INACTIVE', 'Inactive'
        OPEN = 'OPENED', 'Opened'
        CLOSED = 'CLOSED', 'Closed'

    opened_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='opened_stages')
    closed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='closed_stages')
    due_time = models.DateTimeField(null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='stages', default=None, null=True, blank=True)
    name = models.CharField(max_length=100)
    status = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.name} - {self.project.name}"
