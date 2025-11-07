"""
Inbound adapters - Entry points into the application.

This layer will contain:
- API views/endpoints (Django REST Framework)
- CLI commands (Django management commands)
- Celery task definitions
- WebSocket handlers
- GraphQL resolvers

Currently empty - will be populated when implementing user-facing features.

Dependency: Inbound adapters call Application Services (use cases).
"""
