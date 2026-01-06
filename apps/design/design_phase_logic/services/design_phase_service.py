from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.design.design_phase_logic.models.design_phase import DesignPhase, DesignStageLog, DesignStagePlan
from apps.design.design_phase_logic.models.design_phase import DesignPhase, DesignStageLog, DesignStagePlan
from apps.design.eligibility_criteria.services.eligibility_criterion_services import EligibilityCriterionService
from apps.design.research_question.services.question_services import ResearchQuestionService
from apps.design.search_strategy.services.search_strategy_service import SearchStrategyService
from apps.acquisition.facade import get_acquisition_facade


class DesignPhaseService:
    def _consolidate_stage(
        self,
        project_id: int,
        user,
        current_stage: DesignPhase.DesignStage,
        next_stage: DesignPhase.DesignStage,
        finalize_callback: callable = None
    ) -> tuple:

        phase = DesignPhase.objects.get(pk=project_id)
        # 1. Validar etapa actual
        if phase.current_stage != current_stage:
            raise ValidationError(
                f"Cannot consolidate {current_stage.label}. "
                f"Current stage is {phase.current_stage}"
            )
        # 2. Ejecutar lógica de dominio específica (si existe)
        callback_result = None
        if finalize_callback:
            callback_result = finalize_callback(project_id, user)
        # 3. Transición de estado (incluye actualización de cronograma automáticamente)
        self._transition_stage(phase, next_stage)
        return phase, callback_result

    @transaction.atomic
    def consolidate_creation_stage(self, project_id: int, user):
        """
        Cierra la etapa de Creación e inicia Discusión.
        No requiere lógica de dominio específica.
        """
        phase, _ = self._consolidate_stage(
            project_id=project_id,
            user=user,
            current_stage=DesignPhase.DesignStage.RQ_CREATION,
            next_stage=DesignPhase.DesignStage.RQ_DISCUSSION,
            finalize_callback=None
        )
        return phase

    @transaction.atomic
    def consolidate_creation_stage(self, project_id: int, user):
        """
        Cierra la etapa de Creación e inicia Discusión.
        Ajusta dinámicamente el cronograma: la fecha de inicio planificada de RQ_DISCUSSION
        se convierte en la fecha actual.
        """
        phase = DesignPhase.objects.get(pk=project_id)

        if phase.current_stage != DesignPhase.DesignStage.RQ_CREATION:
            raise ValidationError(f"Cannot consolidate Creation. Current stage is {phase.current_stage}")

        # 1. Actualizar Cronograma (Dynamic Schedule)
        # Buscamos el plan de la siguiente etapa (RQ_DISCUSSION)
        try:
            next_stage_plan = DesignStagePlan.objects.get(
                phase=phase,
                stage=DesignPhase.DesignStage.RQ_DISCUSSION
            )
            # Reseteamos el inicio planificado a HOY
            next_stage_plan.planned_start_date = timezone.now().date()
            next_stage_plan.save()
        except DesignStagePlan.DoesNotExist:
            # Si no hay plan, no pasa nada (o podríamos crearlo, pero asumimos que existe)
            pass

        # 2. Transición de estado con auditoría
        self._transition_stage(phase, DesignPhase.DesignStage.RQ_DISCUSSION)

        return phase

    @transaction.atomic
    def consolidate_research_question_stage(self, project_id: int, user):
        """
        Cierra la etapa de Preguntas e inicia Criterios.
        """
        def finalize_questions(proj_id, usr):
            service = ResearchQuestionService()
            return service.finalize_questions_stage(proj_id, usr)
        phase, _ = self._consolidate_stage(
            project_id=project_id,
            user=user,
            current_stage=DesignPhase.DesignStage.RQ_DISCUSSION,
            next_stage=DesignPhase.DesignStage.CRITERIA_DEFINITION,
            finalize_callback=finalize_questions
        )
        return phase

    @transaction.atomic
    def consolidate_eligibility_criteria_stage(self, project_id: int, user):
        """
        Cierra la etapa de Criterios e inicia Estrategia de Búsqueda.
        """
        def finalize_criteria(proj_id, usr):
            service = EligibilityCriterionService()
            return service.finalize_criteria_stage(proj_id, usr)
        phase, _ = self._consolidate_stage(
            project_id=project_id,
            user=user,
            current_stage=DesignPhase.DesignStage.CRITERIA_DEFINITION,
            next_stage=DesignPhase.DesignStage.SEARCH_STRATEGY,
            finalize_callback=finalize_criteria
        )
        return phase

    @transaction.atomic
    def consolidate_search_strategy_stage(self, project_id: int, user):
        """
        Cierra la etapa de Estrategia y Finaliza la Fase de Diseño.
        """
        phase = DesignPhase.objects.get(pk=project_id)
        if phase.current_stage != DesignPhase.DesignStage.SEARCH_STRATEGY:
            raise ValidationError(f"Cannot consolidate Strategy. Current stage is {phase.current_stage}")
        # 1. Ejecutar lógica de dominio específica del sub-módulo
        search_service = SearchStrategyService()
        acquisition_facade = get_acquisition_facade()
        approved_strategy_ids = search_service.finalize_strategies_stage(project_id, user)
        # 2. Transición de estado con auditoría
        self._transition_stage(phase, DesignPhase.DesignStage.FINISHED)

        # 3. Disparar procesos externos (Acquisition)
        # Nota: Esto podría ir en un evento/señal para desacoplar más, pero por ahora es válido aquí.
        for strategy_id in approved_strategy_ids:
            try:
                preview_result = search_service.get_search_results_dto(strategy_id)
                acquisition_facade.finalize_search(
                    design_strategy_id=strategy_id,
                    preview_result=preview_result,
                    user=user
                )
            except Exception as e:
                # Si falla la integración, hacemos rollback de toda la transacción
                raise ValidationError(f"Error persisting strategy {strategy_id}: {str(e)}")
        return phase

    @transaction.atomic
    def check_deadlines_and_consolidate(self, system_user):
        """
        Checks for expired stages and consolidates them automatically.
        Currently only enforces RQ_CREATION deadline.
        """
        active_phases = DesignPhase.objects.filter(
            current_stage=DesignPhase.DesignStage.RQ_CREATION,
            is_active=True
        )
        today = timezone.now().date()
        count = 0

        for phase in active_phases:
            try:
                plan = DesignStagePlan.objects.get(
                    phase=phase,
                    stage=DesignPhase.DesignStage.RQ_CREATION
                )
                if today >= plan.planned_end_date:
                    self.consolidate_creation_stage(phase.project_id, system_user)
                    count += 1
            except DesignStagePlan.DoesNotExist:
                continue
            except Exception:
                # Log error but continue processing others
                continue
        return count

    def _transition_stage(self, phase: DesignPhase, next_stage: str):
        """
        Método helper privado para manejar la lógica repetitiva de cerrar logs y abrir nuevos.
        Garantiza la trazabilidad(RNF - 03).
        También reprograma el inicio de la siguiente etapa a HOY(Dynamic Schedule).
        """
        # 1. Cerrar el log de la etapa actual
        current_log = DesignStageLog.objects.filter(
            phase=phase,
            stage=phase.current_stage,
            end_date__isnull=True
        ).last()

        if current_log:
            current_log.end_date = timezone.now()
            current_log.save()

        # 2. Actualizar la fase
        phase.current_stage = next_stage
        phase.save()

        # 3. Dynamic Schedule: Reset planned start date of next stage to TODAY
        if next_stage != DesignPhase.DesignStage.FINISHED:
            try:
                next_plan = DesignStagePlan.objects.get(phase=phase, stage=next_stage)
                next_plan.planned_start_date = timezone.now().date()
                next_plan.save()
            except DesignStagePlan.DoesNotExist:
                pass

            # 4. Crear el log para la nueva etapa
            DesignStageLog.objects.create(
                phase=phase,
                stage=next_stage,
                start_date=timezone.now()
            )

    @transaction.atomic
    def initialize_design_schedule(self, project_id: int, schedule_data: list[dict]) -> int:
        """
        Implementación concreta del contrato de inicialización.
        """
        phase = DesignPhase.objects.get(pk=project_id)
        phase.planned_stages.all().delete()
        new_plans = []
        for item in schedule_data:
            if item['stage'] not in DesignPhase.DesignStage.values:
                raise ValueError(f"Código de etapa inválido recibido: {item['stage']}")
            new_plans.append(DesignStagePlan(
                phase=phase,
                stage=item['stage'],
                planned_start_date=item['start'],
                planned_end_date=item['end']
            ))
        # 4. Persistencia eficiente
        DesignStagePlan.objects.bulk_create(new_plans)

        return len(new_plans)
