from django.test import TestCase
from django.contrib.auth.models import User
from apps.design.access_control import DesignAccessPolicy
from apps.design.design_phase_logic.models.design_phase import DesignPhase
from apps.design.research_question.models.research_question import ResearchQuestion
from apps.project.structure.models.project_models import Project


class DesignAccessPolicyTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='password')
        self.researcher = User.objects.create_user(username='researcher', password='password')
        self.other_user = User.objects.create_user(username='other', password='password')

        self.project = Project.objects.create(title="Test Project", owner=self.owner)
        self.phase = DesignPhase.objects.create(project=self.project)

        self.question = ResearchQuestion.objects.create(
            design_phase=self.phase,
            researcher=self.researcher,
            question="Test Question",
            motivation="Motivation"
        )

    def test_is_owner(self):
        self.assertTrue(DesignAccessPolicy.is_owner(self.owner, self.project))
        self.assertFalse(DesignAccessPolicy.is_owner(self.researcher, self.project))

    def test_can_edit_question_in_edition_stage(self):
        # Stage: RQ_CREATION (Edition)
        self.phase.current_stage = DesignPhase.DesignStage.RQ_CREATION
        self.phase.save()

        # Owner can edit
        self.assertTrue(DesignAccessPolicy.can_edit_question(self.owner, self.question))
        # Researcher (author) can edit
        self.assertTrue(DesignAccessPolicy.can_edit_question(self.researcher, self.question))
        # Other user cannot edit
        self.assertFalse(DesignAccessPolicy.can_edit_question(self.other_user, self.question))

    def test_can_edit_question_in_locked_stage(self):
        # Stage: CRITERIA_DEFINITION (Locked for RQ)
        self.phase.current_stage = DesignPhase.DesignStage.CRITERIA_DEFINITION
        self.phase.save()

        # Owner can still edit (admin override)
        self.assertTrue(DesignAccessPolicy.can_edit_question(self.owner, self.question))
        # Researcher cannot edit anymore
        self.assertFalse(DesignAccessPolicy.can_edit_question(self.researcher, self.question))

    def test_can_review_question_in_discussion_stage(self):
        # Stage: RQ_DISCUSSION
        self.phase.current_stage = DesignPhase.DesignStage.RQ_DISCUSSION
        self.phase.save()

        # Owner can review any question
        self.assertTrue(DesignAccessPolicy.can_review_question(self.owner, self.phase, self.question))

        # Researcher CANNOT review their OWN question
        self.assertFalse(DesignAccessPolicy.can_review_question(self.researcher, self.phase, self.question))

        # Researcher CAN review OTHER's question
        other_question = ResearchQuestion.objects.create(
            design_phase=self.phase,
            researcher=self.other_user,
            question="Other Question"
        )
        self.assertTrue(DesignAccessPolicy.can_review_question(self.researcher, self.phase, other_question))

    def test_can_consolidate_stage(self):
        self.assertTrue(DesignAccessPolicy.can_consolidate_stage(self.owner, self.phase))
        self.assertFalse(DesignAccessPolicy.can_consolidate_stage(self.researcher, self.phase))
