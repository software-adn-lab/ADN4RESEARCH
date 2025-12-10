"""
Test script to verify the Findings Exporter component.
"""

import os
import sys
import django

# Setup Django environment
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.interpretation.exporter.service import FindingsExportService


def test_pdf_export():
    """Test PDF export functionality."""
    service = FindingsExportService()
    
    print("Testing PDF export for project 2...")
    content, mime_type, filename = service.export_findings(
        project_id="2",
        export_format="pdf"
    )
    
    # Save to file
    output_path = "test_export.pdf"
    with open(output_path, "wb") as f:
        f.write(content.getvalue())
    
    print(f"✅ PDF exported successfully to {output_path}")
    print(f"   MIME type: {mime_type}")
    print(f"   Filename: {filename}")


def test_csv_export():
    """Test CSV export functionality."""
    service = FindingsExportService()
    
    print("\nTesting CSV export for project 2...")
    content, mime_type, filename = service.export_findings(
        project_id="2",
        export_format="csv"
    )
    
    # Save to file
    output_path = "test_export.csv"
    with open(output_path, "w") as f:
        f.write(content.getvalue())
    
    print(f"✅ CSV exported successfully to {output_path}")
    print(f"   MIME type: {mime_type}")
    print(f"   Filename: {filename}")


def test_json_export():
    """Test JSON export functionality."""
    service = FindingsExportService()
    
    print("\nTesting JSON export for project 2...")
    content, mime_type, filename = service.export_findings(
        project_id="2",
        export_format="json"
    )
    
    # Save to file
    output_path = "test_export.json"
    with open(output_path, "w") as f:
        f.write(content)
    
    print(f"✅ JSON exported successfully to {output_path}")
    print(f"   MIME type: {mime_type}")
    print(f"   Filename: {filename}")


if __name__ == "__main__":
    try:
        test_pdf_export()
        test_csv_export()
        test_json_export()
        print("\n🎉 All export tests passed!")
    except Exception as e:
        print(f"\n❌ Export test failed: {e}")
        import traceback
        traceback.print_exc()
