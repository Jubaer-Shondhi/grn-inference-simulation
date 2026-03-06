import pandas as pd
import os
from pathlib import Path
from typing import Tuple, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class DataLoader:
    """Loads gene expression data and ground truth networks."""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        
    def load_dataset(self, complexity: str, trial_index: int) -> Optional[Tuple[pd.DataFrame, pd.DataFrame]]:
        """Load gene expression data and ground truth for a specific trial."""
        
        data_trial = f"{complexity}_trial_{trial_index}"
        
        # Construct paths
        gex_path = self.base_path / complexity / 'data' / f'data_{trial_index}.tsv'
        gt_path = self.base_path / complexity / 'nets' / f'network_{trial_index}.tsv'
        
        if not gex_path.exists() or not gt_path.exists():
            logger.warning(f"Files not found for {data_trial}")
            return None
            
        try:
            # Load data
            gex_data = pd.read_csv(gex_path, sep='\t', index_col=0)
            ground_truth = pd.read_csv(gt_path, sep='\t')
            
            logger.info(f"Loaded {data_trial}")
            return gex_data, ground_truth, data_trial
            
        except Exception as e:
            logger.error(f"Error loading {data_trial}: {e}")
            return None
    
    def load_all_datasets(self, config: Dict) -> Dict:
        """Load all datasets based on configuration."""
        datasets = {}
        
        for complexity, num_trials in config.items():
            datasets[complexity] = []
            
            for trial_index in range(1, 51):  # Up to MAX_SEARCH
                if len(datasets[complexity]) >= num_trials:
                    break
                    
                result = self.load_dataset(complexity, trial_index)
                if result:
                    datasets[complexity].append(result)
                    
        return datasets