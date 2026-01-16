import os
import uuid
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.core.files.storage import default_storage
from django.core.files import File
from django.db import transaction
from django.apps import apps

class Command(BaseCommand):
    help = 'Toma archivos PDF locales y los asigna a estudios existentes en la BD, subiéndolos al Storage.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--folder',
            type=str,
            required=True,
            help='Ruta absoluta de la carpeta que contiene los PDFs reales'
        )
        parser.add_argument(
            '--strategy_id',
            type=int,
            default=1,
            help='ID de la estrategia para filtrar qué estudios actualizar (Default: 1)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Límite de estudios a actualizar (0 = todos los archivos de la carpeta)'
        )

    def handle(self, *args, **options):
        folder_path = Path(options['folder'])
        strategy_id = options['strategy_id']
        
        # 1. Validaciones iniciales
        if not folder_path.exists() or not folder_path.is_dir():
            raise CommandError(f"❌ La carpeta no existe: {folder_path}")

        # Listar solo archivos PDF
        pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            raise CommandError(f"⚠️ No se encontraron archivos .pdf en {folder_path}")

        self.stdout.write(self.style.SUCCESS(f"📂 Se encontraron {len(pdf_files)} archivos PDF locales."))

        # 2. Obtener Modelos
        StudyModel = apps.get_model('acquisition', 'StudyModel')

        # 3. Buscar estudios candidatos para actualizar
        # Buscamos estudios vinculados a la estrategia dada, ordenados por los más recientes
        # y que preferiblemente no tengan ya un PDF válido (opcional, aquí sobrescribimos todo para test)
        candidate_studies = StudyModel.objects.filter(
            executions__strategy_id=strategy_id
        ).distinct().order_by('-discovered_at')

        if options['limit'] > 0:
            candidate_studies = candidate_studies[:options['limit']]

        count_studies = candidate_studies.count()
        self.stdout.write(f"🔎 Se encontraron {count_studies} estudios candidatos en la Estrategia {strategy_id}.")

        if count_studies == 0:
            self.stdout.write(self.style.WARNING("⚠️ No hay estudios para actualizar. Ejecuta primero 'seed_acquisition'."))
            return

        # 4. Proceso de Asignación (Match Files <-> Studies)
        # Zip cortará la iteración cuando se acaben los archivos O se acaben los estudios
        updated_count = 0
        
        with transaction.atomic():
            self.stdout.write("\n🚀 Iniciando carga y vinculación...\n")
            
            for local_filename, study in zip(pdf_files, candidate_studies):
                full_local_path = folder_path / local_filename
                
                try:
                    # A. Generar ruta destino en Storage (MinIO/S3)
                    # Usamos UUID para evitar colisiones, pero guardamos referencia del nombre original
                    ext = os.path.splitext(local_filename)[1]
                    storage_filename = f"papers/{study.uuid}{ext}"
                    
                    # B. Subir archivo (Stream directo)
                    with open(full_local_path, 'rb') as f:
                        django_file = File(f)
                        
                        # Si ya existía un archivo previo en esa ruta (mismo UUID), default_storage maneja el nombre
                        # Pero como usamos study.uuid, idealmente borramos el anterior si existe para limpiar
                        if study.pdf_path and default_storage.exists(study.pdf_path):
                            default_storage.delete(study.pdf_path)
                            
                        saved_path = default_storage.save(storage_filename, django_file)

                    # C. Actualizar el Modelo
                    study.pdf_path = saved_path
                    study.download_status = 'texto_completo_disponible'
                    study.status = 'downloaded' # Actualizamos el estado del workflow
                    study.page_count = 0 # Opcional: Podrías usar pypdf aquí para contar real
                    
                    # Guardamos un log en field_origins para saber que esto fue manual
                    origins = study.field_origins or {}
                    origins['pdf_file'] = f"Local Load: {local_filename}"
                    study.field_origins = origins
                    
                    study.save()
                    
                    self.stdout.write(f"  ✅ Asignado: {local_filename[:20]}... -> Estudio {study.uuid}")
                    updated_count += 1

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ❌ Error con {local_filename}: {str(e)}"))

        # Resumen
        self.stdout.write(self.style.SUCCESS('--------------------------------------'))
        self.stdout.write(self.style.SUCCESS(f'🎉 PROCESO FINALIZADO.'))
        self.stdout.write(f'   - Archivos locales leídos: {len(pdf_files)}')
        self.stdout.write(f'   - Estudios actualizados: {updated_count}')
        self.stdout.write(self.style.SUCCESS('--------------------------------------'))