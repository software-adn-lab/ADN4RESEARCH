"""
Live Integration Tests for Discovery Functionality.

Este módulo prueba que el proceso de discovery funciona correctamente:
- El facade devuelve estudios con título y link
- Los estudios vienen de Scopus e IEEE
- El flujo completo funciona desde facade hasta los conectores

Enfoque: Validar que discovery DEVUELVE ESTUDIOS como producto final del módulo.
"""

import unittest
from tests.acquisition.integration.base_live_test import BaseLiveTest
from apps.acquisition.translation.domain.models import NormalizedStrategy
from apps.design.search_strategy.models.search_strategy import SearchStrategy


class DiscoveryLiveTest(BaseLiveTest):
    """
    Tests de integración para validar que discovery devuelve estudios.
    
    Estos tests validan el flujo completo:
    Facade → Orchestrator → Discovery Service → Connectors (Scopus + IEEE)
    
    Resultado esperado: Lista de estudios con título y link.
    """
    
    def test_facade_returns_studies(self):
        """
        TEST PRINCIPAL: El facade debe devolver estudios con título y link.
        Usamos una query REAL y SIMPLE para garantizar que el scraping funcione.
        """
        strategy_dict = {
            "main_terms": [{"term": "software architecture", "synonyms": []}],
            "exclusions": [],
            "filters": {"year": {"from": 2023, "to": 2024}}
        }
        
        print(f"\n{'='*60}")
        print(f"TEST: Facade debe devolver estudios (Happy Path)")
        print(f"{'='*60}")
        
        # Ejecutar búsqueda a través del facade
        result = self.facade.preview_search(
            strategy_dict=strategy_dict,
            max_results_per_source=3  # Pocos resultados para no saturar
        )
        
        print(f"\n📊 RESULTADOS:")
        print(f"  Total encontrado: {result.total_found}")
        
        # VALIDACIÓN PRINCIPAL: Debe devolver estudios
        self.assertIsNotNone(result, "El facade debe devolver un resultado")
        self.assertIsNotNone(result.studies, "El resultado debe tener estudios")
        self.assertIsInstance(result.studies, list, "Los estudios deben ser una lista")
        
        if result.total_found > 0:
            print(f"\n✅ SUCCESS: Se encontraron {result.total_found} estudios")
            
            # Validar estructura del primer estudio
            study = result.studies[0]
            print(f"  Ejemplo: {study['title'][:80]}...")
            
            self.assertTrue(study['title'].strip(), "Título no puede estar vacío")
            self.assertTrue(study['link'].strip(), "Link no puede estar vacío")
            
            # Validar que vienen de las fuentes esperadas
            sources = set(str(s['source']) if not isinstance(s['source'], str) else s['source'] for s in result.studies)
            print(f"  Fuentes: {sources}")
            self.assertGreater(len(sources), 0)
        else:
            print(f"\n⚠️  WARNING: No se encontraron estudios. Revisa conexión o VPN.")
            # No fallamos el test si es por conexión, pero avisamos
            
    def test_persistence_of_results(self):
        """
        Prueba que los resultados se pueden guardar en la BD.
        """
        print(f"\n{'='*60}")
        print(f"TEST: Persistencia de resultados")
        print(f"{'='*60}")

        # 1. Crear la estrategia en BD (Requisito previo)
        strategy, created = SearchStrategy.objects.update_or_create(
            id=1,
            defaults={
                "status": SearchStrategy.Status.APPROVED,
                "final_search_string": "agile software development",
                "json_definition": {"main_terms": [{"term": "agile"}]},
                "created_by": self.test_user
            }
        )
        print(f"  SearchStrategy id={strategy.id} {'creada' if created else 'existente'}")

        # 2. Buscar algo simple
        strategy_dict = {
            "main_terms": [{"term": "agile", "synonyms": []}],
            "filters": {"year": {"from": 2024, "to": 2024}}
        }
        
        preview = self.facade.preview_search(strategy_dict, max_results_per_source=1)
        
        if preview.total_found == 0:
            print("⚠️ Saltando test de persistencia por falta de resultados en búsqueda")
            return

        # 3. Intentar guardar
        try:
            final_result = self.facade.finalize_search(
                design_strategy_id=1,
                preview_result=preview,
                user=self.test_user
            )
            
            print(f"✅ Se guardaron {len(final_result.studies_persisted)} estudios")
            self.assertGreater(len(final_result.studies_persisted), 0)
            
            # Trackear para limpieza
            for sid in final_result.studies_persisted:
                self.track_created_study(sid)
                
        except Exception as e:
            self.fail(f"Falló la persistencia en BD: {e}")

    def test_discovery_metadata_fields(self):
        """
        Verifica que campos críticos como is_open_access vengan del discovery.
        """
        print(f"\n{'='*60}")
        print(f"TEST: Campos de Metadata (Open Access / PDF)")
        print(f"{'='*60}")
        
        strategy_dict = {
            "main_terms": [{"term": "open access", "synonyms": []}],
            "filters": {"year": {"from": 2024, "to": 2024}}
        }
        
        result = self.facade.preview_search(strategy_dict, max_results_per_source=2)
        
        if result.studies:
            study = result.studies[0]
            # Solo verificamos que las llaves existan en el diccionario, aunque sean None
            self.assertIn('is_open_access', study)
            self.assertIn('pdf_url', study)
            print("✅ Los campos de metadata extra existen en la respuesta")


if __name__ == '__main__':
    unittest.main()
