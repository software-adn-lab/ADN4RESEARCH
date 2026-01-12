#!/usr/bin/env python
"""
Setup test data for selection phase testing
"""
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.project.structure.models.project_models import Project, Membership
from django.contrib.auth.models import User

def main():
    # Get or create test users
    users_data = [
        ('researcher1', 'pass123', 'Ana', 'García', 20),
        ('researcher2', 'pass123', 'Carlos', 'López', 15),
        ('researcher3', 'pass123', 'María', 'Fernández', 10),
    ]

    project = Project.objects.first()
    if not project:
        print("No project found. Please create a project first.")
        return
    
    print(f'Setting up test data for project: {project.title}')

    for username, password, first_name, last_name, workload in users_data:
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
            }
        )
        if created:
            user.set_password(password)
            user.save()
            print(f'Created user: {username}')
        else:
            print(f'User exists: {username}')
        
        # Update or create membership
        membership, m_created = Membership.objects.update_or_create(
            user=user,
            project=project,
            defaults={'workload_hours': workload, 'role': 'RESEARCHER'}
        )
        action = 'Created' if m_created else 'Updated'
        print(f'  {action} membership: {user.username} - {membership.workload_hours}h (role: {membership.role})')

    print('\n=== Summary ===')
    members = Membership.objects.filter(project=project)
    print(f'Total members: {members.count()}')
    total_hours = sum(m.workload_hours for m in members)
    print(f'Total workload hours: {total_hours}')
    
    print('\nMembers:')
    for m in members:
        print(f'  - {m.user.get_full_name() or m.user.username}: {m.workload_hours}h ({m.role})')

if __name__ == '__main__':
    main()
