"""
Sistema de caché para descargas de papers académicos.

Almacena:
- Metadatos de papers descargados
- Intentos fallidos
- Estadísticas de uso

Base de datos: SQLite
"""
import sqlite3
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class DownloadCache:
    """
    Gestiona caché de descargas para evitar requests duplicados.
    """

    def __init__(self, cache_dir: str = "media/papers"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Base de datos para metadatos
        self.db_path = self.cache_dir / "_cache.db"
        self._init_db()

    def _init_db(self):
        """Inicializa base de datos SQLite"""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()

        # Tabla de papers descargados
        c.execute('''
            CREATE TABLE IF NOT EXISTS papers_cache (
                doi TEXT PRIMARY KEY,
                title TEXT,
                file_path TEXT,
                file_size INTEGER,
                file_md5 TEXT,
                source TEXT,
                downloaded_at TIMESTAMP,
                last_accessed TIMESTAMP
            )
        ''')

        # Tabla de intentos fallidos
        c.execute('''
            CREATE TABLE IF NOT EXISTS failed_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doi TEXT,
                source TEXT,
                error_msg TEXT,
                attempted_at TIMESTAMP,
                retry_count INTEGER DEFAULT 1
            )
        ''')

        # Índices para búsquedas rápidas
        c.execute('CREATE INDEX IF NOT EXISTS idx_doi ON papers_cache(doi)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_failed_doi ON failed_attempts(doi)')

        conn.commit()
        conn.close()

        logger.debug("Cache database initialized")

    def get_cached_paper(self, doi: str) -> Optional[Dict]:
        """
        Obtiene paper del caché si existe.

        Returns:
            Dict con información del paper o None si no está cacheado
        """
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()

        c.execute(
            'SELECT doi, title, file_path, file_size, source, downloaded_at FROM papers_cache WHERE doi = ?',
            (doi,)
        )

        row = c.fetchone()

        if row:
            # Actualizar último acceso
            c.execute(
                'UPDATE papers_cache SET last_accessed = ? WHERE doi = ?',
                (datetime.now(), doi)
            )
            conn.commit()

            result = {
                'doi': row[0],
                'title': row[1],
                'file_path': row[2],
                'size': row[3],
                'source': row[4],
                'downloaded_at': row[5]
            }

            # Verificar que el archivo existe
            if Path(row[2]).exists():
                logger.info(f"[Cache HIT] {doi} from {row[4]}")
                conn.close()
                return result
            else:
                # Archivo no existe, limpiar caché
                logger.warning(f"[Cache MISS] File not found: {row[2]}")
                c.execute('DELETE FROM papers_cache WHERE doi = ?', (doi,))
                conn.commit()

        conn.close()
        return None

    def save_paper(self, doi: str, title: str, file_path: str, source: str):
        """
        Guarda información de paper descargado en caché.
        """
        # Calcular MD5 y tamaño
        filepath_obj = Path(file_path)
        if not filepath_obj.exists():
            logger.error(f"Cannot cache: file not found {file_path}")
            return

        file_size = filepath_obj.stat().st_size
        file_md5 = self._calculate_md5(file_path)

        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()

        c.execute('''
            INSERT OR REPLACE INTO papers_cache
            (doi, title, file_path, file_size, file_md5, source, downloaded_at, last_accessed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (doi, title, file_path, file_size, file_md5, source, datetime.now(), datetime.now()))

        conn.commit()
        conn.close()

        size_mb = file_size / 1024 / 1024
        logger.info(f"[Cache SAVE] {title} ({size_mb:.2f} MB) from {source}")

    def mark_failed(self, doi: str, source: str, error: str):
        """
        Registra intento fallido de descarga.
        """
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()

        # Verificar si ya existe un intento fallido reciente
        c.execute('''
            SELECT retry_count FROM failed_attempts
            WHERE doi = ? AND source = ?
            ORDER BY attempted_at DESC LIMIT 1
        ''', (doi, source))

        row = c.fetchone()
        retry_count = (row[0] + 1) if row else 1

        c.execute('''
            INSERT INTO failed_attempts (doi, source, error_msg, attempted_at, retry_count)
            VALUES (?, ?, ?, ?, ?)
        ''', (doi, source, error[:500], datetime.now(), retry_count))

        conn.commit()
        conn.close()

        logger.debug(f"[Cache FAIL] {doi} from {source} (attempt {retry_count})")

    def should_retry(self, doi: str, source: str, max_retries: int = 3) -> bool:
        """
        Verifica si se debe reintentar descarga de una fuente.

        Returns:
            True si se debe reintentar, False si ya se intentó demasiadas veces
        """
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()

        c.execute('''
            SELECT retry_count FROM failed_attempts
            WHERE doi = ? AND source = ?
            ORDER BY attempted_at DESC LIMIT 1
        ''', (doi, source))

        row = c.fetchone()
        conn.close()

        if not row:
            return True

        return row[0] < max_retries

    def get_stats(self) -> Dict:
        """
        Obtiene estadísticas del caché.
        """
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()

        # Total de papers cacheados
        c.execute('SELECT COUNT(*) FROM papers_cache')
        total_papers = c.fetchone()[0]

        # Tamaño total en bytes
        c.execute('SELECT SUM(file_size) FROM papers_cache')
        total_size = c.fetchone()[0] or 0

        # Total de intentos fallidos únicos
        c.execute('SELECT COUNT(DISTINCT doi) FROM failed_attempts')
        failed_dois = c.fetchone()[0]

        # Papers por fuente
        c.execute('SELECT source, COUNT(*) FROM papers_cache GROUP BY source')
        by_source = dict(c.fetchall())

        conn.close()

        return {
            'cached_papers': total_papers,
            'cache_size_gb': total_size / (1024 ** 3),
            'failed_dois': failed_dois,
            'by_source': by_source
        }

    def _calculate_md5(self, file_path: str) -> str:
        """Calcula MD5 hash de un archivo"""
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()

    def clear_cache(self, older_than_days: Optional[int] = None):
        """
        Limpia el caché.

        Args:
            older_than_days: Si se especifica, solo limpia entries más antiguos
        """
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()

        if older_than_days:
            from datetime import timedelta
            cutoff = datetime.now() - timedelta(days=older_than_days)
            c.execute('DELETE FROM papers_cache WHERE last_accessed < ?', (cutoff,))
            c.execute('DELETE FROM failed_attempts WHERE attempted_at < ?', (cutoff,))
        else:
            c.execute('DELETE FROM papers_cache')
            c.execute('DELETE FROM failed_attempts')

        conn.commit()
        deleted = c.rowcount
        conn.close()

        logger.info(f"Cache cleared: {deleted} entries removed")
