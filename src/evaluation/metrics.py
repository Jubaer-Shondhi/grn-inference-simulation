import pandas as pd
from typing import Dict, List, Set, Tuple
import logging

logger = logging.getLogger(__name__)

class MetricsCalculator:
    """Calculates evaluation metrics for GRN inference."""
    
    def __init__(self, thresholds: List[int] = None):
        self.thresholds = thresholds or [5, 10, 15, 20, 50, 75, 100, 125, 300, 500]
    
    @staticmethod
    def create_groundtruth_set(groundtruth_df: pd.DataFrame) -> Set[Tuple[str, str]]:
        """Create set of undirected regulatory relationships."""
        return {
            tuple(sorted((row.source, row.target)))
            for row in groundtruth_df.itertuples()
        }
    
    def compute_precision_at_k(
        self,
        ranked_predictions: pd.DataFrame,
        groundtruth_set: Set[Tuple[str, str]],
        k_values: List[int] = None
    ) -> pd.DataFrame:
        """Compute precision@K for multiple thresholds."""
        if k_values is None:
            k_values = self.thresholds
            
        results = []
        
        for k in k_values:
            top_k = ranked_predictions.head(k)
            
            # Count true positives
            tp = sum(
                tuple(sorted((row.source, row.target))) in groundtruth_set
                for row in top_k.itertuples()
            )
            
            precision = tp / k if k > 0 else 0.0
            results.append({'TopN': k, 'Precision': precision})
            
        return pd.DataFrame(results)
    
    def compute_all_metrics(
        self,
        predicted_network: pd.DataFrame,
        groundtruth: pd.DataFrame,
        dataset_name: str,
        objective_name: str,
        stage: str,
        complexity: str,
        hyperparams: Dict = None
    ) -> pd.DataFrame:
        """Compute all metrics and add metadata."""
        
        if predicted_network.empty:
            logger.warning(f"Empty network for {dataset_name}, {objective_name}")
            return pd.DataFrame()
        
        # Rank predictions
        ranked = predicted_network.sort_values('weight', ascending=False)
        
        # Create ground truth set
        gt_set = self.create_groundtruth_set(groundtruth)
        
        # Compute precision@K
        metrics_df = self.compute_precision_at_k(ranked, gt_set)
        
        # Add metadata
        metrics_df['dataset'] = dataset_name
        metrics_df['objective'] = objective_name
        metrics_df['stage'] = stage
        metrics_df['complexity'] = complexity
        
        # Add hyperparameters
        if hyperparams:
            for param, value in hyperparams.items():
                metrics_df[param] = value
                
        return metrics_df
    
    @staticmethod
    def clean_objective_name(objective: str) -> str:
        """Clean objective names for reporting."""
        objective = objective.replace('-stage1', '').replace('-stage2', '') \
                          .replace('-stage3', '').replace('-stage4', '')
        
        mapping = {
            'count:poisson': 'cnt:pois',
            'distribution:exponential': 'dst:exp',
            'distribution:laplace': 'dst:lap',
            'distribution:negative-binomial': 'dst:ng-bn',
            'distribution:normal': 'dst:norm',
            'distribution:poisson': 'dst:pois',
            'distribution:log-normal': 'dst:logn',
            'reg:absoluteerror': 'reg:ae',
            'reg:gamma': 'reg:gam',
            'reg:pseudohubererror': 'reg:psh',
            'reg:squarederror': 'reg:se',
            'reg:tweedie': 'reg:twd'
        }
        
        return mapping.get(objective, objective)