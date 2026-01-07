from django.test import TestCase
from django.contrib.auth.models import User
from apps.design.research_question.selectors import ResearchQuestionSelector
from apps.design.design_phase_logic.selectors import DesignPhaseSelector
from apps.design.design_phase_logic.models.design_phase import DesignPhase
from apps.design.research_question.models.research_question import ResearchQuestion
from apps.project.structure.models.project_models import Project


class SelectorsTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='password')
        self.project = Project.objects.create(title="Test Project", owner=self.owner)
        self.phase = DesignPhase.objects.create(project=self.project)

        self.q1 = ResearchQuestion.objects.create(
            design_phase=self.phase,
            researcher=self.owner,
            question="Q1",
            status=ResearchQuestion.Status.DRAFT
        )
        self.q2 = ResearchQuestion.objects.create(
            design_phase=self.phase,
            researcher=self.owner,
            question="Q2",
            status=ResearchQuestion.Status.APPROVED
        )

    def test_research_question_selector_get_list(self):
        # Test get_list_for_workspace
        dtos = ResearchQuestionSelector.get_list_for_workspace(self.project.id, self.owner)
        self.assertEqual(len(dtos), 2)
        self.assertEqual(dtos[0].id, self.q2.id)  # Ordered by modified_at desc (default) or creation

        # Test filter
        dtos_filtered = ResearchQuestionSelector.get_list_for_workspace(
            self.project.id,
            self.owner,
            status_filter=ResearchQuestion.Status.APPROVED
        )
        self.assertEqual(len(dtos_filtered), 1)
        self.assertEqual(dtos_filtered[0].id, self.q2.id)

    def test_design_phase_selector_timeline(self):
        # Test get_design_timeline_context
        self.phase.current_stage = DesignPhase.DesignStage.RQ_CREATION
        self.phase.save()

        timeline = DesignPhaseSelector.get_design_timeline_context(self.project.id)

        # Check structure
        self.assertTrue(len(timeline) > 0)

        # Check current stage logic
        current_stage_dto = next(t for t in timeline if t.key == DesignPhase.DesignStage.RQ_CREATION)
        self.assertEqual(current_stage_dto.status, 'current')

        # Check upcoming stage logic
        upcoming_stage_dto = next(t for t in timeline if t.key == DesignPhase.DesignStage.CRITERIA_DEFINITION)
        self.assertEqual(upcoming_stage_dto.status, 'upcoming')
