"""Download related tasks (scaffold)."""

from apps.acquisition.adapters.outbound.download_manager.manager import DownloadManager


def enqueue_download(manager: DownloadManager, job) -> None:
    manager.enqueue(job)
