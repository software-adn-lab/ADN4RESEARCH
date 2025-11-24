from typing import List, Optional

from django.db import transaction

from ...domain.repositories.i_quote_repository import IQuoteRepository
from ...domain.entities.quote import Quote
from ..models import QuoteModel
from ..mappers.domain_mappers import QuoteMapper

class DjangoQuoteRepository(IQuoteRepository):
    @transaction.atomic
    def save(self, quote: Quote) -> Quote:
        # 1. Mapear a Dict para el modelo
        data = {
            'extraction_id': quote.extraction_id,
            'text_portion': quote.text,
            'location': quote.location,
            'researcher_id': quote.researcher_id,
        }

        # 2. Guardar el objeto principal (Quote)
        if quote.id:
            QuoteModel.objects.filter(pk=quote.id).update(**data)
            model = QuoteModel.objects.get(pk=quote.id)
        else:
            model = QuoteModel.objects.create(**data)
            quote.id = model.id  # Asignar ID generado

        # 3. Gestionar relación ManyToMany (Tags)
        if quote.tags:
            # Extraemos solo los IDs de los tags de dominio
            tag_ids = [t.id for t in quote.tags]
            model.tags.set(tag_ids)  # Django maneja la tabla intermedia aquí

        return QuoteMapper.to_domain(model)

    def get_by_id(self, quote_id: int) -> Optional[Quote]:
        try:
            model = QuoteModel.objects.get(pk=quote_id)
            return QuoteMapper.to_domain(model)
        except QuoteModel.DoesNotExist:
            return None

    def get_by_tag(self, tag_id: int) -> List[Quote]:
        qs = QuoteModel.objects.filter(tags__id=tag_id)
        return [QuoteMapper.to_domain(m) for m in qs]

    def delete(self, quote_id: int) -> None:
        QuoteModel.objects.filter(pk=quote_id).delete()