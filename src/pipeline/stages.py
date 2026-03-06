import pandas as pd
import numpy as np
from itertools import product, combinations
from typing import Dict, List, Tuple
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class HyperparameterStages:
    """Manages different stages of hyperparameter exploration."""
    
    def __init__(self, base_params: Dict, hyperparam_grid: Dict):
        self.base_params = base_params
        self.hyperparam_grid = hyperparam_grid
        
    def generate_stage1_configs(self) -> List[Dict]:
        """Stage 1: Single hyperparameter variations."""
        configs = []
        
        for param, values in self.hyperparam_grid.items():
            for value in values:
                config = self.base_params.copy()
                config[param] = value
                configs.append(config)
                
        logger.info(f"Generated {len(configs)} Stage 1 configurations")
        return configs
    
    def generate_stage2_configs(self, pairs: List[Tuple[str, str]]) -> List[Dict]:
        """Stage 2: Two-hyperparameter combinations."""
        configs = []
        
        for param1, param2 in pairs:
            vals1 = self.hyperparam_grid[param1]
            vals2 = self.hyperparam_grid[param2]
            
            for v1, v2 in product(vals1, vals2):
                config = self.base_params.copy()
                config[param1] = v1
                config[param2] = v2
                configs.append(config)
                
        logger.info(f"Generated {len(configs)} Stage 2 configurations")
        return configs
    
    def generate_stage3_configs(self, triples: List[Tuple[str, str, str]]) -> List[Dict]:
        """Stage 3: Three-hyperparameter combinations."""
        configs = []
        
        for param1, param2, param3 in triples:
            vals1 = self.hyperparam_grid[param1]
            vals2 = self.hyperparam_grid[param2]
            vals3 = self.hyperparam_grid[param3]
            
            for v1, v2, v3 in product(vals1, vals2, vals3):
                config = self.base_params.copy()
                config[param1] = v1
                config[param2] = v2
                config[param3] = v3
                configs.append(config)
                
        logger.info(f"Generated {len(configs)} Stage 3 configurations")
        return configs
    
    def generate_stage4_configs(
        self,
        metrics_df: pd.DataFrame,
        dataset_name: str,
        reference_topn: int = 50,
        top_n_configs: int = 5
    ) -> List[Dict]:
        """Stage 4: Refined configurations from best performing ones."""
        
        # Filter results for this dataset
        stage123_df = metrics_df[
            (metrics_df['dataset'] == dataset_name) &
            (metrics_df['stage'].isin(['stage1', 'stage2', 'stage3'])) &
            (metrics_df['TopN'] == reference_topn)
        ]
        
        if stage123_df.empty:
            logger.warning(f"No valid Stage 1-3 results for {dataset_name}")
            return []
        
        # Get top configurations
        top_configs = (
            stage123_df
            .sort_values('Precision', ascending=False)
            .head(top_n_configs)
        )
        
        # Extract mode values for each parameter
        refined_config = self.base_params.copy()
        for param in self.hyperparam_grid.keys():
            if param in top_configs.columns:
                refined_config[param] = top_configs[param].mode()[0]
        
        logger.info(f"Stage 4 refined configuration: {refined_config}")
        return [refined_config]