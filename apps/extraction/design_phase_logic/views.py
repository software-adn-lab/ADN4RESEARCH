"""
Views - Extraction Phase Logic
Router para navegación de fases de extracción
"""
from django.shortcuts import get_object_or_404, redirect
from apps.extraction.planning.models import ExtractionPhase
from apps.shared.decorators import project_member_required


@project_member_required
def extraction_phases_router(request, project_id, project_dto):
    """
    Router que redirige a la fase de extracción del proyecto.
    Si hay una fase abierta, la muestra; de lo contrario, muestra la primera fase.
    """
    # Obtener la fase abierta o la primera disponible
    phase = ExtractionPhase.objects.filter(
        project_id=project_id
    ).open_phases().first()
    
    if not phase:
        # Si no hay fase abierta, obtener la primera
        phase = ExtractionPhase.objects.filter(
            project_id=project_id
        ).first()
    
    if not phase:
        # Si no hay fases, redirigir al proyecto
        return redirect('project:detail', pk=project_id)
    
    # Redirigir a la fase de extracción
    return redirect('extraction:planning:phase_detail', project_id=project_id, pk=phase.pk)
