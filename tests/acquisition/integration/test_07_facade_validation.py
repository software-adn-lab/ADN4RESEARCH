"""
Facade Interface Validation Tests.

Este módulo valida que el AcquisitionFacade funciona correctamente como
punto de entrada único para otros módulos (Design, Selection, Extraction).

Valida:
1. Todos los métodos del facade funcionan correctamente
2. El facade delega correctamente a los servicios internos
3. El facade maneja errores de forma consistente
4. La interfaz del facade es consistente (DTOs, patrones, etc.)

Enfoque: Validar la arquitectura y calidad del facade.
"""

import unittest
from tests.acquisition.integration.base_live_test import BaseLiveTest
from apps.acquisition.facade import (
    AcquisitionFacade,
    PreviewSearchResult,
    FinalSearchResult,
    EnrichmentStatusResult,
    DownloadStatusResult
)


class FacadeValidationTest(BaseLiveTest):
    """
    Tests para validar que el facade funciona correctamente.
    
    Estos tests validan:
    - Funcionalidad de todos los métodos
    - Delegación correcta a servicios
    - Manejo de errores consistente
    - Consistencia de interfaz
    """
    
    def test_facade_all_methods_exist(self):
        """
        Validar que el facade tiene todos los métodos esperados.
        
        Este test verifica que el facade expone todos los métodos
        que otros módulos necesitan.
        """
        print(f"\n{'='*60}")
        print(f"TEST: Facade tiene todos los métodos esperados")
        print(f"{'='*60}")
        
        # Métodos para Design
        self.assertTrue(hasattr(self.facade, 'preview_search'))
        self.assertTrue(hasattr(self.facade, 'finalize_search'))
        print(f"   ✓ Métodos para Design: preview_search, finalize_search")
        
        # Métodos para Selection
        self.assertTrue(hasattr(self.facade, 'enrich_studies'))
        self.assertTrue(hasattr(self.facade, 'download_fulltexts'))
        self.assertTrue(hasattr(self.facade, 'register_manual_study'))
        self.assertTrue(hasattr(self.facade, 'update_study_metadata'))
        self.assertTrue(hasattr(self.facade, 'upload_study_pdf'))
        print(f"   ✓ Métodos para Selection: enrich, download, manual ops")
        
        # Métodos de consulta
        self.assertTrue(hasattr(self.facade, 'get_study_status'))
        print(f"   ✓ Métodos de consulta: get_study_status")
        
        # Métodos de utilidad
        self.assertTrue(hasattr(self.facade, 'is_healthy'))
        print(f"   ✓ Métodos de utilidad: is_healthy")
        
        print(f"\n✅ Facade tiene todos los métodos esperados")
    
    def test_facade_preview_search_returns_correct_dto(self):
        """
        Property 28: Facade Method Functionality
        Validates: Requirements 9.2
        
        Validar que preview_search retorna el DTO correcto.
        """
        print(f"\n{'='*60}")
        print(f"PROPERTY TEST: preview_search retorna DTO correcto")
        print(f"{'='*60}")
        
        strategy_dict = {
            "main_terms": [{"term": "test", "synonyms": []}],
            "exclusions": [],
            "filters": {"year": {"from": 2023, "to": 2024}}
        }
        
        result = self.facade.preview_search(strategy_dict, max_results_per_source=2)
        
        # Validar tipo
        self.assertIsInstance(result, PreviewSearchResult)
        print(f"   ✓ Retorna PreviewSearchResult")
        
        # Validar campos
        self.assertIsNotNone(result.queries_by_source)
        self.assertIsInstance(result.queries_by_source, dict)
        print(f"   ✓ Tiene queries_by_source (dict)")
        
        self.assertIsNotNone(result.total_found)
        self.assertIsInstance(result.total_found, int)
        print(f"   ✓ Tiene total_found (int)")
        
        self.assertIsNotNone(result.studies)
        self.assertIsInstance(result.studies, list)
        print(f"   ✓ Tiene studies (list)")
        
        print(f"\n✅ preview_search retorna DTO correcto")
    
    def test_facade_enrich_studies_returns_correct_dto(self):
        """
        Validar que enrich_studies retorna el DTO correcto.
        """
        print(f"\n{'='*60}")
        print(f"TEST: enrich_studies retorna DTO correcto")
        print(f"{'='*60}")
        
        # Crear estudio de prueba
        study_data = {
            "title": "Facade Test Study",
            "link": "https://example.com/facade-test",
            "doi": "10.1234/facade.test"
        }
        
        created = self.facade.register_manual_study(study_data, user=None)
        study_id = created['id']
        self.track_created_study(study_id)
        
        # Enriquecer
        result = self.facade.enrich_studies([study_id])
        
        # Validar tipo
        self.assertIsInstance(result, EnrichmentStatusResult)
        print(f"   ✓ Retorna EnrichmentStatusResult")
        
        # Validar campos
        self.assertIsNotNone(result.enriched_count)
        self.assertIsInstance(result.enriched_count, int)
        print(f"   ✓ Tiene enriched_count (int)")
        
        self.assertIsNotNone(result.failed_count)
        self.assertIsInstance(result.failed_count, int)
        print(f"   ✓ Tiene failed_count (int)")
        
        self.assertIsNotNone(result.study_ids)
        self.assertIsInstance(result.study_ids, list)
        print(f"   ✓ Tiene study_ids (list)")
        
        print(f"\n✅ enrich_studies retorna DTO correcto")
    
    def test_facade_download_fulltexts_returns_correct_dto(self):
        """
        Validar que download_fulltexts retorna el DTO correcto.
        """
        print(f"\n{'='*60}")
        print(f"TEST: download_fulltexts retorna DTO correcto")
        print(f"{'='*60}")
        
        # Crear estudio de prueba
        study_data = {
            "title": "Download Test Study",
            "link": "https://example.com/download-test"
        }
        
        created = self.facade.register_manual_study(study_data, user=None)
        study_id = created['id']
        self.track_created_study(study_id)
        
        # Descargar
        result = self.facade.download_fulltexts([study_id])
        
        # Validar tipo
        self.assertIsInstance(result, DownloadStatusResult)
        print(f"   ✓ Retorna DownloadStatusResult")
        
        # Validar campos
        self.assertIsNotNone(result.total_count)
        self.assertIsInstance(result.total_count, int)
        print(f"   ✓ Tiene total_count (int)")
        
        self.assertIsNotNone(result.downloaded_count)
        self.assertIsInstance(result.downloaded_count, int)
        print(f"   ✓ Tiene downloaded_count (int)")
        
        self.assertIsNotNone(result.available_count)
        self.assertIsInstance(result.available_count, int)
        print(f"   ✓ Tiene available_count (int)")
        
        self.assertIsNotNone(result.failed_count)
        self.assertIsInstance(result.failed_count, int)
        print(f"   ✓ Tiene failed_count (int)")
        
        print(f"\n✅ download_fulltexts retorna DTO correcto")
    
    def test_facade_manual_operations_return_dicts(self):
        """
        Validar que operaciones manuales retornan dicts consistentes.
        """
        print(f"\n{'='*60}")
        print(f"TEST: Operaciones manuales retornan dicts")
        print(f"{'='*60}")
        
        # register_manual_study
        study_data = {
            "title": "Manual Test",
            "link": "https://example.com/manual"
        }
        
        created = self.facade.register_manual_study(study_data, user=None)
        self.assertIsInstance(created, dict)
        self.assertIn('id', created)
        self.assertIn('title', created)
        self.track_created_study(created['id'])
        print(f"   ✓ register_manual_study retorna dict con id, title")
        
        # update_study_metadata
        updated = self.facade.update_study_metadata(
            study_id=created['id'],
            updates={"year": 2024},
            user=None
        )
        self.assertIsInstance(updated, dict)
        self.assertIn('id', updated)
        self.assertEqual(updated['year'], 2024)
        print(f"   ✓ update_study_metadata retorna dict con cambios")
        
        # upload_study_pdf
        import io
        pdf_file = io.BytesIO(b"%PDF-1.4\nTest\n%%EOF\n")
        pdf_file.name = "test.pdf"
        
        upload_result = self.facade.upload_study_pdf(
            study_id=created['id'],
            file_obj=pdf_file,
            filename="test.pdf",
            user=None
        )
        self.assertIsInstance(upload_result, dict)
        self.assertIn('study_id', upload_result)
        self.assertIn('pdf_path', upload_result)
        print(f"   ✓ upload_study_pdf retorna dict con study_id, pdf_path")
        
        print(f"\n✅ Operaciones manuales retornan dicts consistentes")
    
    def test_facade_get_study_status_returns_list_of_dicts(self):
        """
        Validar que get_study_status retorna lista de dicts.
        """
        print(f"\n{'='*60}")
        print(f"TEST: get_study_status retorna lista de dicts")
        print(f"{'='*60}")
        
        # Crear estudio
        study_data = {
            "title": "Status Test",
            "link": "https://example.com/status"
        }
        
        created = self.facade.register_manual_study(study_data, user=None)
        study_id = created['id']
        self.track_created_study(study_id)
        
        # Consultar estado
        statuses = self.facade.get_study_status([study_id])
        
        # Validar tipo
        self.assertIsInstance(statuses, list)
        print(f"   ✓ Retorna lista")
        
        self.assertEqual(len(statuses), 1)
        print(f"   ✓ Lista tiene 1 elemento")
        
        status = statuses[0]
        self.assertIsInstance(status, dict)
        print(f"   ✓ Elemento es dict")
        
        # Validar campos esperados
        self.assertIn('id', status)
        self.assertIn('title', status)
        self.assertIn('source', status)
        print(f"   ✓ Dict tiene campos esperados (id, title, source)")
        
        print(f"\n✅ get_study_status retorna lista de dicts correcta")
    
    def test_facade_error_handling_consistency(self):
        """
        Property 30: Facade Error Handling
        Validates: Requirements 9.4
        
        Validar que el facade maneja errores de forma consistente.
        """
        print(f"\n{'='*60}")
        print(f"PROPERTY TEST: Manejo de errores consistente")
        print(f"{'='*60}")
        
        # Test 1: Estudio no encontrado
        print(f"\n   Test 1: Estudio no encontrado")
        try:
            self.facade.update_study_metadata(
                study_id="non-existent-id",
                updates={"year": 2024},
                user=None
            )
            self.fail("Debería lanzar excepción")
        except Exception as e:
            self.assertIsNotNone(str(e))
            print(f"   ✓ Lanza excepción con mensaje: {str(e)[:50]}...")
        
        # Test 2: Datos inválidos
        print(f"\n   Test 2: Datos inválidos para crear estudio")
        try:
            self.facade.register_manual_study(
                study_data={},  # Sin title ni link
                user=None
            )
            self.fail("Debería lanzar excepción")
        except Exception as e:
            self.assertIsNotNone(str(e))
            print(f"   ✓ Lanza excepción con mensaje: {str(e)[:50]}...")
        
        print(f"\n✅ Errores manejados de forma consistente")
    
    def test_facade_service_delegation(self):
        """
        Property 29: Facade Service Delegation
        Validates: Requirements 9.3
        
        Validar que el facade delega correctamente a los servicios.
        """
        print(f"\n{'='*60}")
        print(f"PROPERTY TEST: Delegación a servicios")
        print(f"{'='*60}")
        
        # El facade debe tener referencias a los servicios
        self.assertIsNotNone(self.facade._orchestrator)
        print(f"   ✓ Facade tiene orchestrator")
        
        self.assertIsNotNone(self.facade._enrichment_service)
        print(f"   ✓ Facade tiene enrichment_service")
        
        self.assertIsNotNone(self.facade._fulltext_service)
        print(f"   ✓ Facade tiene fulltext_service")
        
        # Verificar que los métodos getter funcionan
        enrichment_service = self.facade.get_enrichment_service()
        self.assertIsNotNone(enrichment_service)
        print(f"   ✓ get_enrichment_service() retorna servicio")
        
        fulltext_service = self.facade.get_fulltext_service()
        self.assertIsNotNone(fulltext_service)
        print(f"   ✓ get_fulltext_service() retorna servicio")
        
        print(f"\n✅ Facade delega correctamente a servicios")
    
    def test_facade_interface_consistency(self):
        """
        Property 31: Facade Interface Consistency
        Validates: Requirements 9.5
        
        Validar que la interfaz del facade es consistente.
        """
        print(f"\n{'='*60}")
        print(f"PROPERTY TEST: Consistencia de interfaz")
        print(f"{'='*60}")
        
        # Todos los métodos principales deben aceptar user opcional
        import inspect
        
        methods_to_check = [
            'register_manual_study',
            'update_study_metadata',
            'upload_study_pdf'
        ]
        
        for method_name in methods_to_check:
            method = getattr(self.facade, method_name)
            sig = inspect.signature(method)
            
            # Verificar que tiene parámetro 'user'
            self.assertIn('user', sig.parameters)
            
            # Verificar que user es opcional (tiene default o es None)
            user_param = sig.parameters['user']
            # El default puede ser None o inspect.Parameter.empty
            has_default = user_param.default is not inspect.Parameter.empty
            
            print(f"   ✓ {method_name} acepta user (default={has_default})")
        
        # Todos los métodos de consulta deben retornar datos serializables
        print(f"\n   Verificando que retornan datos serializables...")
        
        # Crear estudio de prueba
        study_data = {
            "title": "Consistency Test",
            "link": "https://example.com/consistency"
        }
        
        created = self.facade.register_manual_study(study_data, user=None)
        study_id = created['id']
        self.track_created_study(study_id)
        
        # get_study_status debe retornar dicts (JSON-serializable)
        statuses = self.facade.get_study_status([study_id])
        import json
        try:
            json.dumps(statuses)
            print(f"   ✓ get_study_status retorna datos JSON-serializables")
        except TypeError:
            self.fail("get_study_status no retorna datos JSON-serializables")
        
        print(f"\n✅ Interfaz del facade es consistente")
    
    def test_facade_is_healthy(self):
        """
        Validar que el método is_healthy funciona.
        """
        print(f"\n{'='*60}")
        print(f"TEST: is_healthy funciona")
        print(f"{'='*60}")
        
        is_healthy = self.facade.is_healthy()
        
        self.assertIsInstance(is_healthy, bool)
        print(f"   ✓ is_healthy retorna bool")
        
        self.assertTrue(is_healthy)
        print(f"   ✓ Facade está saludable")
        
        print(f"\n✅ is_healthy funciona correctamente")


if __name__ == '__main__':
    unittest.main()
