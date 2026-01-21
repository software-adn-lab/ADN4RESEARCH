"""
Services - Core Bounded Context

Application services that orchestrate use cases related
to paper and quote extraction.
"""
from typing import Dict
import logging
from typing import Tuple

from .models import PaperExtraction, PaperExtractionStatusChoices
from apps.extraction.shared.exceptions import BusinessRuleViolation

logger = logging.getLogger(__name__)

class PaperExtractionService:
    """
    Application service for paper extraction management.
    
    Responsibilities:
    - Orchestrate business validations
    - Manage state transitions
    - Coordinate operations between multiple entities
    """
    
    def validate_completion_rules(self, paper: PaperExtraction) -> Tuple[bool, str]:
        """
        Validates business rules for completing a paper.
        """
        # 
        logger.debug(
            "Starting completion rule validation",
            extra={
                "paper_id": paper.id,
                "paper_status": paper.status,
            }
        )

        # Rule 1: At least one quote
        if not paper.quotes.exists():
            logger.info(
                "Validation failed: paper without quotes",
                extra={
                    "paper_id": paper.id,
                    "rule": "at_least_one_quote",
                }
            )
            return False, (
                "The paper must have at least one extraction (quote). "
                "Select text from the PDF and create quotes before finishing."
            )

        logger.debug(
            "Rule 1 OK: paper has at least one quote",
            extra={"paper_id": paper.id}
        )

        # Rule 2: Mandatory tags coverage
        missing_tags = paper.get_missing_mandatory_tags()
        mandatory_tags = paper.extraction_phase.tags.mandatory()
        logger.info(
            "Mandatory tags status",
            extra={
                "paper_id": paper.id,
                "mandatory_total": mandatory_tags.count(),
                "used_tag_ids": list(
                    paper.quotes.values_list("tags__id", flat=True).distinct()
                ),
            }
        )

        if missing_tags.exists():
            missing_count = missing_tags.count()
            tag_names = ", ".join(tag.name for tag in missing_tags[:3])
            logger.info(
                "Missing mandatory tags detail",
                extra={
                    "paper_id": paper.id,
                    "missing_tag_ids": list(missing_tags.values_list("id", flat=True)),
                }
            )

            if missing_count > 3:
                tag_names += f" (+{missing_count - 3} more)"

            logger.info(
                "Validation failed: missing mandatory tags",
                extra={
                    "paper_id": paper.id,
                    "rule": "mandatory_tags",
                    "missing_tags_count": missing_count,
                    "missing_tags_preview": tag_names,
                }
            )

            return False, (
                f"Missing mandatory tags: {tag_names}. "
                f"Add quotes with these tags before finishing."
            )

        logger.debug(
            "Rule 2 OK: all mandatory tags are covered",
            extra={"paper_id": paper.id}
        )

        # Rule 3: Valid status
        valid_statuses = [
            PaperExtractionStatusChoices.PENDING,
            PaperExtractionStatusChoices.IN_PROGRESS,
        ]

        if paper.status not in valid_statuses:
            logger.warning(
                "Validation failed: invalid status for completing paper",
                extra={
                    "paper_id": paper.id,
                    "rule": "valid_status",
                    "current_status": paper.status,
                }
            )

            return False, (
                f"Cannot complete a paper in status '{paper.get_status_display()}'. "
                f"Only papers in progress can be completed."
            )

        logger.info(
            "Completion validation successful",
            extra={
                "paper_id": paper.id,
                "final_status": paper.status,
            }
        )

        return True, ""
    
    def attempt_complete_paper(self, paper: PaperExtraction, user) -> PaperExtraction:
        """
        Orchestrates the process of completing a paper.
        
        Business Rules:
        - Execute all validations
        - Register state transition
        - Generate domain events (future)
        
        Args:
            paper: PaperExtraction to complete
            user: User requesting completion
            
        Returns:
            Updated PaperExtraction
            
        Raises:
            BusinessRuleViolation: If business rules are not met
            
        """
        logger.info(
            f"Attempting to complete paper: "
            f"paper_id={paper.id}, user={user.username}, "
            f"current_status={paper.status}"
        )
        
        # 1. Validate business rules
        is_valid, error_message = self.validate_completion_rules(paper)
        logger.debug(
            f"Completion validation result: "
            f"paper_id={paper.id}, is_valid={is_valid}, "
            f"error_message={error_message}"
        )
        
        if not is_valid:
            logger.warning(
                f"Paper completion validation failed: "
                f"paper_id={paper.id}, reason={error_message}"
            )
            raise BusinessRuleViolation(error_message)
        
        # 2. Perform state transition
        previous_status = paper.status
        paper.status = PaperExtractionStatusChoices.COMPLETED
        paper.save(update_fields=['status', 'updated_at'])
        
        logger.info(
            f"Paper completed successfully: "
            f"paper_id={paper.id}, "
            f"previous_status={previous_status}, "
            f"new_status={paper.status}, "
            f"quotes_count={paper.quotes.count()}, "
            f"completed_by={user.username}"
        )
        
        # 3. (Future) Generate domain events
        # self._emit_paper_completed_event(paper, user)
        
        return paper
    
    def get_completion_summary(self, paper: PaperExtraction) -> dict:
        """
        Retrieves a summary of the paper's completion status.
        
        Args:
            paper: PaperExtraction to analyze
            
        Returns:
            dict with completion information
        """
        logger.info(
            "Building completion summary: paper_id=%s, status=%s",
            paper.id,
            paper.status
        )
        mandatory_tags = paper.extraction_phase.tags.mandatory()
        
        used_mandatory_tags = paper.get_used_mandatory_tags()
        missing_mandatory_tags = paper.get_missing_mandatory_tags()
        
        total_mandatory = mandatory_tags.count()
        covered_mandatory = used_mandatory_tags.count()
        
        coverage_percent = (
            int((covered_mandatory / total_mandatory) * 100)
            if total_mandatory > 0
            else 100
        )
        
        is_valid, validation_message = self.validate_completion_rules(paper)
        logger.info(
            "Completion summary computed: paper_id=%s, can_complete=%s, "
            "coverage=%s/%s, missing=%s",
            paper.id,
            is_valid,
            covered_mandatory,
            total_mandatory,
            missing_mandatory_tags.count()
        )
        
        return {
            'can_complete': is_valid,
            'validation_message': validation_message,
            'quotes_count': paper.quotes.count(),
            'mandatory_tags_total': total_mandatory,
            'mandatory_tags_covered': covered_mandatory,
            'mandatory_tags_missing': missing_mandatory_tags.count(),
            'coverage_percentage': coverage_percent,
            'is_fully_compliant': missing_mandatory_tags.count() == 0,
            'missing_tags': [
                {'id': tag.id, 'name': tag.name}
                for tag in missing_mandatory_tags
            ]
        }