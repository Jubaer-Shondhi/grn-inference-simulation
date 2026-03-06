#!/usr/bin/env python
"""Main script to run the GRN inference experiment."""

import os
import sys
import time
import logging
from pathlib import Path
import pandas as pd
import warnings

warnings.filterwarnings('ignore', message="overflow encountered", category=RuntimeWarning)
warnings.filterwarnings('ignore', message="overflow encountered in multiply")
warnings.filterwarnings('ignore', message="overflow encountered in cast")

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.data.loader import DataLoader
from src.models.inference import GRNInferencer
from src.evaluation.metrics import MetricsCalculator
from src.pipeline.stages import HyperparameterStages
from src.utils.config_manager import ConfigManager
from src.utils.parallel import get_optimal_workers
from src.utils.logger import setup_logging

def main():
    """Main execution function."""
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Load configurations
    config_manager = ConfigManager()
    config = config_manager.load_config()
    objectives_config = config_manager.load_objectives()
    
    # Initialize components
    data_loader = DataLoader(config['paths']['base_data'])
    inferencer = GRNInferencer(batch_size=config['pipeline']['batch_size'])
    metrics_calculator = MetricsCalculator(thresholds=config['pipeline']['thresholds'])
    
    # Get optimal workers
    n_workers = get_optimal_workers(config['pipeline']['n_workers'])
    
    # Load datasets
    logger.info("Loading datasets...")
    datasets = data_loader.load_all_datasets(config['datasets']['complexities'])
    
    # Initialize hyperparameter stages
    hyperparam_stages = HyperparameterStages(
        base_params=config['model']['base_hyperparameters'],
        hyperparam_grid={
            'max_depth': [2, 4, 6, 8],
            'learning_rate': [0.03, 0.05, 0.1, 0.2],
            'n_estimators': [50, 100, 200, 400],
            'subsample': [0.6, 0.8, 1.0],
            'colsample_bytree': [0.6, 0.8, 1.0]
        }
    )
    
    # Define stage configurations
    stage2_pairs = [
        ('max_depth', 'learning_rate'),
        ('max_depth', 'n_estimators'),
        ('subsample', 'colsample_bytree'),
        ('n_estimators', 'subsample'),
        ('n_estimators', 'learning_rate')
    ]
    
    stage3_triples = [
        ('max_depth', 'learning_rate', 'n_estimators'),
        ('learning_rate', 'n_estimators', 'subsample'),
        ('learning_rate', 'n_estimators', 'colsample_bytree'),
        ('max_depth', 'learning_rate', 'subsample')
    ]
    
    # Collect all metrics
    all_metrics = []
    start_time = time.time()
    
    # Main experiment loop
    for complexity, dataset_list in datasets.items():
        logger.info(f"Processing complexity: {complexity}")
        
        for gex_data, ground_truth, dataset_name in dataset_list:
            logger.info(f"  Dataset: {dataset_name}")
            
            # Get TF names
            tf_names = list(ground_truth.source.unique())
            
            # STAGE 1: Single hyperparameter variations
            stage1_configs = hyperparam_stages.generate_stage1_configs()
            run_stage_experiments(
                stage_name="stage1",
                configs=stage1_configs,
                gex_data=gex_data,
                ground_truth=ground_truth,
                tf_names=tf_names,
                dataset_name=dataset_name,
                complexity=complexity,
                inferencer=inferencer,
                metrics_calculator=metrics_calculator,
                objectives_config=objectives_config,
                n_workers=n_workers,
                metrics_collector=all_metrics,
                config=config
            )
            
            # STAGE 2: Two-hyperparameter combinations
            stage2_configs = hyperparam_stages.generate_stage2_configs(stage2_pairs)
            run_stage_experiments(
                stage_name="stage2",
                configs=stage2_configs,
                gex_data=gex_data,
                ground_truth=ground_truth,
                tf_names=tf_names,
                dataset_name=dataset_name,
                complexity=complexity,
                inferencer=inferencer,
                metrics_calculator=metrics_calculator,
                objectives_config=objectives_config,
                n_workers=n_workers,
                metrics_collector=all_metrics,
                config=config
            )
            
            # STAGE 3: Three-hyperparameter combinations
            stage3_configs = hyperparam_stages.generate_stage3_configs(stage3_triples)
            run_stage_experiments(
                stage_name="stage3",
                configs=stage3_configs,
                gex_data=gex_data,
                ground_truth=ground_truth,
                tf_names=tf_names,
                dataset_name=dataset_name,
                complexity=complexity,
                inferencer=inferencer,
                metrics_calculator=metrics_calculator,
                objectives_config=objectives_config,
                n_workers=n_workers,
                metrics_collector=all_metrics,
                config=config
            )
            
            # STAGE 4: Refined configurations
            if all_metrics:
                metrics_df = pd.concat(all_metrics, ignore_index=True)
                stage4_configs = hyperparam_stages.generate_stage4_configs(
                    metrics_df=metrics_df,
                    dataset_name=dataset_name,
                    reference_topn=config['evaluation']['stage4']['reference_topn'],
                    top_n_configs=config['evaluation']['stage4']['top_n_configs']
                )
                
                if stage4_configs:
                    run_stage_experiments(
                        stage_name="stage4",
                        configs=stage4_configs,
                        gex_data=gex_data,
                        ground_truth=ground_truth,
                        tf_names=tf_names,
                        dataset_name=dataset_name,
                        complexity=complexity,
                        inferencer=inferencer,
                        metrics_calculator=metrics_calculator,
                        objectives_config=objectives_config,
                        n_workers=n_workers,
                        metrics_collector=all_metrics,
                        config=config
                    )
            
            # Auto-save results
            if len(all_metrics) > 0 and len(all_metrics) % config['logging']['save_frequency'] == 0:
                save_results(all_metrics, config['paths']['results_dir'])
    
    # Final save
    save_results(all_metrics, config['paths']['results_dir'])
    
    # Generate summary tables
    generate_summary_tables(all_metrics, config['paths']['results_dir'])
    
    logger.info(f"Total execution time: {(time.time() - start_time) / 60:.2f} minutes")

