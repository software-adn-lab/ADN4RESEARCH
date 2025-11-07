"""
Outbound adapters - Infrastructure implementations.

This layer contains implementations of domain interfaces (ports):
- connectors/: External API clients (Scopus, IEEE Xplore, Web of Science, etc.)
- repositories/: Database persistence implementations
- storage/: File/document storage implementations (local, S3, etc.)
- messaging/: Event bus and message queue implementations

Dependency: Outbound adapters implement interfaces defined in Domain layer.
"""
