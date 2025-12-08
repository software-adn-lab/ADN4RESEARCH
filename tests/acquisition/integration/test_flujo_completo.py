"""
Test de flujo completo: Agregar estudio manual → Enriquecer → Descargar PDF

Escenario real:
1. Agregar estudio manual con DOI
2. Enriquecer metadatos desde fuentes externas
3. Intentar descargar PDF (Open Access o Sci-Hub)
4. Verificar que quedó guardado en MinIO/PostgreSQL

Paper de prueba:
- Título: Teaching the Scrum Master Role using Professional Agile Coaches
- DOI: 10.1109/ICSE-SEET52601.2021.00012
- URL: https://sci-hub.ru/10.1109/ICSE-SEET52601.2021.00012
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.acquisition.facade import AcquisitionFacade
from apps.acquisition.models import StudyModel

def test_flujo_completo():
    print("=" * 80)
    print("TEST: FLUJO COMPLETO - Agregar Estudio → Enriquecer → Descargar PDF")
    print("=" * 80)
    
    # Inicializar facade (composition root)
    facade = AcquisitionFacade()
    
    # PASO 1: Agregar estudio manual
    print("\n📝 PASO 1: Agregando estudio manual con DOI...")
    study_data = {
        "title": "Teaching the Scrum Master Role using Professional Agile Coaches and Communities of Practice",
        "doi": "10.1109/ICSE-SEET52601.2021.00012",
        "link": "https://sci-hub.ru/10.1109/ICSE-SEET52601.2021.00012",
        "authors": ["Autor Desconocido"],  # Se enriquecerá después
        "year": 2021,
        "abstract": "Paper sobre enseñanza de Scrum Master (a enriquecer)",
        "keywords": ["scrum", "agile", "teaching"],
        "journal": "IEEE Conference (a enriquecer)"
    }
    
    try:
        result = facade.register_manual_study(study_data=study_data)
        study_id = result['id']
        print(f"✅ Estudio creado con ID: {study_id}")
        print(f"   Título: {result['title']}")
        print(f"   DOI: {result.get('doi', 'N/A')}")
    except Exception as e:
        print(f"❌ Error creando estudio: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # PASO 2: Verificar en PostgreSQL
    print("\n🔍 PASO 2: Verificando en PostgreSQL...")
    try:
        db_study = StudyModel.objects.get(uuid=study_id)
        print("✅ Estudio encontrado en PostgreSQL")
        print(f"   UUID: {db_study.uuid}")
        print(f"   Title: {db_study.title}")
        print(f"   DOI: {db_study.doi}")
        print(f"   Source: {db_study.source}")
        print(f"   Download Status: {db_study.download_status}")
    except StudyModel.DoesNotExist:
        print("❌ Estudio NO encontrado en PostgreSQL")
        return
    
    # PASO 3: Enriquecer metadatos
    print("\n📊 PASO 3: Enriqueciendo metadatos desde fuentes externas...")
    print("   (Crossref, Scopus, IEEE...)")
    try:
        enrichment_result = facade.enrich_studies(study_ids=[study_id])
        print("✅ Enriquecimiento completado")
        print(f"   Estudios enriquecidos: {enrichment_result.enriched_count}")
        print(f"   Estudios fallidos: {enrichment_result.failed_count}")
    except Exception as e:
        print(f"⚠️  Enriquecimiento falló: {e}")
        print("   (Continuando con descarga de PDF...)")
    
    # PASO 4: Verificar enriquecimiento en DB
    print("\n🔍 PASO 4: Verificando cambios post-enriquecimiento...")
    try:
        db_study.refresh_from_db()
        print(f"   Autores actualizados: {db_study.authors}")
        print(f"   Abstract: {db_study.abstract[:100]}...")
        print(f"   Journal: {db_study.journal}")
    except Exception as e:
        print(f"⚠️  Error verificando: {e}")
    
    # PASO 5: Intentar descargar PDF
    print("\n📥 PASO 5: Intentando descargar PDF...")
    print("   Verificando Open Access...")
    print("   Si no está en OA, intentará Sci-Hub...")
    try:
        download_result = facade.download_fulltexts(study_ids=[study_id])
        print("✅ Descarga completada")
        print(f"   Total: {download_result.total_count}")
        print(f"   Descargados: {download_result.downloaded_count}")
        print(f"   Fallidos: {download_result.failed_count}")
        print(f"   Estado por estudio: {download_result.study_statuses}")
    except Exception as e:
        print(f"❌ Error descargando PDF: {e}")
        import traceback
        traceback.print_exc()
    
    # PASO 6: Verificar PDF en storage
    print("\n📂 PASO 6: Verificando PDF en storage...")
    try:
        db_study.refresh_from_db()
        if db_study.pdf_path:
            print(f"✅ PDF registrado en DB: {db_study.pdf_path}")
            print(f"   Download Status: {db_study.download_status}")
            print(f"   PDF Source: {db_study.pdf_source}")
            
            # Verificar si está en MinIO o en disco
            import os
            if os.path.exists(db_study.pdf_path):
                size = os.path.getsize(db_study.pdf_path)
                print(f"   Archivo en disco local: {size} bytes")
            else:
                print("   Archivo NO está en disco local (debe estar en MinIO)")
                print("   Verifica MinIO Console: http://localhost:9001")
        else:
            print("⚠️  No hay pdf_path en la base de datos")
    except Exception as e:
        print(f"❌ Error verificando storage: {e}")
    
    # RESUMEN FINAL
    print("\n" + "=" * 80)
    print("RESUMEN DEL FLUJO")
    print("=" * 80)
    print(f"✅ Estudio creado: {study_id}")
    print(f"✅ DOI: {db_study.doi}")
    print(f"✅ Título: {db_study.title}")
    
    if db_study.pdf_path:
        print(f"✅ PDF descargado: {db_study.pdf_path}")
        print(f"✅ Fuente del PDF: {db_study.pdf_source}")
    else:
        print("⚠️  PDF no descargado (puede estar bloqueado o sin OA)")
    
    print("\n💡 VERIFICACIÓN MANUAL:")
    print(f"   1. PostgreSQL:")
    print(f"      docker exec -it adn4research_postgres psql -U postgres -d adn4research -c \"SELECT uuid, title, doi, pdf_path, download_status, pdf_source FROM acquisition_study WHERE uuid='{study_id}';\"")
    print(f"\n   2. MinIO Console: http://localhost:9001")
    print(f"      Buscar: {study_id}/")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_flujo_completo()
