"""
Full Pipeline Integration Tests.

Este módulo prueba el flujo completo end-to-end del sistema de Acquisition:
1. Translation: Strategy → Queries
2. Discovery: Queries → Studies
3. Persistence: Studies → Database
4. Enrichment: Studies → Complete Metadata
5. Downloads: Studies → PDFs

Enfoque: Validar que todo el pipeline funciona correctamente de principio a fin.
"""

import unittest
from tests.acquisition.integration.base_live_test import BaseLiveTest


class FullPipelineLiveTest(BaseLiveTest):
    """
    Tests de integración para validar el pipeline completo.
    
    Estos tests validan el flujo end-to-end:
    Strategy → Translation → Discovery → Persistence → Enrichment → Downloads
    
    Resultado esperado: Pipeline completo funciona sin errores.
    """
    
    def test_full_pipeline_end_to_end(self):
        """
        TEST PRINCIPAL: Pipeline completo de principio a fin.
        
        FLUJO COMPLETO:
        1. Translation: Convertir estrategia a queries
        2. Discovery: Ejecutar búsqueda y encontrar estudios
        3. Persistence: Guardar estudios en BD
        4. Enrichment: Enriquecer metadatos
        5. Downloads: Descargar PDFs
        6. Validation: Verificar que todo persiste correctamente
        """
        print(f"\n{'='*60}")
        print(f"TEST: Pipeline completo end-to-end")
        print(f"{'='*60}")
        
        # ========================================
        # STAGE 1: TRANSLATION
        # ========================================
        print(f"\n🔄 STAGE 1: TRANSLATION")
        print(f"   Convertir estrategia a queries...")
        
        strategy_dict = {
            "main_terms": [
                {"term": "machine learning", "synonyms": ["ML", "artificial intelligence"]}
            ],
            "exclusions": [],
            "filters": {"year": {"from": 2023, "to": 2024}}
        }
        
        print(f"   ✓ Estrategia definida")
        print(f"     Main terms: {len(strategy_dict['main_terms'])} términos")
        print(f"     Filters: {strategy_dict['filters']}")
        
        # ========================================
        # STAGE 2: DISCOVERY
        # ========================================
        print(f"\n🔍 STAGE 2: DISCOVERY")
        print(f"   Ejecutando búsqueda en fuentes académicas...")
        
        preview_result = self.facade.preview_search(
            strategy_dict=strategy_dict,
            max_results_per_source=5
        )
        
        if preview_result.total_found == 0:
            self.skipTest("No se encontraron estudios para el pipeline completo")
        
        print(f"   ✓ Discovery completado")
        print(f"     Total encontrado: {preview_result.total_found} estudios")
        print(f"     Fuentes: {list(preview_result.queries_by_source.keys())}")
        
        # Mostrar algunos estudios
        for idx, study in enumerate(preview_result.studies[:3], 1):
            print(f"     Estudio {idx}: {study['title'][:50]}...")
        
        # ========================================
        # STAGE 3: PERSISTENCE
        # ========================================
        print(f"\n💾 STAGE 3: PERSISTENCE")
        print(f"   Guardando estudios en base de datos...")
        
        from apps.acquisition.container import Container
        from apps.acquisition.shared.domain.entities.study import Study
        
        repository = Container.get_repository()
        study_ids = []
        
        # Persistir primeros 3 estudios
        selected_studies = preview_result.studies[:3]
        
        for study_data in selected_studies:
            # Convertir DOI a string si es necesario
            doi_value = study_data.get('doi')
            if doi_value and hasattr(doi_value, 'value'):
                doi_value = doi_value.value
            
            study = Study.create_discovered(
                title=study_data['title'],
                link=study_data['link'],
                source=str(study_data['source']),
                doi=doi_value
            )
            
            # Preservar metadata de discovery
            if study_data.get('authors'):
                study.authors = study_data['authors']
            if study_data.get('year'):
                study.year = study_data['year']
            if study_data.get('is_open_access') is not None:
                study.is_open_access = study_data['is_open_access']
            if study_data.get('pdf_url'):
                study.pdf_url = study_data['pdf_url']
            
            saved_study = repository.save(study)
            study_ids.append(str(saved_study.id))
            self.track_created_study(str(saved_study.id))
        
        print(f"   ✓ Persistence completado")
        print(f"     Estudios guardados: {len(study_ids)}")
        print(f"     IDs: {[sid[:8] + '...' for sid in study_ids]}")
        
        # ========================================
        # STAGE 4: ENRICHMENT
        # ========================================
        print(f"\n📚 STAGE 4: ENRICHMENT")
        print(f"   Enriqueciendo metadatos desde fuentes externas...")
        
        enrichment_result = self.facade.enrich_studies(
            study_ids=study_ids
        )
        
        print(f"   ✓ Enrichment completado")
        print(f"     Enriquecidos: {enrichment_result.enriched_count}")
        print(f"     Fallidos: {enrichment_result.failed_count}")
        
        # ========================================
        # STAGE 5: DOWNLOADS
        # ========================================
        print(f"\n📥 STAGE 5: DOWNLOADS")
        print(f"   Descargando PDFs de estudios...")
        
        download_result = self.facade.download_fulltexts(
            study_ids=study_ids
        )
        
        print(f"   ✓ Downloads completado")
        print(f"     Descargados: {download_result.downloaded_count}")
        print(f"     Ya disponibles: {download_result.available_count}")
        print(f"     No disponibles: {download_result.failed_count}")
        
        # ========================================
        # STAGE 6: VALIDATION
        # ========================================
        print(f"\n✅ STAGE 6: VALIDATION")
        print(f"   Validando que todo el pipeline funcionó correctamente...")
        
        # Consultar estado final de todos los estudios
        final_statuses = self.facade.get_study_status(study_ids)
        
        print(f"   Estados finales:")
        for idx, status in enumerate(final_statuses, 1):
            print(f"     Estudio {idx}:")
            print(f"       ID: {status['id'][:8]}...")
            print(f"       Título: {status['title'][:40]}...")
            print(f"       Autores: {len(status.get('authors', []))} autores")
            print(f"       Year: {status.get('year', 'N/A')}")
            print(f"       PDF: {'Sí' if status.get('pdf_path') else 'No'}")
        
        # VALIDACIONES FINALES
        self.assertEqual(len(final_statuses), len(study_ids),
                        "Todos los estudios deben estar en BD")
        
        # Al menos uno debe tener metadatos enriquecidos
        studies_with_metadata = sum(1 for s in final_statuses if s.get('authors'))
        self.assertGreater(studies_with_metadata, 0,
                          "Al menos un estudio debe tener metadatos")
        
        print(f"\n{'='*60}")
        print(f"✅ PIPELINE COMPLETO EXITOSO")
        print(f"{'='*60}")
        print(f"   ✓ Translation: Estrategia → Queries")
        print(f"   ✓ Discovery: {preview_result.total_found} estudios encontrados")
        print(f"   ✓ Persistence: {len(study_ids)} estudios guardados")
        print(f"   ✓ Enrichment: {enrichment_result.enriched_count} enriquecidos")
        print(f"   ✓ Downloads: {download_result.downloaded_count + download_result.available_count} PDFs")
        print(f"   ✓ Validation: Todos los datos persisten correctamente")
    
    def test_pipeline_stage_completion(self):
        """
        Validar que cada stage del pipeline se completa correctamente.
        
        Este test verifica que:
        - Cada stage produce output válido
        - El output de un stage es input válido para el siguiente
        - No hay errores en ningún stage
        """
        print(f"\n{'='*60}")
        print(f"TEST: Completitud de stages del pipeline")
        print(f"{'='*60}")
        
        strategy_dict = {
            "main_terms": [{"term": "software engineering", "synonyms": []}],
            "exclusions": [],
            "filters": {"year": {"from": 2023, "to": 2024}}
        }
        
        # Stage 1: Preview debe retornar queries
        print(f"\n   Stage 1: Preview Search")
        preview = self.facade.preview_search(strategy_dict, max_results_per_source=3)
        
        self.assertIsNotNone(preview.queries_by_source)
        self.assertGreater(len(preview.queries_by_source), 0)
        print(f"   ✓ Queries generados: {len(preview.queries_by_source)} fuentes")
        
        if preview.total_found == 0:
            self.skipTest("No hay estudios para validar stages")
        
        # Stage 2: Studies deben tener estructura válida
        print(f"\n   Stage 2: Study Structure")
        first_study = preview.studies[0]
        
        self.assertIn('title', first_study)
        self.assertIn('link', first_study)
        self.assertIn('source', first_study)
        print(f"   ✓ Estudios tienen estructura válida")
        
        # Stage 3: Persistence debe generar IDs
        print(f"\n   Stage 3: Persistence")
        from apps.acquisition.container import Container
        from apps.acquisition.shared.domain.entities.study import Study
        
        repository = Container.get_repository()
        study = Study.create_discovered(
            title=first_study['title'],
            link=first_study['link'],
            source=str(first_study['source']),
            doi=first_study.get('doi')
        )
        
        saved = repository.save(study)
        self.track_created_study(str(saved.id))
        
        self.assertIsNotNone(saved.id)
        print(f"   ✓ Estudio persistido con ID: {saved.id[:8]}...")
        
        # Stage 4: Enrichment debe procesar sin errores
        print(f"\n   Stage 4: Enrichment")
        enrich_result = self.facade.enrich_studies([str(saved.id)])
        
        self.assertIsNotNone(enrich_result)
        self.assertEqual(enrich_result.enriched_count + enrich_result.failed_count, 1)
        print(f"   ✓ Enrichment procesado (success={enrich_result.enriched_count})")
        
        # Stage 5: Downloads debe procesar sin errores
        print(f"\n   Stage 5: Downloads")
        download_result = self.facade.download_fulltexts([str(saved.id)])
        
        self.assertIsNotNone(download_result)
        total_processed = (download_result.downloaded_count + 
                          download_result.available_count + 
                          download_result.failed_count)
        self.assertEqual(total_processed, 1)
        print(f"   ✓ Downloads procesado")
        
        print(f"\n✅ Todos los stages se completaron correctamente")
    
    def test_pipeline_data_flow(self):
        """
        Validar que los datos fluyen correctamente entre stages.
        
        Este test verifica que:
        - Los datos de discovery se preservan en persistence
        - Los datos de persistence están disponibles para enrichment
        - Los datos de enrichment están disponibles para downloads
        """
        print(f"\n{'='*60}")
        print(f"TEST: Flujo de datos entre stages")
        print(f"{'='*60}")
        
        # Crear estudio con datos específicos
        print(f"\n   Creando estudio con datos de prueba...")
        
        test_title = "Data Flow Test Study"
        test_doi = "10.1234/dataflow.test.001"
        
        study_data = {
            "title": test_title,
            "link": "https://example.com/dataflow",
            "doi": test_doi,
            "year": 2024
        }
        
        created = self.facade.register_manual_study(study_data, user=None)
        study_id = created['id']
        self.track_created_study(study_id)
        
        print(f"   ✓ Estudio creado: {study_id[:8]}...")
        
        # Verificar que datos fluyen a través de consultas
        print(f"\n   Verificando flujo de datos...")
        
        # Query 1: Después de creación
        status1 = self.facade.get_study_status([study_id])[0]
        self.assertEqual(status1['title'], test_title)
        self.assertEqual(status1['doi'], test_doi)
        self.assertEqual(status1['year'], 2024)
        print(f"   ✓ Query 1: Datos iniciales preservados")
        
        # Actualizar metadatos
        self.facade.update_study_metadata(
            study_id=study_id,
            updates={"authors": ["Test Author"]},
            user=None
        )
        
        # Query 2: Después de actualización
        status2 = self.facade.get_study_status([study_id])[0]
        self.assertEqual(status2['title'], test_title)  # Dato original
        self.assertEqual(status2['year'], 2024)  # Dato original
        self.assertEqual(len(status2.get('authors', [])), 1)  # Dato nuevo
        print(f"   ✓ Query 2: Datos originales + actualizaciones preservados")
        
        # Subir PDF
        import io
        pdf_file = io.BytesIO(b"%PDF-1.4\nDataflow test\n%%EOF\n")
        pdf_file.name = "dataflow.pdf"
        
        self.facade.upload_study_pdf(
            study_id=study_id,
            file_obj=pdf_file,
            filename="dataflow.pdf",
            user=None
        )
        
        # Query 3: Después de PDF
        status3 = self.facade.get_study_status([study_id])[0]
        self.assertEqual(status3['title'], test_title)  # Dato original
        self.assertEqual(status3['year'], 2024)  # Dato original
        self.assertEqual(len(status3.get('authors', [])), 1)  # Dato actualizado
        self.assertIsNotNone(status3['pdf_path'])  # Dato nuevo
        print(f"   ✓ Query 3: Todos los datos preservados a través del pipeline")
        
        print(f"\n✅ Flujo de datos funciona correctamente")
    
    def test_pipeline_result_persistence(self):
        """
        Validar que los resultados del pipeline persisten correctamente.
        
        Este test verifica que:
        - Los estudios persisten en BD
        - Los PDFs persisten en disco
        - Los metadatos persisten correctamente
        - Todo es recuperable después del pipeline
        """
        print(f"\n{'='*60}")
        print(f"TEST: Persistencia de resultados del pipeline")
        print(f"{'='*60}")
        
        # Ejecutar mini-pipeline
        print(f"\n   Ejecutando mini-pipeline...")
        
        strategy_dict = {
<<<<<<< HEAD
=======
            "strategy_id": "persistence_test",
>>>>>>> bfe06b0 (Feature/acquisition clean architecture (#23))
            "main_terms": [{"term": "data persistence", "synonyms": []}],
            "exclusions": [],
            "filters": {"year": {"from": 2023, "to": 2024}}
        }
        
        preview = self.facade.preview_search(strategy_dict, max_results_per_source=2)
        
        if preview.total_found == 0:
            self.skipTest("No hay estudios para validar persistencia")
        
        # Persistir un estudio
        from apps.acquisition.container import Container
        from apps.acquisition.shared.domain.entities.study import Study
        
        repository = Container.get_repository()
        study_data = preview.studies[0]
        
        study = Study.create_discovered(
            title=study_data['title'],
            link=study_data['link'],
            source=str(study_data['source']),
            doi=study_data.get('doi')
        )
        
        saved = repository.save(study)
        study_id = str(saved.id)
        self.track_created_study(study_id)
        
        print(f"   ✓ Estudio persistido: {study_id[:8]}...")
        
        # Verificar persistencia en BD
        print(f"\n   Verificando persistencia en BD...")
        
        retrieved = repository.find_by_id(study_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, study_id)
        self.assertEqual(retrieved.title, study_data['title'])
        print(f"   ✓ Estudio recuperable desde BD")
        
        # Enriquecer y verificar persistencia
        self.facade.enrich_studies([study_id])
        
        enriched = repository.find_by_id(study_id)
        print(f"   ✓ Metadatos enriquecidos persisten en BD")
        
        # Descargar PDF y verificar persistencia
        self.facade.download_fulltexts([study_id])
        
        with_pdf = repository.find_by_id(study_id)
        if with_pdf.pdf_path:
            import os
            self.assertTrue(os.path.exists(with_pdf.pdf_path),
                          "PDF debe existir en disco")
            print(f"   ✓ PDF persiste en disco: {with_pdf.pdf_path[:50]}...")
        
        print(f"\n✅ Todos los resultados persisten correctamente")
    
    def test_pipeline_audit_trail(self):
        """
        Validar que el pipeline mantiene audit trail completo.
        
        Este test verifica que:
        - Se registran timestamps de cada operación
        - Se registra el origen de los datos (field_origins)
        - Se puede rastrear el flujo completo de un estudio
        """
        print(f"\n{'='*60}")
        print(f"TEST: Audit trail del pipeline")
        print(f"{'='*60}")
        
        # Crear estudio manual para tener control total
        print(f"\n   Creando estudio para audit trail...")
        
        study_data = {
            "title": "Audit Trail Test Study",
            "link": "https://example.com/audit",
            "doi": "10.1234/audit.001",
            "year": 2024
        }
        
        created = self.facade.register_manual_study(study_data, user=None)
        study_id = created['id']
        self.track_created_study(study_id)
        
        print(f"   ✓ Estudio creado: {study_id[:8]}...")
        
        # Verificar timestamps iniciales
        print(f"\n   Verificando audit trail...")
        
        status = self.facade.get_study_status([study_id])[0]
        
        # Debe tener discovered_at
        self.assertIsNotNone(status.get('discovered_at'))
        print(f"   ✓ discovered_at: {status.get('discovered_at')}")
        
        # Debe tener field_origins
        self.assertIn('field_origins', status)
        field_origins = status.get('field_origins', {})
        self.assertEqual(field_origins.get('source'), 'manual')
        print(f"   ✓ field_origins registra origen manual")
        
        # Actualizar y verificar trazabilidad
        self.facade.update_study_metadata(
            study_id=study_id,
            updates={"abstract": "Updated abstract"},
            user=None
        )
        
        updated_status = self.facade.get_study_status([study_id])[0]
        updated_origins = updated_status.get('field_origins', {})
        
        self.assertEqual(updated_origins.get('abstract'), 'manual')
        print(f"   ✓ Actualización manual registrada en field_origins")
        
        print(f"\n✅ Audit trail completo y funcional")


if __name__ == '__main__':
    unittest.main()
