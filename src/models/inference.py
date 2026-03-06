import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from xgboost_distribution import XGBDistribution
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logger = logging.getLogger(__name__)

class GRNInferencer:
    """Infers Gene Regulatory Networks using XGBoost models."""
    
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        
    def infer_for_gene_batch(
        self,
        genes_batch: List[str],
        data: pd.DataFrame,
        predictors: List[str],
        model_type: str,
        model_params: Dict
    ) -> pd.DataFrame:
        """Infer regulatory relationships for a batch of target genes."""
        batch_results = []
        
        for target_gene in genes_batch:
            y = data[target_gene].copy()
            X = data[predictors].drop(columns=[target_gene], errors='ignore')
            
            # Skip invalid targets
            if y.sum() == 0 or y.var() == 0:
                continue
                
            # Special handling for log-normal distribution
            if (model_type == 'distribution' and 
                model_params.get('distribution') == 'log-normal' and 
                (y <= 0).any()):
                continue
                
            # Filter constant predictors
            X = X.loc[:, X.var() > 1e-6]
            if X.empty or np.std(X.values) < 1e-6:
                continue
                
            # Initialize model
            if model_type == 'regressor':
                model = XGBRegressor(**model_params)
            elif model_type == 'distribution':
                model = XGBDistribution(**model_params)
                if model_params.get('distribution') == 'negative-binomial':
                    model.natural_gradient = True
            else:
                raise ValueError(f"model_type must be 'regressor' or 'distribution', got {model_type}")
            
            try:
                model.fit(X, y)
                imp = model.feature_importances_
                
                # Create result DataFrame
                df = pd.DataFrame({
                    'source': X.columns,
                    'target': target_gene,
                    'weight': imp
                })
                
                # Filter zero weights
                df = df[df['weight'] > 0]
                if not df.empty:
                    batch_results.append(df)
                    
            except (np.linalg.LinAlgError, Exception) as e:
                logger.debug(f"Skipping {target_gene}: {e}")
                continue
                
        return pd.concat(batch_results, ignore_index=True) if batch_results else pd.DataFrame()
    
    def compute_network(
        self,
        expression_data: pd.DataFrame,
        tf_names: List[str],
        model_type: str,
        model_params: Dict,
        n_workers: int = None
    ) -> pd.DataFrame:
        """Compute regulatory network for all genes."""
        from src.data.preprocessor import DataPreprocessor
        
        # Get objective/distribution type
        if model_type == 'regressor':
            dist_type = model_params.get('objective')
        else:
            dist_type = model_params.get('distribution', 'normal')
        
        # Preprocess data
        preprocessor = DataPreprocessor()
        data = preprocessor.dispatch_preprocessing(expression_data, model_type, dist_type)
        
        # Filter TFs present in data
        predictors = [tf for tf in tf_names if tf in data.columns]
        all_genes = data.columns.tolist()
        
        # Create batches
        batches = [
            all_genes[i:i + self.batch_size] 
            for i in range(0, len(all_genes), self.batch_size)
        ]
        
        # Parallel execution
        with ThreadPoolExecutor(max_workers=n_workers) as executor:
            futures = [
                executor.submit(
                    self.infer_for_gene_batch,
                    batch, data, predictors, model_type, model_params
                )
                for batch in batches
            ]
            
            results = []
            for future in as_completed(futures):
                res = future.result()
                if not res.empty:
                    results.append(res)
                    
        return pd.concat(results, ignore_index=True) if results else pd.DataFrame()