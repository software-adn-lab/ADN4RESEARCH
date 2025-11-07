"""
Adapters layer for Acquisition module.

Contains inbound and outbound adapters following Clean Architecture principles.

Structure:
- inbound/: Entry points (API, CLI, Jobs, UI) - currently empty, used by external layers
- outbound/: Exit points (Connectors, Repositories, Storage, Messaging)

Dependency Rules:
- Adapters can depend on Application and Domain layers
- Domain and Application layers NEVER depend on Adapters
"""
