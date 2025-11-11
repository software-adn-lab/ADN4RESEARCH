"""
Celery tasks for download operations.

In production these would be Celery tasks (@shared_task or @app.task);
for now they are plain functions which can be invoked synchronously in tests.

Future integration:
    from celery import shared_task

    @shared_task
    def download_paper_async(paper_id: str, url: str):
        ...
"""

# TODO: Implement DownloadService in downloads/application/
# TODO: Implement download domain entities and interfaces


def enqueue_download(download_job: dict) -> None:
    """
    Enqueue a download job (scaffold).

    Args:
        download_job: Dictionary with download job details
            Example: {
                "paper_id": "123",
                "url": "https://...",
                "priority": "high",
                "retry_count": 0
            }

    Future implementation:
        This will call DownloadService to handle the actual download logic.

    Example:
        >>> job = {
        ...     "paper_id": "paper-123",
        ...     "url": "https://arxiv.org/pdf/1234.5678.pdf",
        ...     "priority": "normal"
        ... }
        >>> enqueue_download(job)
    """
    # TODO: Implement download service call
    # from apps.acquisition.downloads.application.download_service import DownloadService
    # service = DownloadService()
    # service.enqueue(download_job)
    pass


def process_download(download_job: dict) -> dict:
    """
    Process a download job (scaffold).

    Args:
        download_job: Dictionary with download job details

    Returns:
        Dictionary with download result:
        {
            "status": "success" | "failed",
            "file_path": "/path/to/downloaded/file.pdf",
            "error": Optional[str]
        }

    Future implementation:
        This will call DownloadService to execute the download.

    Example:
        >>> job = {"paper_id": "123", "url": "https://..."}
        >>> result = process_download(job)
        >>> result["status"]
        'success'
    """
    # TODO: Implement download execution
    return {
        "status": "pending",
        "file_path": None,
        "error": "Download service not implemented yet"
    }
