"""
Selection Module Adapter

Centralizes communication with the Selection module.
Provides clean interface for Extraction to consume selection results.
"""
import logging
from typing import List

logger = logging.getLogger(__name__)


class SelectionAdapter:
    """
    Adapter for Selection module integration.
    
    Responsible for:
    - Getting approved papers from selection phase
    - Converting selection results to extraction domain format
    """

    @staticmethod
    def get_approved_papers(project_id: int) -> List[str]:
        """
        Get list of papers approved in selection phase.
        
        Calls the Selection module to retrieve papers that passed
        screening and fulltext review phases.
        
        Args:
            project_id: Project ID
            
        Returns:
            List of paper UUIDs approved in selection phase
            
        Raises:
            Exception: If selection module is unavailable
        """
        try:
            from apps.selection.services import SelectionFacade
            
            facade = SelectionFacade()
            approved_papers = facade.get_approved_fulltext_papers(project_id)
            
            logger.info(
                f"[SELECTION ADAPTER] Retrieved {len(approved_papers)} "
                f"approved papers for project {project_id}"
            )
            
            return approved_papers
            
        except Exception as e:
            logger.error(
                f"[SELECTION ADAPTER] Failed to get approved papers: {e}",
                exc_info=True
            )
            raise
    
    @staticmethod
    def is_selection_complete(project_id: int) -> bool:
        """
        Check if selection phase is fully complete.
        
        Args:
            project_id: Project ID
            
        Returns:
            True if selection (screening + fulltext + discussions) is complete
        """
        try:
            from apps.selection.services import SelectionFacade
            
            facade = SelectionFacade()
            is_complete = facade.is_selection_complete(project_id)
            
            logger.info(
                f"[SELECTION ADAPTER] Selection phase complete: {is_complete} "
                f"for project {project_id}"
            )
            
            return is_complete
            
        except Exception as e:
            logger.error(
                f"[SELECTION ADAPTER] Failed to check selection completion: {e}",
                exc_info=True
            )
            return False


def get_selection_adapter() -> SelectionAdapter:
    """Factory function to get SelectionAdapter instance."""
    return SelectionAdapter()
