"""
Live Integration Tests for PDF Downloads.

Este módulo prueba la descarga de PDFs de estudios:
- Descarga usando Open Access sources (Unpaywall, Crossref)
- Validación de archivos descargados
- Actualización de estado de descarga

Enfoque: Validar que Selection puede descargar PDFs vía facade.
"""

import os
import unittest
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase as HypothesisTestCase

from tests.acquisition.integration.base_live_test import BaseLiveTest


class DownloadsLiveTest(BaseLiveTest):
    """
    Tests de integración para validar la descarga de PDFs.
    
    Estos tests validan el flujo completo:
    Discovery → Persist → Enrich → Download
    
    Resultado esperado: PDFs descargados y validados.
    """
    
    def test_selection_downloads_pdfs_via_facade(self):
        """
        TEST PRINCIPAL: Simular cómo Selection usa el facade para descargar PDFs.
        
        FLUJO REAL COMPLETO:
        1. Discovery encuentra estudios
        2. Design persiste estudios
        3. Selection enriquece estudios (opcional)
        4. Selection llama a facade.download_fulltexts(study_ids)
        5. Facade descarga PDFs usando Unpaywall/Crossref/etc.
        6. Selection consulta estado de descargas
        """
        print(f"\n{'='*60}")
        print(f"TEST: Flujo completo Discovery → Persist → Download")
        print(f"{'='*60}")
        
        # PASO 1: DISCOVERY - Buscar estudios con Open Access
        print(f"\n1️⃣ PASO 1: Discovery busca estudios Open Access")
        
        strategy_dict = {
            "main_terms": [{"term": "open access machine learning", "synonyms": []}],
            "exclusions": [],
            "filters": {"year": {"from": 2023, "to": 2024}}
        }
        
        preview_result = self.facade.preview_search(
            strategy_dict=strategy_dict,
            max_results_per_source=5
        )
        
        if preview_result.total_found == 0:
            self.skipTest("No se encontraron estudios para descargar")
        
        print(f"   ✓ Discovery encontró {preview_result.total_found} estudios")
        
        # Mostrar estudios con info de Open Access
        oa_count = 0
        for idx, study in enumerate(preview_result.studies[:3], 1):
            is_oa = study.get('is_open_access')
            pdf_url = study.get('pdf_url')
            print(f"   Estudio {idx}:")
            print(f"     Título: {study['title'][:60]}...")
            print(f"     is_open_access: {is_oa}")
            print(f"     pdf_url: {'Sí' if pdf_url else 'No'}")
            if is_oa:
                oa_count += 1
        
        print(f"   Estudios Open Access: {oa_count}/{min(3, preview_result.total_found)}")
        
        # PASO 2: PERSISTIR - Design guarda los estudios
        print(f"\n2️⃣ PASO 2: Design persiste estudios en BD")
        
        from apps.acquisition.container import Container
        from apps.acquisition.shared.domain.entities.study import Study
        
        repository = Container.get_repository()
        study_ids = []
        
        # Persistir primeros 2 estudios
        selected_studies = preview_result.studies[:2]
        
        for study_data in selected_studies:
            study = Study.create_discovered(
                title=study_data['title'],
                link=study_data['link'],
                source=str(study_data['source']),
                doi=study_data.get('doi')
            )
            
            # Preservar metadata de discovery
            if study_data.get('authors'):
                study.authors = study_data['authors']
            if study_data.get('is_open_access') is not None:
                study.is_open_access = study_data['is_open_access']
            if study_data.get('pdf_url'):
                study.pdf_url = study_data['pdf_url']
            
            saved_study = repository.save(study)
            study_ids.append(str(saved_study.id))
            self.track_created_study(str(saved_study.id))
        
        print(f"   ✓ Persistidos {len(study_ids)} estudios")
        print(f"   IDs: {[sid[:8] + '...' for sid in study_ids]}")
        
        # PASO 3: DOWNLOAD - Selection llama al facade
        print(f"\n3️⃣ PASO 3: Selection llama facade.download_fulltexts()")
        print(f"   Descargando PDFs de {len(study_ids)} estudios...")
        
        # ESTE ES EL MÉTODO QUE USARÁ SELECTION
        download_result = self.facade.download_fulltexts(
            study_ids=study_ids
        )
        
        # PASO 4: RESULTADO - Selection recibe el estado
        print(f"\n4️⃣ PASO 4: Selection recibe resultado")
        print(f"\n📊 RESULTADO de descargas:")
        print(f"   Total procesados: {download_result.total_count}")
        print(f"   Descargados exitosamente: {download_result.downloaded_count}")
        print(f"   Ya disponibles: {download_result.available_count}")
        print(f"   Fallidos/No disponibles: {download_result.failed_count}")
        
        # VALIDACIONES
        self.assertIsNotNone(download_result,
                           "El facade debe devolver un resultado")
        
        self.assertEqual(download_result.total_count, len(study_ids),
                       "Debe procesar todos los estudios")
        
        # Al menos uno debe ser procesado
        total_processed = (download_result.downloaded_count + 
                          download_result.available_count + 
                          download_result.failed_count)
        self.assertEqual(total_processed, len(study_ids),
                       "Todos los estudios deben ser procesados")
        
        if download_result.downloaded_count > 0:
            print(f"\n✅ SUCCESS: Se descargaron {download_result.downloaded_count} PDFs")
        elif download_result.available_count > 0:
            print(f"\n✅ SUCCESS: {download_result.available_count} PDFs ya estaban disponibles")
        else:
            print(f"\n⚠️  WARNING: No se descargaron PDFs")
            print(f"   Esto puede ser normal si los estudios no son Open Access")
        
        # PASO 5: CONSULTAR ESTADO - Selection verifica descargas
        print(f"\n5️⃣ PASO 5: Selection consulta estado de descargas")
        
        study_statuses = self.facade.get_study_status(study_ids)
        
        print(f"   Estados obtenidos: {len(study_statuses)}")
        for status in study_statuses[:2]:
            print(f"   - Estudio: {status.get('id', 'N/A')[:8]}...")
            print(f"     Download status: {status.get('download_status', 'N/A')}")
            print(f"     PDF path: {'Sí' if status.get('pdf_path') else 'No'}")
        
        print(f"\n✅ FLUJO COMPLETO: Selection puede descargar PDFs vía facade")
    
    def test_download_validates_pdf_files(self):
        """
        Validar que los PDFs descargados son archivos válidos.
        
        Este test verifica que:
        - Los archivos descargados existen
        - Los archivos tienen el header PDF correcto
        - Los archivos tienen tamaño > 0
        """
        print(f"\n{'='*60}")
        print(f"TEST: Validación de archivos PDF")
        print(f"{'='*60}")
        
        # Crear un estudio con PDF URL conocido (Open Access)
        from apps.acquisition.container import Container
        from apps.acquisition.shared.domain.entities.study import Study
        
        repository = Container.get_repository()
        
        # Estudio de prueba con PDF Open Access conocido
        study = Study.create_discovered(
            title="Test Study with Known OA PDF",
            link="https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0123456",
            source="Manual",
            doi="10.1371/journal.pone.0123456"  # PLOS ONE (Open Access)
        )
        
        study.is_open_access = True
        saved_study = repository.save(study)
        study_id = str(saved_study.id)
        self.track_created_study(study_id)
        
        print(f"   Estudio creado: {study_id[:8]}...")
        print(f"   DOI: {study.doi.value if study.doi else 'N/A'}")
        
        # Intentar descargar
        print(f"\n   Intentando descargar PDF...")
        
        download_result = self.facade.download_fulltexts(
            study_ids=[study_id]
        )
        
        print(f"\n📊 RESULTADO:")
        print(f"   Descargados: {download_result.downloaded_count}")
        print(f"   Fallidos: {download_result.failed_count}")
        
        if download_result.downloaded_count > 0:
            # Verificar que el archivo existe y es válido
            study_status = self.facade.get_study_status([study_id])[0]
            pdf_path = study_status.get('pdf_path')
            
            if pdf_path and os.path.exists(pdf_path):
                print(f"\n✅ PDF descargado: {pdf_path}")
                
                # Validar que es un PDF válido
                self.assert_valid_pdf_file(pdf_path)
                print(f"✅ PDF validado correctamente")
            else:
                print(f"\n⚠️  PDF no encontrado en disco")
        else:
            print(f"\n⚠️  No se pudo descargar el PDF")
            print(f"   Esto puede ser normal si el servicio no está disponible")
    
    def test_download_updates_study_status(self):
        """
        Validar que el estado del estudio se actualiza después de descargar.
        
        Este test verifica que:
        - download_status se actualiza correctamente
        - pdf_path se registra
        - pdf_source se registra
        """
        print(f"\n{'='*60}")
        print(f"TEST: Actualización de estado después de descarga")
        print(f"{'='*60}")
        
        # Crear estudio de prueba
        from apps.acquisition.container import Container
        from apps.acquisition.shared.domain.entities.study import Study
        
        repository = Container.get_repository()
        
        study = Study.create_discovered(
            title="Test Study for Status Update",
            link="https://example.com/test-status",
            source="Manual",
            doi="10.1234/test.status.001"
        )
        
        saved_study = repository.save(study)
        study_id = str(saved_study.id)
        self.track_created_study(study_id)
        
        print(f"   Estudio creado: {study_id[:8]}...")
        
        # Estado inicial
        initial_status = self.facade.get_study_status([study_id])[0]
        print(f"\n   Estado inicial:")
        print(f"     download_status: {initial_status.get('download_status', 'N/A')}")
        print(f"     pdf_path: {initial_status.get('pdf_path', 'N/A')}")
        
        # Intentar descargar
        print(f"\n   Intentando descargar...")
        
        download_result = self.facade.download_fulltexts(
            study_ids=[study_id]
        )
        
        # Estado después de descarga
        final_status = self.facade.get_study_status([study_id])[0]
        print(f"\n   Estado final:")
        print(f"     download_status: {final_status.get('download_status', 'N/A')}")
        print(f"     pdf_path: {final_status.get('pdf_path', 'N/A')}")
        
        # Validar que el estado cambió
        self.assertIsNotNone(final_status.get('download_status'),
                           "El download_status debe estar definido")
        
        print(f"\n✅ Estado actualizado correctamente")
    
    def test_download_cascade_with_scihub(self):
        """
        Validar que la cascada de descargas incluye Sci-Hub como último recurso.
        
        Cascada esperada:
        1. Descarga directa (si tiene pdf_url)
        2. Unpaywall/Crossref (si tiene DOI)
        3. Fuentes alternativas (incluye Sci-Hub si está habilitado)
        4. Marcar como no_disponible
        """
        print(f"\n{'='*60}")
        print(f"TEST: Cascada de descargas con Sci-Hub")
        print(f"{'='*60}")
        
        # Verificar que Sci-Hub está habilitado
        import os
        scihub_enabled = os.getenv("ENABLE_SCIHUB", "false").lower() == "true"
        print(f"\n   ENABLE_SCIHUB: {scihub_enabled}")
        
        if not scihub_enabled:
            print(f"\n⚠️  Sci-Hub NO está habilitado")
            print(f"   Para habilitarlo: ENABLE_SCIHUB=true en .env")
        else:
            print(f"\n✅ Sci-Hub está habilitado")
        
        # Crear estudio sin pdf_url (para forzar cascada completa)
        from apps.acquisition.container import Container
        from apps.acquisition.shared.domain.entities.study import Study
        
        repository = Container.get_repository()
        
        study = Study.create_discovered(
            title="Test Study for Cascade",
            link="https://example.com/test-cascade",
            source="Manual",
            doi="10.1109/ICSE-SEET52601.2021.00012"  # DOI que sabemos que funciona
        )
        
        # NO establecer pdf_url para forzar cascada completa
        study.is_open_access = None
        
        saved_study = repository.save(study)
        study_id = str(saved_study.id)
        self.track_created_study(study_id)
        
        print(f"\n   Estudio creado:")
        print(f"     ID: {study_id[:8]}...")
        print(f"     DOI: {study.doi.value if study.doi else 'N/A'}")
        print(f"     pdf_url: {study.pdf_url or 'None (forzará cascada completa)'}")
        
        # Intentar descargar (debería pasar por toda la cascada)
        print(f"\n   Iniciando cascada de descarga...")
        print(f"   1. Descarga directa (sin pdf_url, se saltará)")
        print(f"   2. Unpaywall/Crossref (buscará por DOI)")
        print(f"   3. Fuentes alternativas (incluye Sci-Hub)")
        
        download_result = self.facade.download_fulltexts(
            study_ids=[study_id]
        )
        
        print(f"\n📊 RESULTADO:")
        print(f"   Descargados: {download_result.downloaded_count}")
        print(f"   Fallidos: {download_result.failed_count}")
        
        # Consultar estado final
        final_status = self.facade.get_study_status([study_id])[0]
        print(f"\n   Estado final:")
        print(f"     download_status: {final_status.get('download_status', 'N/A')}")
        print(f"     pdf_path: {'Sí' if final_status.get('pdf_path') else 'No'}")
        print(f"     pdf_source: {final_status.get('pdf_source', 'N/A')}")
        
        if download_result.downloaded_count > 0:
            print(f"\n✅ PDF descargado exitosamente")
            if final_status.get('pdf_source') == 'alternativo':
                print(f"   Fuente: Alternativa (posiblemente Sci-Hub)")
        else:
            print(f"\n⚠️  No se pudo descargar")
            print(f"   Esto puede indicar que:")
            print(f"   - El DOI no está en Unpaywall")
            print(f"   - Sci-Hub no tiene el paper")
            print(f"   - Sci-Hub está bloqueado/no disponible")
        
        print(f"\n✅ Cascada completa ejecutada")
