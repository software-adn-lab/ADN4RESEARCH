"""
Script de inicialización de almacenamiento.
Se ejecuta automáticamente al iniciar la aplicación si el bucket no existe.
"""

import os
import sys
import boto3
from botocore.exceptions import ClientError

def init_storage_if_needed():
    """
    Inicializa el almacenamiento solo si es necesario.
    Retorna True si ya estaba configurado, False si se configuró ahora.
    """
    
    endpoint_url = os.getenv('AWS_S3_ENDPOINT_URL', 'http://localhost:9000')
    access_key = os.getenv('AWS_ACCESS_KEY_ID', 'minioadmin')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY', 'minioadmin')
    bucket_name = os.getenv('AWS_STORAGE_BUCKET_NAME', 'adn4research')
    region = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')
    
    try:
        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            verify=False
        )
        
        # Verificar si el bucket existe
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            # Bucket existe, no hacer nada
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Bucket no existe, crearlo
                print(f"📦 Inicializando almacenamiento...")
                print(f"   Creando bucket '{bucket_name}'...")
                
                s3_client.create_bucket(Bucket=bucket_name)
                
                print(f"✅ Bucket '{bucket_name}' creado")
                print(f"💡 Almacenamiento listo en: {endpoint_url}")
                return False
            else:
                # Otro error
                raise
    
    except Exception as e:
        print(f"⚠️  No se pudo inicializar almacenamiento: {e}")
        print(f"   La aplicación funcionará pero sin almacenamiento S3")
        return False

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    was_already_setup = init_storage_if_needed()
    
    if was_already_setup:
        print("✅ Almacenamiento ya configurado")
    else:
        print("✅ Almacenamiento inicializado")
    
    sys.exit(0)
