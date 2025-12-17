import traceback

from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
import os
import json
from django.views import View
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from .models import PaperExtraction, Quote
from ..taxonomy.models import Tag

from django.views.generic import DetailView

# Asegúrate de importar settings si tus rutas son relativas a MEDIA_ROOT, etc.
# from django.conf import settings 

from .models import PaperExtraction

class PDFServeView(LoginRequiredMixin, View):
    def get(self, request, paper_id):
        paper = get_object_or_404(PaperExtraction, pk=paper_id)
        
        # Validar seguridad: El usuario debe poder ver este paper
        # (Implementa tu lógica aquí si es necesario, ej: si es owner o researcher asignado)

        file_path = paper.path # Asumiendo que 'path' es la ruta absoluta o relativa válida

        if not os.path.exists(file_path):
            raise Http404("El archivo PDF no se encuentra.")

        with open(file_path, 'rb') as pdf_file:
            response = HttpResponse(pdf_file.read(), content_type='application/pdf')
            # 'inline' hace que se vea en el navegador, 'attachment' lo descarga
            response['Content-Disposition'] = f'inline; filename="{paper.study.title}.pdf"'
            return response

class PaperWorkspaceView(LoginRequiredMixin, DetailView):
    model = PaperExtraction
    template_name = 'paper_extraction_detail.html'
    context_object_name = 'paper'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['available_tags'] = self.object.extraction_phase.tags.filter(
            status='APPROVED'
        )

        context['mandatory_tags'] = self.object.extraction_phase.tags.filter(
            status='APPROVED',
            is_mandatory=True
        )

        context['quotes_list'] = list(self.object.quotes.values(
            'id', 'text_fragment', 'location'
        ))

        print(f"Ruta del PDF: {self.object.path}")

        return context


class QuoteCreateView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            print("\n" + "=" * 50)
            print("🚀 DEBUG START: QuoteCreateView.post")

            # 1. Ver qué llega exactamente en el cuerpo de la petición
            body_unicode = request.body.decode('utf-8')
            print(f"📥 RAW BODY RECIBIDO:\n{body_unicode}")

            data = json.loads(request.body)

            text_fragment = data.get('text_fragment')
            paper_id = data.get('paper_extraction_id')
            tag_ids = data.get('tags', [])

            # 2. Ver específicamente qué valor toma 'location'
            location = data.get('location', {})
            print(f"📍 LOCATION EXTRAÍDO: {location} | Tipo: {type(location)}")

            if not text_fragment or not paper_id:
                print("❌ ERROR: Faltan datos obligatorios")
                return JsonResponse({'error': 'Faltan datos obligatorios'}, status=400)

            with transaction.atomic():
                print(f"🔍 Buscando Paper ID: {paper_id}")
                paper = PaperExtraction.objects.get(id=paper_id)

                print("💾 Intentando crear Quote en DB...")
                quote = Quote.objects.create(
                    paper_extraction=paper,
                    text_fragment=text_fragment,
                    created_by=request.user,
                    location=location  # Aquí pasamos el dict
                )

                # 3. Confirmar qué se guardó realmente en el objeto
                print(f"✅ QUOTE CREADA: ID={quote.id}")
                print(f"💾 LOCATION GUARDADO EN DB: {quote.location}")

                valid_tags = Tag.objects.filter(id__in=tag_ids)
                print(f"🏷️ Tags encontrados para asociar: {valid_tags.count()}")
                quote.tags.set(valid_tags)

            print("🚀 DEBUG END: Success")
            print("=" * 50 + "\n")
            return JsonResponse({'id': quote.id, 'status': 'success'}, status=201)

        except PaperExtraction.DoesNotExist:
            print("❌ ERROR: PaperExtraction no encontrado")
            return JsonResponse({'error': 'Paper no encontrado'}, status=404)
        except Exception as e:
            print(f"🔥 EXCEPCIÓN NO CONTROLADA: {str(e)}")
            traceback.print_exc()  # Esto imprimirá la línea exacta del error
            return JsonResponse({'error': str(e)}, status=500)
