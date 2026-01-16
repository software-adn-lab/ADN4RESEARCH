class SelectionStatusChoices:
    """Selection phase status choices"""
    ON_GOING = 'ON_GOING'
    FINALIZED = 'FINALIZED'

    CHOICES = [
        (ON_GOING, 'On Going'),
        (FINALIZED, 'Finalized'),
    ]


class SubPhaseStatusChoices:
    """Sub-phase status choices for screening and fulltext"""
    NOT_STARTED = 'NOT_STARTED'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'

    CHOICES = [
        (NOT_STARTED, 'Not Started'),
        (IN_PROGRESS, 'In Progress'),
        (COMPLETED, 'Completed'),
    ]


class SelectionStageChoices:
    """Selection stage choices"""
    # Screening sub-phases
    SCREENING_OVERVIEW = 'SCREENING_OVERVIEW'
    SCREENING = 'SCREENING'
    SCREENING_DISCUSSION = 'SCREENING_DISCUSSION'
    # Fulltext sub-phases
    FULLTEXT_OVERVIEW = 'FULLTEXT_OVERVIEW'
    FULLTEXT = 'FULLTEXT'
    FULLTEXT_DISCUSSION = 'FULLTEXT_DISCUSSION'

    CHOICES = [
        (SCREENING_OVERVIEW, 'Screening Overview'),
        (SCREENING, 'Screening'),
        (SCREENING_DISCUSSION, 'Screening Discussion'),
        (FULLTEXT_OVERVIEW, 'Full-text Overview'),
        (FULLTEXT, 'Full-text Review'),
        (FULLTEXT_DISCUSSION, 'Full-text Discussion'),
    ]

    # For backward compatibility with PaperReview stage field
    STAGE_SCREENING = 'SCREENING'
    STAGE_FULLTEXT = 'FULL_TEXT'


class AssignmentStageChoices:
    """Stage for paper assignments"""
    SCREENING = 'SCREENING'
    FULLTEXT = 'FULLTEXT'

    CHOICES = [
        (SCREENING, 'Screening'),
        (FULLTEXT, 'Full-text'),
    ]


class ResolutionMethodChoices:
    """Method used to resolve a conflict"""
    OWNER_VOTE = 'OWNER_VOTE'
    THIRD_REVIEWER = 'THIRD_REVIEWER'

    CHOICES = [
        (OWNER_VOTE, 'Owner Vote'),
        (THIRD_REVIEWER, 'Third Reviewer'),
    ]


class SelectionDecisionChoices:
    """Paper selection decision choices"""
    INCLUDED = 'INCLUDED'
    EXCLUDED = 'EXCLUDED'
    PENDING = 'PENDING'

    CHOICES = [
        (INCLUDED, 'Included'),
        (EXCLUDED, 'Excluded'),
        (PENDING, 'Pending'),
    ]
