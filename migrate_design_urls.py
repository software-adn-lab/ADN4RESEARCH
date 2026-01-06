#!/usr/bin/env python
"""
URL Migration Script for Design Module Templates
Automatically updates all {% url %} tags from old flat structure to new hierarchical namespaces.
"""
import os
import re
from pathlib import Path

# URL name migrations mapping
URL_MIGRATIONS = {
    # Research Questions
    "'design:rq_workspace'": "'design:questions:workspace'",
    "'design:create_research_question'": "'design:questions:create'",
    "'design:autosave_research_question'": "'design:questions:autosave'",
    "'design:edit_research_question'": "'design:questions:edit'",
    "'design:delete_research_question'": "'design:questions:delete'",
    "'design:send_research_question_for_review'": "'design:questions:submit'",
    "'design:get_search_strategy_for_question'": "'design:questions:generate_strategy'",
    "'design:consolidate_creation_stage'": "'design:questions:consolidate_creation'",

    # Discussion
    "'design:question_discussion_panel'": "'design:discussion:panel'",
    "'design:review_research_question_action'": "'design:discussion:review'",
    "'design:consolidate_discussion_stage'": "'design:discussion:consolidate'",

    # Eligibility Criteria
    "'design:eligibility_criteria_panel'": "'design:criteria:panel'",
    "'design:create_criterion'": "'design:criteria:create'",
    "'design:update_criterion'": "'design:criteria:update'",
    "'design:approve_criterion'": "'design:criteria:approve'",
    "'design:reject_criterion'": "'design:criteria:reject'",
    "'design:delete_criterion'": "'design:criteria:delete'",
    "'design:consolidate_eligibility_stage'": "'design:criteria:consolidate'",

    # Keywords
    "'design:create_project_keyword'": "'design:keywords:create'",
    "'design:update_project_keyword'": "'design:keywords:update'",
    "'design:delete_project_keyword'": "'design:keywords:delete'",

    # Search Strategies
    "'design:open_search_strategy_panel'": "'design:strategies:panel'",
    "'design:search_strategy_builder_view'": "'design:strategies:builder'",
    "'design:preview_search_string'": "'design:strategies:preview'",
    "'design:save_visual_strategy'": "'design:strategies:save'",
    "'design:search_results_view'": "'design:strategies:results'",
    "'design:approve_strategy'": "'design:strategies:approve'",
    "'design:reject_strategy'": "'design:strategies:reject'",
    "'design:get_strategy_versions'": "'design:strategies:versions'",
    "'design:delete_strategy_version'": "'design:strategies:delete_version'",
    "'design:consolidate_search_strategy_stage'": "'design:strategies:consolidate'",
}


def migrate_template(file_path):
    """Migrate a single template file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    replacements_made = 0

    for old_url, new_url in URL_MIGRATIONS.items():
        if old_url in content:
            content = content.replace(old_url, new_url)
            count = original_content.count(old_url)
            replacements_made += count
            print(f"  ✓ Replaced {old_url} → {new_url} ({count}x)")

    if replacements_made > 0:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return replacements_made
    return 0


def main():
    templates_dir = Path(r'c:\Project\ADN4RESEARCH\ui\design\templates')

    if not templates_dir.exists():
        print(f"❌ Templates directory not found: {templates_dir}")
        return

    print("🔄 Starting URL migration for Design templates...\n")

    total_files = 0
    total_replacements = 0

    for template_file in templates_dir.rglob('*.html'):
        replacements = migrate_template(template_file)
        if replacements > 0:
            total_files += 1
            total_replacements += replacements
            print(f"📝 Updated: {template_file.relative_to(templates_dir)} ({replacements} replacements)\n")

    print(f"\n✅ Migration complete!")
    print(f"   Files updated: {total_files}")
    print(f"   Total replacements: {total_replacements}")


if __name__ == '__main__':
    main()
