from .application.commands.activate_extraction_phase import ActivateExtractionPhaseHandler
from .application.commands.configure_extraction_phase import ConfigureExtractionPhaseHandler
from .application.queries.get_extraction_quotes_with_locations import GetExtractionQuotesWithLocationsHandler
from .infrastructure.adapters.acquisition_service_adapter import AcquisitionServiceAdapter
from .infrastructure.adapters.design_service_adapter import DesignServiceAdapter
from .infrastructure.adapters.project_service_adapter import ProjectServiceAdapter
from .infrastructure.repositories.django_extraction_phase_repository import DjangoExtractionPhaseRepository
from .infrastructure.repositories.django_extraction_repository import DjangoExtractionRepository
from .infrastructure.repositories.django_tag_repository import DjangoTagRepository
from .domain.services.extraction_validator import ExtractionValidator
from .application.commands.create_extraction import CreateExtractionHandler
from .application.commands.complete_extraction import CompleteExtractionHandler
from .infrastructure.repositories.django_quote_repository import DjangoQuoteRepository
from .domain.services.tag_merger import TagMergeService
from .application.commands.create_quote import CreateQuoteHandler
from .application.commands.create_tag import CreateTagHandler
from .application.commands.moderate_tag import ModerateTagHandler
from .application.commands.merge_tags import MergeTagsHandler
from .application.queries.get_extraction import GetExtractionHandler
from .application.queries.list_extractions import ListExtractionsHandler


class Container:
    # Repositories & Adapters
    extraction_repository = DjangoExtractionRepository()
    quote_repository = DjangoQuoteRepository()
    acquisition_adapter = AcquisitionServiceAdapter()
    design_adapter = DesignServiceAdapter()
    project_adapter = ProjectServiceAdapter()
    tag_repository = DjangoTagRepository(acquisition_adapter)
    phase_repository = DjangoExtractionPhaseRepository()

    # Domain Services
    extraction_validator = ExtractionValidator(tag_repository)
    tag_merger = TagMergeService(quote_repository, tag_repository)

    # Command Handlers
    @property
    def configure_extraction_phase_handler(self):  # ✅
        return ConfigureExtractionPhaseHandler(
            self.phase_repository,
            self.project_adapter
        )

    @property
    def activate_extraction_phase_handler(self):  # ✅
        return ActivateExtractionPhaseHandler(
            self.phase_repository,
            self.project_adapter
        )

    @property
    def create_extraction_handler(self):
        return CreateExtractionHandler(
            self.extraction_repository,
            self.acquisition_adapter,
            self.phase_repository
        )

    @property
    def complete_extraction_handler(self):
        return CompleteExtractionHandler(
            self.extraction_repository,
            self.extraction_validator
        )

    @property
    def create_quote_handler(self):
        return CreateQuoteHandler(
            extraction_repo=self.extraction_repository,
            quote_repo=self.quote_repository,
            tag_repo=self.tag_repository,
            acquisition_adapter=self.acquisition_adapter
        )

    @property
    def create_tag_handler(self):
        return CreateTagHandler(
            tag_repo=self.tag_repository,
            design_repo=self.design_adapter,
            project_repo=self.project_adapter
        )

    @property
    def moderate_tag_handler(self):
        return ModerateTagHandler(self.tag_repository, self.project_adapter)

    @property
    def merge_tags_handler(self):
        return MergeTagsHandler(
            self.tag_repository,
            self.tag_merger,
            self.project_adapter
        )

    @property
    def get_extraction_handler(self):
        return GetExtractionHandler(self.extraction_repository)

    @property
    def list_extractions_handler(self):
        return ListExtractionsHandler(self.extraction_repository)

    @property
    def get_extraction_quotes_handler(self):
        return GetExtractionQuotesWithLocationsHandler(
            self.extraction_repository
        )

container = Container()