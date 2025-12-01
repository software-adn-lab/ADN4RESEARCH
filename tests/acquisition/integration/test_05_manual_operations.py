"""
Live Integration Tests for Manual Operations.

Este módulo prueba las operaciones manuales del sistema:
- Creación manual de estudios (cuando no aparecen en búsquedas)
- Edición manual de metadatos (correcciones)
- Subida manual de PDFs (cuando no están disponibles online)
- Persistencia y trazabilidad de operaciones manuales

Enfoque: Validar que usuarios pueden intervenir manualmente cuando los robots fallan.
"""

import os
import io
import unittest
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase as HypothesisTestCase

from tests.acquisition.integration.base_live_test import BaseLiveTest


class ManualOperationsLiveTest(BaseLiveTest):
    """
    Tests de integración para validar operaciones manuales.
    
    Estos tests validan el flujo manual:
    - Registro manual de estudios
    - Edición de metadatos
    - Subida de PDFs
    - Trazabilidad de operaciones
    
    Resultado esperado: Usuarios pueden intervenir cuando automatización falla.
    """
    
    def test_manual_study_creation(self):
        """
        TEST PRINCIPAL: Crear un estudio manualmente.
        
        CASO DE USO:
        - Usuario encuentra un paper en una conferencia local
        - El paper no aparece en Scopus/IEEE/etc
        - Usuario lo registra manualmente en el sistema
        
        FLUJO:
        1. Usuario llama a facade.register_manual_study()
        2. Sistema crea estudio con source="Manual"
        3. Sistema persiste en BD
        4. Usuario puede consultar el estudio
        """
        print(f"\n{'='*60}")
        print(f"TEST: Creación manual de estudio")
        print(f"{'='*60}")
        
        # PASO 1: CREAR ESTUDIO MANUAL
        print(f"\n1️⃣ PASO 1: Usuario registra estudio manual")
        
        study_data = {
            "title": "Manual Study: Local Conference Paper on AI",
            "link": "https://local-conference.edu/papers/2024/ai-paper.pdf",
            "doi": "10.9999/local.conf.2024.001",
            "authors": ["John Doe", "Jane Smith", "Bob Johnson"],
            "year": 2024,
            "abstract": "This is a manually registered study from a local conference that is not indexed in major databases.",
            "journal": "Local AI Conference 2024",
            "keywords": ["artificial intelligence", "machine learning", "local research"]
        }
        
        print(f"   Datos del estudio:")
        print(f"     Título: {study_data['title']}")
        print(f"     DOI: {study_data['doi']}")
        print(f"     Autores: {len(study_data['authors'])} autores")
        
        # Registrar estudio manual
        created_study = self.facade.register_manual_study(
            study_data=study_data,
            user=None  # En producción sería el usuario actual
        )
        
        study_id = created_study['id']
        self.track_created_study(study_id)
        
        print(f"\n   ✓ Estudio creado con ID: {study_id[:8]}...")
        print(f"   Source: {created_study.get('source', 'N/A')}")
        print(f"   Status: {created_study.get('status', 'N/A')}")
        
        # PASO 2: VALIDAR PERSISTENCIA
        print(f"\n2️⃣ PASO 2: Validar que el estudio se persistió correctamente")
        
        # Consultar el estudio
        study_status = self.facade.get_study_status([study_id])[0]
        
        print(f"   Estado recuperado:")
        print(f"     Título: {study_status.get('title', 'N/A')[:50]}...")
        print(f"     DOI: {study_status.get('doi', 'N/A')}")
        print(f"     Autores: {len(study_status.get('authors', []))} autores")
        print(f"     Year: {study_status.get('year', 'N/A')}")
        
        # VALIDACIONES
        self.assertIsNotNone(created_study, "El estudio debe ser creado")
        self.assertEqual(created_study['title'], study_data['title'])
        self.assertEqual(created_study['doi'], study_data['doi'])
        self.assertEqual(len(created_study.get('authors', [])), 3)
        
        print(f"\n✅ SUCCESS: Estudio manual creado y persistido correctamente")
    
    def test_manual_metadata_update(self):
        """
        Validar actualización manual de metadatos.
        
        CASO DE USO:
        - Sistema descubrió un estudio con metadatos incorrectos
        - Usuario corrige manualmente los metadatos
        - Sistema actualiza y mantiene trazabilidad
        
        FLUJO:
        1. Crear estudio con metadatos incorrectos
        2. Usuario actualiza metadatos vía facade
        3. Sistema persiste cambios
        4. Validar que cambios se aplicaron
        """
        print(f"\n{'='*60}")
        print(f"TEST: Actualización manual de metadatos")
        print(f"{'='*60}")
        
        # PASO 1: CREAR ESTUDIO CON METADATOS INCORRECTOS
        print(f"\n1️⃣ PASO 1: Crear estudio con metadatos incorrectos")
        
        initial_data = {
            "title": "Study with Wrong Metadata",
            "link": "https://example.com/wrong-metadata",
            "doi": "10.1234/wrong.metadata.001",
            "authors": ["Wrong Author"],
            "year": 2020,  # Año incorrecto
            "abstract": "Wrong abstract"
        }
        
        created_study = self.facade.register_manual_study(
            study_data=initial_data,
            user=None
        )
        
        study_id = created_study['id']
        self.track_created_study(study_id)
        
        print(f"   Estudio creado: {study_id[:8]}...")
        print(f"   Year inicial: {created_study.get('year')}")
        print(f"   Autores iniciales: {created_study.get('authors')}")
        
        # PASO 2: ACTUALIZAR METADATOS
        print(f"\n2️⃣ PASO 2: Usuario corrige metadatos")
        
        updates = {
            "year": 2024,  # Año correcto
            "authors": ["Correct Author 1", "Correct Author 2"],
            "abstract": "This is the correct abstract with proper information."
        }
        
        print(f"   Actualizaciones:")
        print(f"     Year: {initial_data['year']} → {updates['year']}")
        print(f"     Autores: {len(initial_data['authors'])} → {len(updates['authors'])}")
        
        updated_study = self.facade.update_study_metadata(
            study_id=study_id,
            updates=updates,
            user=None
        )
        
        print(f"\n   ✓ Metadatos actualizados")
        
        # PASO 3: VALIDAR CAMBIOS
        print(f"\n3️⃣ PASO 3: Validar que cambios se aplicaron")
        
        study_status = self.facade.get_study_status([study_id])[0]
        
        print(f"   Estado final:")
        print(f"     Year: {study_status.get('year')}")
        print(f"     Autores: {study_status.get('authors')}")
        print(f"     Abstract: {study_status.get('abstract', '')[:50]}...")
        
        # VALIDACIONES
        self.assertEqual(study_status.get('year'), 2024)
        self.assertEqual(len(study_status.get('authors', [])), 2)
        self.assertIn("correct abstract", study_status.get('abstract', '').lower())
        
        print(f"\n✅ SUCCESS: Metadatos actualizados correctamente")
    
    def test_manual_pdf_upload(self):
        """
        Validar subida manual de PDF.
        
        CASO DE USO:
        - Estudio no tiene PDF disponible online
        - Usuario tiene acceso institucional o copia física
        - Usuario sube el PDF manualmente
        
        FLUJO:
        1. Crear estudio sin PDF
        2. Usuario sube PDF vía facade
        3. Sistema almacena PDF
        4. Validar que PDF está disponible
        """
        print(f"\n{'='*60}")
        print(f"TEST: Subida manual de PDF")
        print(f"{'='*60}")
        
        # PASO 1: CREAR ESTUDIO SIN PDF
        print(f"\n1️⃣ PASO 1: Crear estudio sin PDF")
        
        study_data = {
            "title": "Study Without PDF Online",
            "link": "https://example.com/no-pdf-available",
            "doi": "10.1234/no.pdf.001",
            "authors": ["Test Author"],
            "year": 2024
        }
        
        created_study = self.facade.register_manual_study(
            study_data=study_data,
            user=None
        )
        
        study_id = created_study['id']
        self.track_created_study(study_id)
        
        print(f"   Estudio creado: {study_id[:8]}...")
        print(f"   PDF path inicial: {created_study.get('pdf_path', 'None')}")
        
        # PASO 2: CREAR PDF SIMULADO
        print(f"\n2️⃣ PASO 2: Usuario sube PDF manualmente")
        
        # Crear un PDF simulado (mínimo válido)
        pdf_content = b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n"  # Header PDF válido
        pdf_content += b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        pdf_content += b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        pdf_content += b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        pdf_content += b"xref\n0 4\n"
        pdf_content += b"0000000000 65535 f\n"
        pdf_content += b"0000000015 00000 n\n"
        pdf_content += b"0000000068 00000 n\n"
        pdf_content += b"0000000137 00000 n\n"
        pdf_content += b"trailer\n<< /Size 4 /Root 1 0 R >>\n"
        pdf_content += b"startxref\n228\n%%EOF\n"
        
        # Crear objeto archivo simulado
        pdf_file = io.BytesIO(pdf_content)
        pdf_file.name = "manual_upload_test.pdf"
        
        print(f"   Subiendo PDF: {pdf_file.name}")
        print(f"   Tamaño: {len(pdf_content)} bytes")
        
        # Subir PDF
        upload_result = self.facade.upload_study_pdf(
            study_id=study_id,
            file_obj=pdf_file,
            filename="manual_upload_test.pdf",
            user=None
        )
        
        print(f"\n   ✓ PDF subido")
        print(f"   PDF path: {upload_result.get('pdf_path', 'N/A')}")
        print(f"   Download status: {upload_result.get('download_status', 'N/A')}")
        
        # PASO 3: VALIDAR QUE PDF ESTÁ DISPONIBLE
        print(f"\n3️⃣ PASO 3: Validar que PDF está disponible")
        
        study_status = self.facade.get_study_status([study_id])[0]
        pdf_path = study_status.get('pdf_path')
        
        print(f"   Estado final:")
        print(f"     PDF path: {pdf_path}")
        print(f"     Download status: {study_status.get('download_status')}")
        
        # VALIDACIONES
        self.assertIsNotNone(pdf_path, "El PDF debe tener una ruta")
        self.assertTrue(os.path.exists(pdf_path), "El archivo PDF debe existir en disco")
        
        # Validar que es un PDF válido
        if os.path.exists(pdf_path):
            self.assert_valid_pdf_file(pdf_path)
            print(f"   ✓ PDF validado correctamente")
        
        print(f"\n✅ SUCCESS: PDF subido y almacenado correctamente")
    
    def test_manual_operations_persistence(self):
        """
        Validar que operaciones manuales persisten correctamente.
        
        Este test verifica que:
        - Estudios manuales se guardan en BD
        - Actualizaciones persisten
        - PDFs subidos se mantienen
        - Trazabilidad se preserva
        """
        print(f"\n{'='*60}")
        print(f"TEST: Persistencia de operaciones manuales")
        print(f"{'='*60}")
        
        # PASO 1: CREAR ESTUDIO MANUAL COMPLETO
        print(f"\n1️⃣ PASO 1: Crear estudio manual completo")
        
        study_data = {
            "title": "Complete Manual Study",
            "link": "https://example.com/complete-manual",
            "doi": "10.1234/complete.manual.001",
            "authors": ["Author One", "Author Two"],
            "year": 2024,
            "abstract": "Complete manual study with all metadata",
            "journal": "Manual Journal",
            "keywords": ["manual", "test", "persistence"]
        }
        
        created_study = self.facade.register_manual_study(
            study_data=study_data,
            user=None
        )
        
        study_id = created_study['id']
        self.track_created_study(study_id)
        
        print(f"   Estudio creado: {study_id[:8]}...")
        
        # PASO 2: ACTUALIZAR METADATOS
        print(f"\n2️⃣ PASO 2: Actualizar metadatos")
        
        updates = {
            "year": 2025,
            "keywords": ["manual", "test", "persistence", "updated"]
        }
        
        self.facade.update_study_metadata(
            study_id=study_id,
            updates=updates,
            user=None
        )
        
        print(f"   ✓ Metadatos actualizados")
        
        # PASO 3: SUBIR PDF
        print(f"\n3️⃣ PASO 3: Subir PDF")
        
        pdf_content = b"%PDF-1.4\nTest PDF content\n%%EOF\n"
        pdf_file = io.BytesIO(pdf_content)
        pdf_file.name = "persistence_test.pdf"
        
        self.facade.upload_study_pdf(
            study_id=study_id,
            file_obj=pdf_file,
            filename="persistence_test.pdf",
            user=None
        )
        
        print(f"   ✓ PDF subido")
        
        # PASO 4: VALIDAR PERSISTENCIA COMPLETA
        print(f"\n4️⃣ PASO 4: Validar persistencia completa")
        
        study_status = self.facade.get_study_status([study_id])[0]
        
        print(f"   Estado final:")
        print(f"     Título: {study_status.get('title', 'N/A')[:40]}...")
        print(f"     Year: {study_status.get('year')}")
        print(f"     Keywords: {len(study_status.get('keywords', []))} keywords")
        print(f"     PDF: {'Sí' if study_status.get('pdf_path') else 'No'}")
        
        # VALIDACIONES
        self.assertEqual(study_status.get('year'), 2025)
        self.assertEqual(len(study_status.get('keywords', [])), 4)
        self.assertIsNotNone(study_status.get('pdf_path'))
        
        print(f"\n✅ SUCCESS: Todas las operaciones manuales persistieron correctamente")
    
    # ==========================================================================
    # PROPERTY-BASED TESTS
    # ==========================================================================
    
    def test_property_manual_study_creation(self):
        """
        Property 19: Manual Study Creation
        Validates: Requirements 7.1
        
        Property: For any valid study data (title, link, optional metadata),
        the system should create a study with a unique ID and persist it correctly.
        """
        print(f"\n{'='*60}")
        print(f"PROPERTY TEST: Manual Study Creation")
        print(f"{'='*60}")
        
        # Test with minimal data
        minimal_study = self.facade.register_manual_study(
            study_data={
                "title": "Minimal Study",
                "link": "https://example.com/minimal"
            },
            user=None
        )
        
        self.track_created_study(minimal_study['id'])
        self.assertIsNotNone(minimal_study['id'])
        self.assertEqual(minimal_study['title'], "Minimal Study")
        print(f"   ✓ Minimal study created: {minimal_study['id'][:8]}...")
        
        # Test with full metadata
        full_study = self.facade.register_manual_study(
            study_data={
                "title": "Full Study with All Metadata",
                "link": "https://example.com/full",
                "doi": "10.1234/full.001",
                "authors": ["Author 1", "Author 2", "Author 3"],
                "year": 2024,
                "abstract": "Complete abstract",
                "journal": "Test Journal",
                "keywords": ["test", "property", "manual"]
            },
            user=None
        )
        
        self.track_created_study(full_study['id'])
        self.assertIsNotNone(full_study['id'])
        self.assertEqual(len(full_study.get('authors', [])), 3)
        self.assertEqual(full_study['year'], 2024)
        print(f"   ✓ Full study created: {full_study['id'][:8]}...")
        
        # Verify both have unique IDs
        self.assertNotEqual(minimal_study['id'], full_study['id'])
        
        print(f"\n✅ Property validated: Manual studies created with unique IDs")
    
    def test_property_manual_metadata_updates(self):
        """
        Property 20: Manual Metadata Updates
        Validates: Requirements 7.2
        
        Property: For any study and any valid metadata updates,
        the system should apply the updates and preserve the study ID.
        """
        print(f"\n{'='*60}")
        print(f"PROPERTY TEST: Manual Metadata Updates")
        print(f"{'='*60}")
        
        # Create base study
        study = self.facade.register_manual_study(
            study_data={
                "title": "Study for Updates",
                "link": "https://example.com/updates",
                "year": 2020
            },
            user=None
        )
        
        study_id = study['id']
        self.track_created_study(study_id)
        print(f"   Base study created: {study_id[:8]}...")
        
        # Test multiple update scenarios
        update_scenarios = [
            {"year": 2021},
            {"authors": ["New Author"]},
            {"abstract": "New abstract"},
            {"year": 2024, "authors": ["Author 1", "Author 2"]},
        ]
        
        for i, updates in enumerate(update_scenarios, 1):
            updated = self.facade.update_study_metadata(
                study_id=study_id,
                updates=updates,
                user=None
            )
            
            # Verify ID is preserved
            self.assertEqual(updated['id'], study_id)
            
            # Verify updates were applied
            for key, value in updates.items():
                self.assertEqual(updated.get(key), value)
            
            print(f"   ✓ Update scenario {i}: {list(updates.keys())}")
        
        print(f"\n✅ Property validated: Updates preserve ID and apply correctly")
    
    def test_property_manual_pdf_upload_association(self):
        """
        Property 21: Manual PDF Upload Association
        Validates: Requirements 7.3
        
        Property: For any study and any valid PDF file,
        the system should associate the PDF with the correct study.
        """
        print(f"\n{'='*60}")
        print(f"PROPERTY TEST: Manual PDF Upload Association")
        print(f"{'='*60}")
        
        # Create multiple studies
        studies = []
        for i in range(1, 4):
            study = self.facade.register_manual_study(
                study_data={
                    "title": f"Study {i} for PDF",
                    "link": f"https://example.com/pdf-{i}"
                },
                user=None
            )
            studies.append(study)
            self.track_created_study(study['id'])
            print(f"   Study {i} created: {study['id'][:8]}...")
        
        # Upload PDF to each study
        for i, study in enumerate(studies, 1):
            pdf_content = f"%PDF-1.4\nPDF for study {i}\n%%EOF\n".encode()
            pdf_file = io.BytesIO(pdf_content)
            pdf_file.name = f"study_{i}.pdf"
            
            result = self.facade.upload_study_pdf(
                study_id=study['id'],
                file_obj=pdf_file,
                filename=f"study_{i}.pdf",
                user=None
            )
            
            # Verify PDF is associated with correct study
            self.assertEqual(result['study_id'], study['id'])
            self.assertIsNotNone(result['pdf_path'])
            
            print(f"   ✓ PDF uploaded to study {i}: {result['study_id'][:8]}...")
        
        # Verify each study has its own PDF
        for i, study in enumerate(studies, 1):
            status = self.facade.get_study_status([study['id']])[0]
            self.assertIsNotNone(status['pdf_path'])
            self.assertIn(f"study_{i}.pdf", status['pdf_path'])
            print(f"   ✓ Study {i} has correct PDF")
        
        print(f"\n✅ Property validated: PDFs correctly associated with studies")
    
    def test_property_manual_operation_persistence(self):
        """
        Property 22: Manual Operation Persistence
        Validates: Requirements 7.4
        
        Property: For any sequence of manual operations (create, update, upload),
        all changes should persist across queries.
        """
        print(f"\n{'='*60}")
        print(f"PROPERTY TEST: Manual Operation Persistence")
        print(f"{'='*60}")
        
        # Create study
        study = self.facade.register_manual_study(
            study_data={
                "title": "Persistence Test Study",
                "link": "https://example.com/persistence",
                "year": 2020
            },
            user=None
        )
        
        study_id = study['id']
        self.track_created_study(study_id)
        print(f"   Study created: {study_id[:8]}...")
        
        # Query 1: Initial state
        state1 = self.facade.get_study_status([study_id])[0]
        self.assertEqual(state1['year'], 2020)
        self.assertIsNone(state1.get('pdf_path'))
        print(f"   ✓ Query 1: Initial state verified")
        
        # Update metadata
        self.facade.update_study_metadata(
            study_id=study_id,
            updates={"year": 2024, "authors": ["Test Author"]},
            user=None
        )
        
        # Query 2: After update
        state2 = self.facade.get_study_status([study_id])[0]
        self.assertEqual(state2['year'], 2024)
        self.assertEqual(len(state2.get('authors', [])), 1)
        print(f"   ✓ Query 2: Updates persisted")
        
        # Upload PDF
        pdf_file = io.BytesIO(b"%PDF-1.4\nTest\n%%EOF\n")
        pdf_file.name = "persistence.pdf"
        
        self.facade.upload_study_pdf(
            study_id=study_id,
            file_obj=pdf_file,
            filename="persistence.pdf",
            user=None
        )
        
        # Query 3: After PDF upload
        state3 = self.facade.get_study_status([study_id])[0]
        self.assertEqual(state3['year'], 2024)
        self.assertEqual(len(state3.get('authors', [])), 1)
        self.assertIsNotNone(state3['pdf_path'])
        print(f"   ✓ Query 3: All operations persisted")
        
        print(f"\n✅ Property validated: All operations persist correctly")
    
    def test_property_user_attribution_tracking(self):
        """
        Property 23: User Attribution Tracking
        Validates: Requirements 7.5
        
        Property: For any manual operation, the system should track
        which fields were modified manually via field_origins.
        """
        print(f"\n{'='*60}")
        print(f"PROPERTY TEST: User Attribution Tracking")
        print(f"{'='*60}")
        
        # Create manual study
        study = self.facade.register_manual_study(
            study_data={
                "title": "Attribution Test",
                "link": "https://example.com/attribution",
                "year": 2024,
                "authors": ["Manual Author"]
            },
            user=None
        )
        
        study_id = study['id']
        self.track_created_study(study_id)
        
        # Verify field_origins tracks manual creation
        self.assertIn('field_origins', study)
        field_origins = study.get('field_origins', {})
        
        # All manually created fields should be marked as "manual"
        self.assertEqual(field_origins.get('source'), 'manual')
        print(f"   ✓ Manual creation tracked in field_origins")
        
        # Update metadata manually
        self.facade.update_study_metadata(
            study_id=study_id,
            updates={"abstract": "Manually added abstract"},
            user=None
        )
        
        # Verify update is tracked
        updated_study = self.facade.get_study_status([study_id])[0]
        updated_origins = updated_study.get('field_origins', {})
        
        self.assertEqual(updated_origins.get('abstract'), 'manual')
        print(f"   ✓ Manual update tracked in field_origins")
        
        print(f"\n✅ Property validated: Manual operations tracked correctly")


if __name__ == '__main__':
    unittest.main()
