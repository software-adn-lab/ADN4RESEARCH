from typing import List
from ..entities.tag import Tag
from ..entities.quote import Quote
from ..repositories.i_quote_repository import IQuoteRepository
from ..repositories.i_tag_repository import ITagRepository


class TagMergeService:
    def __init__(self, quote_repo: IQuoteRepository, tag_repo: ITagRepository):
        self.quote_repo = quote_repo
        self.tag_repo = tag_repo

    def merge_tags(self, target_tag: Tag, source_tag: Tag):
        """
        Fusiona source_tag DENTRO de target_tag.
        1. Busca todas las quotes que usen source_tag.
        2. Reemplaza source_tag por target_tag en esas quotes.
        3. Elimina source_tag.
        """
        quotes = self.quote_repo.get_by_tag(source_tag.id)

        for quote in quotes:
            quote.replace_tag(old_tag=source_tag, new_tag=target_tag)
            self.quote_repo.save(quote)  # Persistimos el cambio en la quote

        self.tag_repo.delete(source_tag)  # Eliminamos el tag duplicado