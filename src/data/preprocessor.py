import pandas as pd
import numpy as np
import scanpy as sc
from typing import Literal
import warnings
from anndata import ImplicitModificationWarning

warnings.filterwarnings('ignore', category=ImplicitModificationWarning)

class DataPreprocessor:
    """Handles preprocessing of gene expression data for different model types."""
    
    def __init__(self, eps: float = 1e-6):
        self.eps = eps
        
    def preprocess_scaled(self, gex_data: pd.DataFrame) -> pd.DataFrame:
        """Scale data using scanpy's scaling."""
        if 'gene' in gex_data.columns:
            gex_data = gex_data.set_index('gene')
        
        gex_data = gex_data.T
        ad = sc.AnnData(
            gex_data.values,
            var=pd.DataFrame(index=gex_data.columns),
            obs=pd.DataFrame(index=gex_data.index)
        )
        sc.pp.scale(ad)
        
        return pd.DataFrame(ad.X, index=gex_data.index, columns=gex_data.columns)
    
    def preprocess_unscaled(self, gex_data: pd.DataFrame, is_integer: bool = False) -> pd.DataFrame:
        """Preprocess without scaling, with optional integer conversion."""
        if 'gene' in gex_data.columns:
            gex_data = gex_data.set_index('gene')
        
        new_d = gex_data.T.copy()
        
        if is_integer:
            new_d = np.floor(new_d.values)
            new_d = np.clip(new_d, 0, 1000).astype(int)
        else:
            new_d = new_d.astype(float)
            new_d = np.clip(new_d, 0, None)
            new_d[new_d == 0] = self.eps
            
        return pd.DataFrame(new_d, index=gex_data.T.index, columns=gex_data.T.columns)
    
    def dispatch_preprocessing(
        self,
        gex_data: pd.DataFrame,
        model_type: Literal['regressor', 'distribution'],
        objective_type: str = None
    ) -> pd.DataFrame:
        """Dispatch to appropriate preprocessing based on model and objective."""
        
        scaled_objectives = ['reg:squarederror', 'reg:absoluteerror', 'reg:pseudohubererror']
        
        if model_type == 'regressor':
            if objective_type in scaled_objectives:
                return self.preprocess_scaled(gex_data)
            elif objective_type == 'count:poisson':
                return self.preprocess_unscaled(gex_data, is_integer=True)
            elif objective_type in ['reg:gamma', 'reg:tweedie']:
                return self.preprocess_unscaled(gex_data)
            else:
                return self.preprocess_scaled(gex_data)
                
        elif model_type == 'distribution':
            if objective_type in ['poisson', 'negative-binomial']:
                return self.preprocess_unscaled(gex_data, is_integer=True)
            elif objective_type in ['exponential', 'gamma']:
                return self.preprocess_unscaled(gex_data)
            elif objective_type == 'log-normal':
                # Return as-is for log-normal (will be filtered later)
                return gex_data.T.astype(float)
            else:
                return self.preprocess_scaled(gex_data)
        else:
            raise ValueError(f"model_type must be 'regressor' or 'distribution', got {model_type}")