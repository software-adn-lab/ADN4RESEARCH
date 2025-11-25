from typing import Optional, List
from django.db.models import Q
from django.utils import timezone
from ...domain.repositories.i_extraction_phase_repository import IExtractionPhaseRepository
from ...domain.entities.extraction_phase import ExtractionPhase
from ..models import ExtractionPhaseModel
from ..mappers.domain_mappers import ExtractionPhaseMapper
from ...domain.value_objects.phase_status import PhaseStatus


class DjangoExtractionPhaseRepository(IExtractionPhaseRepository):

    def get_by_project_id(self, project_id: int) -> Optional[ExtractionPhase]:
        try:
            model = ExtractionPhaseModel.objects.get(project_id=project_id)
            return ExtractionPhaseMapper.to_domain(model)
        except ExtractionPhaseModel.DoesNotExist:
            return None

    def save(self, phase: ExtractionPhase) -> ExtractionPhase:
        data = ExtractionPhaseMapper.to_db(phase)

        if phase.id:
            ExtractionPhaseModel.objects.filter(pk=phase.id).update(**data)
            model = ExtractionPhaseModel.objects.get(pk=phase.id)
        else:
            model = ExtractionPhaseModel.objects.create(**data)
            phase.id = model.id

        return ExtractionPhaseMapper.to_domain(model)

    def get_active_phases_to_close(self) -> List[ExtractionPhase]:
        """Obtiene fases activas que ya pasaron su end_date"""

        now = timezone.now()
        qs = ExtractionPhaseModel.objects.filter(
            status=PhaseStatus.ACTIVE.value,
            auto_close=True,
            end_date__lte=now
        )

        return [ExtractionPhaseMapper.to_domain(m) for m in qs]