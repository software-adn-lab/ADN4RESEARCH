"""
Project Adapter
Centralizes access to Project module functionality (Project, Membership, etc).
"""
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class ProjectAdapter:
    """
    ACL for Project module.
    Provides access to project structure and membership information.
    """

    def get_project_members(self, project_id: int) -> List[Dict]:
        """
        Gets all members of a project including the owner.
        
        Args:
            project_id: Project ID
            
        Returns:
            List of dicts with 'id' and 'username' keys
        """
        try:
            from apps.project.structure.models.project_models import Project, Membership

            project = Project.objects.get(id=project_id)
            
            # Start with the project owner
            members = [
                {'id': project.owner.id, 'username': project.owner.username}
            ]
            
            # Add other team members
            team_members = Membership.objects.filter(
                project=project
            ).select_related('user')
            
            members.extend([
                {'id': m.user.id, 'username': m.user.username}
                for m in team_members
            ])
            
            logger.info(f"Retrieved {len(members)} members for project {project_id}")
            return members
            
        except Exception as e:
            logger.error(f"Error getting project members: {str(e)}", exc_info=True)
            return []


def get_project_adapter() -> ProjectAdapter:
    """Factory function for ProjectAdapter."""
    return ProjectAdapter()