def run_stage_experiments(
    stage_name,
    configs,
    gex_data,
    ground_truth,
    tf_names,
    dataset_name,
    complexity,
    inferencer,
    metrics_calculator,
    objectives_config,
    n_workers,
    metrics_collector,
    config
):
    """Run experiments for a specific stage."""
    logger = logging.getLogger(__name__)
    
    # Standard objectives
    for objective in objectives_config['standard_objectives']:
        for hyperparams in configs:
            logger.info(f"[{stage_name.upper()}] {objective} | hyperparams={hyperparams}")
            
            # Prepare model parameters
            model_params = {
                'objective': objective,
                'random_state': config['model']['base_hyperparameters']['random_state'],
                'eval_metric': objectives_config['eval_metrics'][objective]
            }
            
            if objective == 'reg:tweedie':
                model_params['tweedie_variance_power'] = 1.5
                
            model_params.update(hyperparams)
            
            # Infer network
            network = inferencer.compute_network(
                gex_data.copy(),
                tf_names,
                'regressor',
                model_params,
                n_workers
            )
            
            if not network.empty:
                # Calculate metrics
                metrics = metrics_calculator.compute_all_metrics(
                    predicted_network=network,
                    groundtruth=ground_truth,
                    dataset_name=dataset_name,
                    objective_name=f"{objective}-{stage_name}",
                    stage=stage_name,
                    complexity=complexity,
                    hyperparams=hyperparams
                )
                
                if not metrics.empty:
                    metrics_collector.append(metrics)
    
    # Distribution objectives
    for dist_name, xgb_dist_name in objectives_config['distributions'].items():
        for hyperparams in configs:
            logger.info(f"[{stage_name.upper()}] distribution:{dist_name} | hyperparams={hyperparams}")
            
            # Prepare model parameters
            model_params = {
                'distribution': xgb_dist_name,
                'random_state': config['model']['base_hyperparameters']['random_state']
            }
            model_params.update(hyperparams)
            
            # Infer network
            network = inferencer.compute_network(
                gex_data.copy(),
                tf_names,
                'distribution',
                model_params,
                n_workers
            )
            
            if not network.empty:
                # Calculate metrics
                metrics = metrics_calculator.compute_all_metrics(
                    predicted_network=network,
                    groundtruth=ground_truth,
                    dataset_name=dataset_name,
                    objective_name=f"distribution:{dist_name}-{stage_name}",
                    stage=stage_name,
                    complexity=complexity,
                    hyperparams=hyperparams
                )
                
                if not metrics.empty:
                    metrics_collector.append(metrics)

def save_results(metrics_collector, results_dir):
    """Save collected metrics to disk."""
    logger = logging.getLogger(__name__)
    if not metrics_collector:
        return
        
    # Create the DataFrame once
    output_path = Path(results_dir) / "GRN_Inference_RESULTS.csv"
    df = pd.concat(metrics_collector, ignore_index=True)
    
    # Save to first file
    df.to_csv(output_path, index=False)
    logger.info(f"Results saved to {output_path}")
    
    precision_path = Path(results_dir) / "precision_metrics.csv"
    df.to_csv(precision_path, index=False)
    logger.info(f"Precision metrics saved to {precision_path}")

def generate_summary_tables(metrics_collector, results_dir):
    """Generate and save summary tables."""
    logger = logging.getLogger(__name__)
    if not metrics_collector:
        return
        
    from src.evaluation.metrics import MetricsCalculator
    
    df = pd.concat(metrics_collector, ignore_index=True)
    results_dir = Path(results_dir)
    
    # Split by stage
    for stage in ['stage1', 'stage2', 'stage3', 'stage4']:
        stage_df = df[df['stage'] == stage].copy()
        
        if not stage_df.empty:
            # Clean objective names
            stage_df['objective_clean'] = stage_df['objective'].apply(
                MetricsCalculator.clean_objective_name
            )
            
            # Create pivot table
            pivot = (
                stage_df.groupby(['objective_clean', 'TopN'])['Precision']
                .mean()
                .reset_index()
                .pivot(index='TopN', columns='objective_clean', values='Precision')
                .sort_index(axis=1)
            )
            
            # Print to console
            print(f"\n## {stage.upper()} – Mean Precision by Objective and Top-N")
            print(pivot.to_string(float_format="%.3f"))

if __name__ == "__main__":
    main()