"""
Acquisition Module Adapter

Centralizes communication with the Acquisition module.
Provides clean interface for Extraction to access acquired studies and PDFs.

Architecture:
- Studies are acquired in the Selection phase (not here)
- This adapter provides access to existing PDFs for display in Extraction UI
- All PDF URLs are generated using default_storage (FileSystem or S3 compatible)
"""
import logging
from typing import Optional, List, Dict, Any
from django.core.files.storage import default_storage

from apps.acquisition.facade import get_acquisition_facade

logger = logging.getLogger(__name__)


class AcquisitionAdapter:
    """
    Adapter for accessing studies acquired in Selection phase.
    
    Responsible for:
    - Getting PDF URLs for existing studies (for UI display)
    """

    def __init__(self):
        self._facade = get_acquisition_facade()

    def get_study_pdf_url(self, study_id: str, project_id: int) -> Optional[str]:
        """
        Get PDF URL for a study already acquired in Selection phase.
        
        The PDF file is already stored in StudyModel.pdf_path.
        This method only generates the accessible URL using default_storage.
        
        Args:
            study_id: Study UUID (from PaperExtraction.study_id)
            project_id: The ID of the project.
            
        Returns:
            PDF URL string or None if PDF not available
        """
        try:
            # Use facade to get all studies for the project
            project_studies = self._facade.get_studies_by_project(project_id)
            
            # Find the specific study
            study_data = next((s for s in project_studies if s['id'] == study_id), None)

            if not study_data or not study_data.get('pdf_path'):
                logger.debug(f"[ACQUISITION ADAPTER] Study {study_id} not found in project {project_id} or has no PDF path.")
                return None
            
            # Generate URL from the path
            pdf_url = default_storage.url(study_data['pdf_path'])
            logger.debug(f"[ACQUISITION ADAPTER] Generated PDF URL for study {study_id}: {pdf_url}")
            
            return pdf_url
            
        except Exception as e:
            logger.error(f"[ACQUISITION ADAPTER] Failed to get PDF URL for study {study_id}: {e}", exc_info=True)
            return None
    
    def enrich_studies(self, study_ids: List[str]) -> Dict[str, Any]:
        """
        Enrich study metadata (consolidate author info, abstract, keywords, etc.).
        
        Args:
            study_ids: List of study UUIDs to enrich
            
        Returns:
            Dict with enrichment status
        """
        try:
            result = self._facade.enrich_studies(study_ids)
            
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

    def upload_study_pdf(
        self,
        study_id: str,
        file_obj: Any,
        filename: str,
        user: Any,
    ) -> Dict[str, Any]:
        """
        Uploads a new PDF for a study.
        
        Args:
            study_id: The UUID of the study.
            file_obj: The file object to upload.
            filename: The name of the file.
            user: The user performing the upload.
            
        Returns:
            A dictionary with the result of the upload.
        """
        try:
            logger.info(
                f"[ACQUISITION ADAPTER] Uploading new PDF for study {study_id} by user {user.username}"
            )
            # Use force=True to allow replacing existing PDFs
            result = self._facade.upload_study_pdf(
                study_id=study_id,
                file_obj=file_obj,
                filename=filename,
                user=user,
                force=True
            )
            return result
        except Exception as e:
            logger.error(
                f"[ACQUISITION ADAPTER] Failed to upload PDF for study {study_id}: {e}",
                exc_info=True
            )
            raise


def get_acquisition_adapter() -> AcquisitionAdapter:
    """Factory function to get AcquisitionAdapter instance."""
    return AcquisitionAdapter()