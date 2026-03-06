import os
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

def get_optimal_workers(n_workers: Optional[int] = None) -> int:
    """Get optimal number of workers for parallel execution."""
    if n_workers == "auto" or n_workers is None:
        return max(1, os.cpu_count())
    elif n_workers <= 0:
        return max(1, os.cpu_count() + n_workers)
    else:
        return n_workers