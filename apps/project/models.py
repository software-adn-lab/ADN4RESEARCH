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
    name = models.CharField(max_length=100)
    description = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_projects')
    research_framework = models.ForeignKey(
        ResearchFramework, 
        on_delete=models.PROTECT, 
        related_name='projects', 
        default=None
    )
    
    @property
    def protocol_questions(self):
        return self.research_questions.filter(status='APPROVED') 

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
        
class ProjectPhase(models.Model):
    class PhaseType(models.TextChoices):
        DESIGN = 'DESIGN', 'Design Phase'

    class Stage(models.TextChoices):
        RQ_CREATION = 'RQ_CREATION', 'Research Question Creation'
        RQ_DISCUSSION = 'RQ_DISCUSSION', 'Discussion'
        CRITERIA_DEFINITION = 'CRITERIA_DEFINITION', 'Eligibility Criteria Definition' 
        SEARCH_STRATEGY = 'SEARCH_STRATEGY', 'Search Strategy Building'
        FINISHED = 'FINISHED', 'Finalized'

    STAGES_FLOW = {
        PhaseType.DESIGN: [
            Stage.RQ_CREATION, 
            Stage.RQ_DISCUSSION, 
            Stage.CRITERIA_DEFINITION,
            Stage.SEARCH_STRATEGY,
            Stage.FINISHED
        ],
    }

    project = models.ForeignKey('project.Project', related_name='phases', on_delete=models.CASCADE)
    phase_type = models.CharField(max_length=20, choices=PhaseType.choices)
    current_stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.RQ_CREATION)
    
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('project', 'phase_type')

    def clean(self):
        """Valida que la etapa asignada sea válida para esta fase"""
        valid_stages = self.STAGES_FLOW.get(self.phase_type, [])
        if self.current_stage not in valid_stages:
            raise ValidationError(f"Etapa inválida para fase {self.phase_type}")

    def save(self, *args, **kwargs):
        self.full_clean()
        # Si llegamos a FINISHED, cerramos la fase automáticamente
        if self.current_stage == self.Stage.FINISHED:
            self.is_active = False
            self.end_date = timezone.now()
        super().save(*args, **kwargs)
     