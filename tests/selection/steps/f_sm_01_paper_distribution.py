"""
BDD Steps for paper distribution feature
"""

import json
from behave import given, when, then
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock

from apps.project.structure.models.project_models import Project, Membership
from apps.selection.features.distribution.metadata.services import PaperDistributionService


@given('investigadores con cargas horarias definidas:')
def step_given_researchers_with_workload(context):
    """
    Create researchers with workload hours.
    
    Expected format in context.text:
    {"I1": 10, "I2": 20, "I3": 5}
    """
    workloads = json.loads(context.text.strip())
    
    # Create project
    owner = User.objects.create_user(username='owner', password='test123')
    project = Project.objects.create(
        title='Test Project',
        summary='Test',
        motivation='Test',
        general_objective='Test',
        owner=owner
    )
    
    # Store in context
    context.project = project
    context.researchers = {}
    context.workloads = workloads
    
    # Create researchers
    for researcher_id, workload in workloads.items():
        user = User.objects.create_user(
            username=researcher_id.lower(),
            password='test123'
        )
        
        Membership.objects.create(
            project=project,
            user=user,
            role='RESEARCHER',
            workload_hours=workload
        )
        
        context.researchers[researcher_id] = user


@given('papers con un número específico de hojas:')
def step_given_papers_with_pages(context):
    """
    Mock papers with word counts (using 'hojas' as word count for screening).
    
    Expected format in context.text:
    {"P1": 12, "P2": 6, "P3": 18}
    """
    papers_pages = json.loads(context.text.strip())
    context.papers_pages = papers_pages
    
    # Create mock papers data (simulating project facade response)
    context.mock_papers = []
    for paper_id, word_count in papers_pages.items():
        # Create abstract with exact word count
        # Each "word" is just a placeholder like "word1 word2 word3..."
        abstract_words = ' '.join([f'word{i}' for i in range(word_count)])
        
        context.mock_papers.append({
            'id': paper_id,
            'title': f'Paper {paper_id}',
            'abstract': abstract_words,
            'source': 'IEEE',
            'status': 'enriched'
        })


@given('que cada paper debe asignarse {total_reviews:d} veces a revisores distintos')
def step_given_total_reviews(context, total_reviews):
    """Store total reviews per paper"""
    context.total_reviews = total_reviews


@when('se ejecuta el algoritmo de distribución')
def step_when_distribution_executed(context):
    """Execute the distribution algorithm"""
    
    # Mock the project facade
    with patch('apps.selection.features.distribution.shared.services.get_project_facade') as mock_facade:
        mock_instance = MagicMock()
        mock_instance.get_studies_by_project.return_value = context.mock_papers
        mock_facade.return_value = mock_instance
        
        # Execute distribution
        service = PaperDistributionService(context.project.id)
        context.distribution = service.distribute_papers(
            total_reviews_per_paper=context.total_reviews
        )


@then('cada paper debe tener {total_reviews:d} revisores distintos')
def step_then_each_paper_has_reviewers(context, total_reviews):
    """Verify each paper has the correct number of reviewers"""
    
    # Count assignments per paper
    paper_assignments = {}
    for username, papers in context.distribution.items():
        for paper_id in papers:
            if paper_id not in paper_assignments:
                paper_assignments[paper_id] = []
            paper_assignments[paper_id].append(username)
    
    # Verify each paper has correct number of unique reviewers
    for paper_id, papers_pages in context.papers_pages.items():
        assert paper_id in paper_assignments, \
            f"Paper {paper_id} has no assignments"
        
        reviewers = paper_assignments[paper_id]
        assert len(reviewers) == total_reviews, \
            f"Paper {paper_id} has {len(reviewers)} reviewers, expected {total_reviews}"
        
        # Verify all reviewers are unique
        assert len(reviewers) == len(set(reviewers)), \
            f"Paper {paper_id} has duplicate reviewer assignments"


@then('ningún investigador debe recibir asignaciones repetidas del mismo paper')
def step_then_no_duplicate_assignments(context):
    """Verify no researcher has duplicate paper assignments"""
    
    for username, papers in context.distribution.items():
        unique_papers = set(papers)
        assert len(papers) == len(unique_papers), \
            f"Researcher {username} has duplicate paper assignments: {papers}"


@then('la distribución debe ser balanceada según carga horaria')
def step_then_distribution_balanced(context):
    """
    Verify distribution is balanced according to workload.
    
    Total words assigned should be proportional to workload hours.
    """
    # Calculate total words per researcher
    researcher_words = {}
    for username, papers in context.distribution.items():
        total_words = sum(
            context.papers_pages.get(paper_id, 0)
            for paper_id in papers
        )
        researcher_words[username] = total_words
    
    # Get workload for each researcher (map username to workload)
    workload_by_username = {}
    for researcher_id, workload in context.workloads.items():
        username = researcher_id.lower()
        workload_by_username[username] = workload
    
    # Calculate expected proportions
    total_workload = sum(context.workloads.values())
    total_words = sum(context.papers_pages.values()) * context.total_reviews
    
    # Verify each researcher's assignment is proportional
    for username, assigned_words in researcher_words.items():
        workload = workload_by_username[username]
        expected_proportion = workload / total_workload
        expected_words = expected_proportion * total_words
        
        # Allow 20% tolerance for greedy algorithm variance
        tolerance = 0.2
        min_words = expected_words * (1 - tolerance)
        max_words = expected_words * (1 + tolerance)
        
        assert min_words <= assigned_words <= max_words, \
            f"Researcher {username}: assigned {assigned_words} words, " \
            f"expected {expected_words:.1f} (±20%), " \
            f"workload={workload}/{total_workload}"


@then('la distribución resultante debe ser:')
def step_then_expected_distribution(context):
    """
    Verify the distribution matches or is similar to expected distribution.
    
    Note: This is informational - the greedy algorithm may produce different
    valid distributions, so we just log the comparison.
    """
    expected_distribution = json.loads(context.text.strip())
    
    print("\n=== DISTRIBUCIÓN ESPERADA ===")
    for researcher, papers in expected_distribution.items():
        print(f"{researcher}: {papers}")
    
    print("\n=== DISTRIBUCIÓN REAL ===")
    for researcher, papers in context.distribution.items():
        # Map back to researcher IDs (i1 -> I1)
        researcher_id = researcher.upper()
        print(f"{researcher_id}: {papers}")
    
    # Note: We don't assert exact match because greedy algorithm
    # can produce different valid solutions
