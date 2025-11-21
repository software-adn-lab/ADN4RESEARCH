from django.conf import settings
from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class ResearchFramework(models.Model):
    name = models.CharField(max_length=50)
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='custom_frameworks', default=None)
    fields_data = models.JSONField(default=dict)

    class Meta:
        unique_together = ('name', 'assigned_by')  

    @property
    def fields_completed(self):
        return sum(1 for f in self.fields_data.values() if f and str(f).strip())
    @property
    def total_fields(self):
        """Calcula automáticamente el número total de campos"""
        return len(self.fields_data) if self.fields_data else 0
    
    @property
    def is_complete(self):
        return self.fields_completed == self.total_fields
    
    def get_allowed_keys(self):
        return self.fields_data.keys()

    def __str__(self):
        prefix = "Global" if self.is_global else "Custom"
        return f"{prefix} Framework: {self.name}"
    
class Project(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_projects')
    research_framework = models.ForeignKey(
        ResearchFramework, 
        on_delete=models.PROTECT, 
        related_name='projects', 
        default=None
    )

    def __str__(self):
        return self.name
    
    def add_member(self, user, role):
        try:
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
     