"""
Acquisition Module Adapter

Centralizes communication with the Acquisition module.
Provides clean interface for Extraction to access acquired studies and PDFs.
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class AcquisitionAdapter:
    """
    Adapter for Acquisition module integration.
    
    Responsible for:
    - Getting studies by project
    - Downloading full texts (PDFs)
    - Accessing study metadata
    """

    @staticmethod
    def get_studies_by_project(
        project_id: int,
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all studies acquired for a project.
        
        Args:
            project_id: Project ID
            include_metadata: Whether to include full metadata
            
        Returns:
            List of study dicts with id, title, status, etc.
        """
        try:
            from apps.acquisition.facade import get_acquisition_facade
            
            facade = get_acquisition_facade()
            studies = facade.get_studies_by_project(
                project_id=project_id,
                include_metadata=include_metadata
            )
            
            logger.info(
                f"[ACQUISITION ADAPTER] Retrieved {len(studies)} studies "
                f"for project {project_id}"
            )
            
            return studies
            
        except Exception as e:
            logger.error(
                f"[ACQUISITION ADAPTER] Failed to get studies: {e}",
                exc_info=True
            )
            raise

    @staticmethod
    def download_fulltexts(study_ids: List[str]) -> Dict[str, Any]:
        """
        Download full text PDFs for studies.
        
        Triggers the acquisition workflow to:
        1. Check Open Access availability
        2. Download PDFs from available sources
        3. Store in configured storage (filesystem or S3)
        
        Args:
            study_ids: List of study UUIDs to download
            
        Returns:
            Dict with download status (downloaded_count, failed_count, etc.)
        """
        try:
            from apps.acquisition.facade import get_acquisition_facade
            
            facade = get_acquisition_facade()
            result = facade.download_fulltexts(study_ids)
            
            logger.info(
                f"[ACQUISITION ADAPTER] Downloaded {result.downloaded_count} PDFs "
                f"(failed: {result.failed_count})"
            )
            
            return {
                'total_count': result.total_count,
                'downloaded_count': result.downloaded_count,
                'available_count': result.available_count,
                'failed_count': result.failed_count,
                'study_statuses': result.study_statuses
            }
            
        except Exception as e:
            logger.error(
                f"[ACQUISITION ADAPTER] Failed to download fulltexts: {e}",
                exc_info=True
            )
            raise
    
    @staticmethod
    def enrich_studies(study_ids: List[str]) -> Dict[str, Any]:
        """
        Enrich study metadata (consolidate author info, abstract, keywords, etc.).
        
        Args:
            study_ids: List of study UUIDs to enrich
            
        Returns:
            Dict with enrichment status
        """
        try:
            from apps.acquisition.facade import get_acquisition_facade
            
            facade = get_acquisition_facade()
            result = facade.enrich_studies(study_ids)
            
            logger.info(
                f"[ACQUISITION ADAPTER] Enriched {result.enriched_count} studies"
            )
            
            return {
                'enriched_count': result.enriched_count,
                'failed_count': result.failed_count,
                'study_ids': result.study_ids
            }
            
        except Exception as e:
            logger.error(
                f"[ACQUISITION ADAPTER] Failed to enrich studies: {e}",
                exc_info=True
            )
            raise


def get_acquisition_adapter() -> AcquisitionAdapter:
    """Factory function to get AcquisitionAdapter instance."""
    return AcquisitionAdapter()
