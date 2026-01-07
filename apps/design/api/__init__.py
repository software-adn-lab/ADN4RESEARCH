"""
Design API - Public Interface.

This module exposes the public API for Design module.
Other modules (Project, Acquisition, Selection, Extraction) should ONLY import from here.

USAGE EXAMPLE:
    # Use factory functions (recommended - avoids circular imports)
    from apps.design.api import get_design_management, get_design_protocol
    
    design_mgmt = get_design_management()
    design_mgmt.initialize_design_phase(project_id)
    
    design_protocol = get_design_protocol()
    questions = design_protocol.get_protocol_questions(project_id)
"""

from .contracts import IDesignManagement, IDesignProtocol
from .dtos import QuestionDTO, CriterionDTO, DesignScheduleDTO

# NOTE: Providers imported inside factory functions to avoid circular imports
# DO NOT import providers at module level!


def get_design_management() -> IDesignManagement:
    """
    Factory function to get Design management instance.

    This function uses lazy initialization to avoid circular imports.
    Import happens at runtime (when called), not at module load time.

    Returns:
        IDesignManagement: Instance of design management provider

    Example:
        design_mgmt = get_design_management()
        design_mgmt.initialize_design_phase(project_id)
    """
    from .providers import DesignManagementProvider
    return DesignManagementProvider()


def get_design_protocol() -> IDesignProtocol:
    """
    Factory function to get Design protocol instance.

    This function uses lazy initialization to avoid circular imports.

    Returns:
        IDesignProtocol: Instance of design protocol provider

    Example:
        design_protocol = get_design_protocol()
        questions = design_protocol.get_protocol_questions(project_id)
    """
    from .providers import DesignProtocolProvider
    return DesignProtocolProvider()


__all__ = [
    # Interfaces (contracts)
    'IDesignManagement',
    'IDesignProtocol',

    # Factory functions (RECOMMENDED - avoids circular imports)
    'get_design_management',
    'get_design_protocol',

    # DTOs (data transfer objects)
    'QuestionDTO',
    'CriterionDTO',
    'DesignScheduleDTO',
]
