"""
Script para configurar MinIO y crear el bucket necesario usando boto3.
"""

import os
import sys
import boto3
from botocore.exceptions import ClientError

def setup_minio():
    """Configura MinIO y crea el bucket si no existe."""
    
    # Leer configuración desde .env
    endpoint_url = os.getenv('AWS_S3_ENDPOINT_URL', 'http://localhost:9000')
    access_key = os.getenv('AWS_ACCESS_KEY_ID', 'minioadmin')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY', 'minioadmin')
    bucket_name = os.getenv('AWS_STORAGE_BUCKET_NAME', 'adn4research')
    region = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')
    
    print("="*60)
    print("CONFIGURACIÓN DE MinIO")
    print("="*60)
    print(f"\n📦 Endpoint: {endpoint_url}")
    print(f"🔑 Access Key: {access_key}")
    print(f"🪣 Bucket: {bucket_name}")
    print(f"🌍 Region: {region}")
    
    try:
        # Crear cliente S3 (boto3) para MinIO
        print(f"\n🔌 Conectando a MinIO...")
        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            verify=False  # No verificar SSL
        )
        
        # Verificar si el bucket existe
        print(f"\n🔍 Verificando bucket '{bucket_name}'...")
        
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            print(f"✅ El bucket '{bucket_name}' ya existe")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                print(f"⚠️  El bucket '{bucket_name}' no existe")
                print(f"📦 Creando bucket '{bucket_name}'...")
                
                s3_client.create_bucket(Bucket=bucket_name)
                print(f"✅ Bucket '{bucket_name}' creado exitosamente")
            else:
                raise
        
        # Listar objetos en el bucket
        print(f"\n📂 Contenido del bucket '{bucket_name}':")
        
        try:
            response = s3_client.list_objects_v2(Bucket=bucket_name)
            
            if 'Contents' in response:
                objects = response['Contents']
                print(f"   Archivos encontrados: {len(objects)}")
                
                for idx, obj in enumerate(objects[:10], 1):
                    size_mb = obj['Size'] / (1024 * 1024)
                    print(f"   {idx}. {obj['Key']} ({size_mb:.2f} MB)")
                
                if len(objects) > 10:
                    print(f"   ... y {len(objects) - 10} archivos más")
            else:
                print(f"   (vacío - sin archivos)")
        except ClientError:
            print(f"   (vacío - sin archivos)")
        
        print(f"\n{'='*60}")
        print(f"✅ CONFIGURACIÓN COMPLETADA")
        print(f"{'='*60}")
        print(f"\n💡 Puedes acceder a MinIO en:")
        print(f"   URL: http://localhost:9001")
        print(f"   Usuario: {access_key}")
        print(f"   Contraseña: {secret_key}")
        print(f"\n💡 El bucket '{bucket_name}' está listo para usar")
        
        return True
        
    except ClientError as e:
        print(f"\n❌ Error de S3/MinIO: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Cargar variables de entorno desde .env
    from dotenv import load_dotenv
    load_dotenv()
    
    success = setup_minio()
    sys.exit(0 if success else 1)
