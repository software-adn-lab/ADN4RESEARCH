from django.core.exceptions import ValidationError
from django.utils import timezone
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
        return f"Framework: {self.name}"
    
class Project(models.Model):
    title = models.CharField(max_length=100)
    summary = models.TextField()
    motivation = models.TextField()
    general_objective = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_projects')
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    research_framework = models.ForeignKey(
        ResearchFramework, 
        on_delete=models.PROTECT, 
        related_name='projects', 
        null=True,
        blank=True
    )
    
    @property
    def protocol_questions(self):
        return self.design_phase.research_questions.filter(status='APPROVED')

    def __str__(self):
        return self.title
    
    def add_member(self, user, role, workload=0):
        try:
            if not Membership.objects.filter(project=self, user=user).exists():
                Membership.objects.create(project=self, user=user, role=role, workload_hours=workload)
        except Exception as e:
            print(f"Error adding member: {e}")
    
    def get_members(self):
        return Membership.objects.filter(project=self)

class SpecificObjective(models.Model):
    project = models.ForeignKey(Project, related_name='specific_objectives', on_delete=models.CASCADE)
    description = models.TextField()

    def __str__(self):
        return self.description[:60]

class ExpectedResult(models.Model):
    project = models.ForeignKey(Project, related_name='expected_results', on_delete=models.CASCADE)
    description = models.TextField()

    def __str__(self):
        return self.description[:60]
        
class Membership(models.Model): 
    ROLE_CHOICES = [
        ('OWNER', 'Owner'),
        ('RESEARCHER', 'Researcher'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    workload_hours = models.PositiveIntegerField(
        default=0,
        help_text="Weekly workload hours for this researcher in this project"
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project', 'user')

class BasePhase(models.Model): # Clase abstracta para las phases
    is_active = models.BooleanField(default=False)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        abstract = True 