#!/usr/bin/env python
"""Generate plots and tables from GRN inference results."""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import argparse
from pathlib import Path

def load_and_prepare_data(results_path):
    """Load and prepare data for plotting."""
    df = pd.read_csv(results_path)
    
    # Clean objective names by removing stage suffixes first
    df['objective_base'] = df['objective'].str.replace('-stage1', '').str.replace('-stage2', '')\
                                           .str.replace('-stage3', '').str.replace('-stage4', '')
    
    # Create mapping for clean short names
    objective_mapping = {
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
    
    # Apply mapping to create clean names
    df['objective_clean'] = df['objective_base'].map(objective_mapping)
    
    # Extract stage
    df['stage'] = df['objective'].str.extract(r'(stage[1-4])')
    
    return df

def plot_precision_curves(df, figures_dir):
    """Plot 1: Precision curves with clean names."""
    plt.figure(figsize=(10, 5))
    
    unique_objectives = sorted(df['objective_clean'].unique())
    colors = plt.cm.tab10(np.linspace(0, 1, len(unique_objectives)))
    
    thresholds = sorted(df['TopN'].unique())
    threshold_labels = [str(t) for t in thresholds]
    
    for i, obj in enumerate(unique_objectives):
        obj_data = df[df['objective_clean'] == obj].groupby('TopN')['Precision'].mean().reset_index()
        obj_data = obj_data.sort_values('TopN')
        plt.plot(range(len(obj_data['TopN'])), obj_data['Precision'], 
                 label=obj, linewidth=2, marker='o', markersize=4, color=colors[i])
    
    plt.xlabel('Top-k Edges (k)', fontsize=13)
    plt.ylabel('Precision@k', fontsize=13)
    plt.title('Precision@k Curves for All XGBoost Objectives', fontsize=14, fontweight='bold')
    plt.xticks(range(len(thresholds)), threshold_labels, rotation=45)
    plt.ylim(0, 0.4)
    plt.legend(loc='upper right', ncol=2, fontsize=14, frameon=True)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # Save
    plt.savefig(figures_dir / 'precision_curves.pdf', dpi=300, bbox_inches='tight')
    # plt.savefig(figures_dir / 'precision_curves.png', dpi=300, bbox_inches='tight')
    # plt.show()
    plt.close()

def plot_stagewise_curves(df, figures_dir):
    """Plot 2: Stage-wise precision curves."""
    plt.figure(figsize=(10, 5))
    
    # Create objective display names with stage
    df_copy = df.copy()
    df_copy['objective_base'] = df_copy['objective'].str.replace('-stage1', '').str.replace('-stage2', '')\
                                                     .str.replace('-stage3', '').str.replace('-stage4', '')
    df_copy['stage'] = df_copy['objective'].str.extract(r'(stage[1-4])')
    df_copy['objective_clean'] = df_copy['objective_base'].map(objective_mapping)
    df_copy['objective_stage'] = df_copy['objective_clean'] + '-' + df_copy['stage']
    
    thresholds = sorted(df_copy['TopN'].unique())
    threshold_labels = [str(t) for t in thresholds]
    
    # Use a colormap with 12 distinct colors
    colors = plt.cm.tab20(np.linspace(0, 1, 12))
    linestyles = ['-', '--', '-.', ':']
    
    for i, obj in enumerate(sorted(df_copy['objective_clean'].unique())):
        for j, stage in enumerate(['stage1', 'stage2', 'stage3', 'stage4']):
            obj_stage = f"{obj}-{stage}"
            data = df_copy[df_copy['objective_stage'] == obj_stage].groupby('TopN')['Precision'].mean().reset_index()
            if not data.empty:
                data = data.sort_values('TopN')
                plt.plot(range(len(data['TopN'])), data['Precision'], 
                        label=f"{obj}-{stage}", linewidth=1.5, 
                        linestyle=linestyles[j], color=colors[i], alpha=0.8)
    
    plt.xlabel('Top-k Edges (k)', fontsize=12)
    plt.ylabel('Precision@k', fontsize=12)
    plt.title('Precision Curves: All Objectives (Stage-wise)', fontsize=14, fontweight='bold')
    plt.xticks(range(len(thresholds)), threshold_labels, rotation=45)
    plt.ylim(0, 0.4)
    plt.legend(loc='upper right', frameon=True, fontsize=7, ncol=3)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # Save
    # plt.savefig(figures_dir / 'precision_curves_stagewise.png', dpi=300, bbox_inches='tight')
    plt.savefig(figures_dir / 'precision_curves_stagewise.pdf', dpi=300, bbox_inches='tight')
    # plt.show()
    plt.close()

def plot_stages_1to3_configs(df, figures_dir):
    """Plot 3: Best configurations for Stages 1-3 at TopN=50."""
    df_50 = df[df['TopN'] == 50].copy()
    
    # STAGE 1
    stage1 = df_50[df_50['stage'] == 'stage1']
    best_single = {}
    params = ['max_depth', 'learning_rate', 'n_estimators', 'subsample', 'colsample_bytree']
    
    for param in params:
        best_val = stage1.groupby(param)['Precision'].mean().sort_values(ascending=False).head(1)
        best_single[param] = (best_val.index[0], best_val.values[0])
    
    # STAGE 2
    stage2 = df_50[df_50['stage'] == 'stage2']
    stage2_pairs = [('max_depth', 'learning_rate'),
                    ('max_depth', 'n_estimators'),
                    ('subsample', 'colsample_bytree'),
                    ('n_estimators', 'subsample'),
                    ('n_estimators', 'learning_rate')]
    
    best_pairs = []
    for param1, param2 in stage2_pairs:
        pair_perf = stage2.groupby([param1, param2])['Precision'].mean().reset_index()
        pair_perf = pair_perf.sort_values('Precision', ascending=False).head(2)
        for _, row in pair_perf.iterrows():
            best_pairs.append({
                'param1': param1, 'value1': row[param1],
                'param2': param2, 'value2': row[param2],
                'precision': row['Precision']
            })
    
    # STAGE 3
    stage3 = df_50[df_50['stage'] == 'stage3']
    stage3_groups = [
        ('max_depth', 'learning_rate', 'n_estimators'),
        ('learning_rate', 'n_estimators', 'subsample'),
        ('learning_rate', 'n_estimators', 'colsample_bytree'),
        ('max_depth', 'learning_rate', 'subsample')
    ]
    
    best_triplets = []
    for params_trip in stage3_groups:
        param1, param2, param3 = params_trip
        trip_perf = stage3.groupby([param1, param2, param3])['Precision'].mean().reset_index()
        trip_perf = trip_perf.sort_values('Precision', ascending=False).head(1)
        for _, row in trip_perf.iterrows():
            best_triplets.append({
                'param1': param1, 'value1': row[param1],
                'param2': param2, 'value2': row[param2],
                'param3': param3, 'value3': row[param3],
                'precision': row['Precision']
            })
    
    # Create vertical colored table for Stages 1-3
    fig, axes = plt.subplots(3, 1, figsize=(6, 8))
    for ax in axes:
        ax.axis('off')
        ax.set_position([0, 0, 1, 1])
    
    # Stage 1 Table
    stage1_data = []
    cell_colors1 = []
    for param, (val, prec) in best_single.items():
        stage1_data.append([param, str(val), f"{prec:.3f}"])
        cell_colors1.append([[1,1,1], [1,1,1], [1, 1-prec, 1-prec]])
    
    table1 = axes[0].table(cellText=stage1_data, 
                           colLabels=['Parameter', 'Best', 'Prec@50'],
                           cellLoc='center', loc='center',
                           cellColours=cell_colors1, bbox=[0,0,1,1])
    table1.auto_set_font_size(False)
    table1.set_fontsize(9)
    axes[0].set_title('Stage 1: Best Single Parameters', fontweight='bold', fontsize=10, pad=2)
    
    # Stage 2 Table
    stage2_data = []
    cell_colors2 = []
    for pair in best_pairs[:8]:
        stage2_data.append([f"{pair['param1']}={pair['value1']}", 
                            f"{pair['param2']}={pair['value2']}", 
                            f"{pair['precision']:.3f}"])
        cell_colors2.append([[1,1,1], [1,1,1], [1, 1-pair['precision'], 1-pair['precision']]])
    
    table2 = axes[1].table(cellText=stage2_data,
                           colLabels=['Pair 1', 'Pair 2', 'Prec@50'],
                           cellLoc='center', loc='center',
                           cellColours=cell_colors2, bbox=[0,0,1,1])
    table2.auto_set_font_size(False)
    table2.set_fontsize(8)
    axes[1].set_title('Stage 2: Best Parameter Pairs', fontweight='bold', fontsize=10, pad=2)
    
    # Stage 3 Table
    stage3_data = []
    cell_colors3 = []
    for trip in best_triplets:
        stage3_data.append([f"{trip['param1']}={trip['value1']}", 
                            f"{trip['param2']}={trip['value2']}",
                            f"{trip['param3']}={trip['value3']}",
                            f"{trip['precision']:.3f}"])
        cell_colors3.append([[1,1,1], [1,1,1], [1,1,1], [1, 1-trip['precision'], 1-trip['precision']]])
    
    table3 = axes[2].table(cellText=stage3_data,
                           colLabels=['P1', 'P2', 'P3', 'Prec'],
                           cellLoc='center', loc='center',
                           cellColours=cell_colors3, bbox=[0,0,1,1])
    table3.auto_set_font_size(False)
    table3.set_fontsize(7)
    axes[2].set_title('Stage 3: Best Parameter Triplets', fontweight='bold', fontsize=10, pad=2)
    
    plt.suptitle('Best Configurations at TopN=50 (Stages 1-3)', fontsize=12, fontweight='bold', y=0.98)
    plt.subplots_adjust(left=0, right=1, top=0.95, bottom=0, hspace=0.1)
    
    # Save
    plt.savefig(figures_dir / 'stages_1to3_configs.pdf', dpi=300, bbox_inches='tight', pad_inches=0)
    # plt.show()
    plt.close()
    
    return best_single, best_pairs, best_triplets

def plot_stage4_by_complexity(df, figures_dir):
    """Plot 4: Stage 4 configurations by complexity."""
    complexities = ['5_sources', '10_sources', '20_sources']
    stage4_data = []
    
    for complexity in complexities:
        best = df[(df['TopN'] == 50) & 
                  (df['stage'] == 'stage4') & 
                  (df['complexity'] == complexity)].groupby(
            ['max_depth', 'learning_rate', 'n_estimators', 'subsample', 'colsample_bytree']
        )['Precision'].mean().sort_values(ascending=False).head(1).reset_index()
        
        if not best.empty:
            row = best.iloc[0]
            stage4_data.append([
                complexity.replace('_', ' '),
                f"{row['max_depth']:.0f}",
                f"{row['learning_rate']}",
                f"{row['n_estimators']:.0f}",
                f"{row['subsample']}",
                f"{row['colsample_bytree']}",
                f"{row['Precision']:.3f}"
            ])
    
    # Create Stage 4 table
    fig, ax = plt.subplots(figsize=(8, 2.5))
    ax.axis('off')
    ax.axis('tight')
    
    table4 = ax.table(cellText=stage4_data,
                      colLabels=['Network', 'depth', 'lr', 'n_est', 'sub', 'col', 'Prec@50'],
                      cellLoc='center', loc='center')
    table4.auto_set_font_size(False)
    table4.set_fontsize(10)
    table4.scale(1, 1.5)
    ax.set_title('Stage 4: Optimal Configurations by Network Complexity', fontweight='bold', fontsize=12)
    
    plt.tight_layout()
    
    # Save
    plt.savefig(figures_dir / 'stage4_by_complexity.pdf', dpi=300, bbox_inches='tight')
    # plt.show()
    plt.close()
    
    # Print summary
    print("\n" + "="*60)
    print("STAGE 4 SUMMARY BY COMPLEXITY")
    print("="*60)
    for row in stage4_data:
        print(f"{row[0]}: depth={row[1]}, lr={row[2]}, n_est={row[3]}, sub={row[4]}, col={row[5]} → Prec={row[6]}")
    
    return stage4_data

def plot_top_objectives_bar(df, figures_dir):
    """Plot 5: Top objectives bar charts."""
    key_thresholds = [5, 50, 300]
    top_n = 6
    
    fig, axes = plt.subplots(1, 3, figsize=(12, 5))
    
    for idx, k in enumerate(key_thresholds):
        k_data = df[df['TopN'] == k].groupby('objective_clean')['Precision'].mean()\
                                     .sort_values(ascending=False).head(top_n)
        
        axes[idx].barh(range(len(k_data)), k_data.values, color='steelblue')
        axes[idx].set_yticks(range(len(k_data)))
        axes[idx].set_yticklabels(k_data.index)
        axes[idx].set_xlabel('Precision', fontsize=14)
        axes[idx].set_title(f'k={k}')
        axes[idx].invert_yaxis()
        
        axes[idx].tick_params(axis='both', labelsize=13)
        for label in axes[idx].get_xticklabels() + axes[idx].get_yticklabels():
            label.set_fontsize(15)
    
    plt.suptitle('Top-6 Objectives at Key Thresholds (k=5, 50, 300)', 
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    # Save
    plt.savefig(figures_dir / 'top_objectives_bar.pdf', dpi=300, bbox_inches='tight', pad_inches=0.02)
    # plt.savefig(figures_dir / 'top_objectives_bar.png', dpi=300, bbox_inches='tight')
    # plt.show()
    plt.close()

def main():
    parser = argparse.ArgumentParser(description='Generate plots from GRN results')
    parser.add_argument('--input_data', type=str, 
                       default="results",  
                       help='Directory containing input results CSV')
    parser.add_argument('--output_dir', type=str,
                       default="results",  
                       help='Directory to save figures')
    args = parser.parse_args()
    
    # Setup paths
    input_dir = Path(args.input_data)
    output_dir = Path(args.output_dir)
    figures_dir = output_dir / 'figures'
    figures_dir.mkdir(parents=True, exist_ok=True)
    
    # Load data from input directory
    results_file = input_dir / 'precision_metrics.csv'
    if not results_file.exists():
        results_file = input_dir / 'GRN_Inference_RESULTS.csv'
    
    print(f"Loading data from: {results_file}")
    print(f"Saving figures to: {figures_dir}")
    df = load_and_prepare_data(results_file)
    
    # Check mapping worked
    print("\nMapping check:")
    print(df[['objective_base', 'objective_clean']].drop_duplicates().sort_values('objective_clean'))
    
    # Generate all plots (they will save to figures_dir)
    print("\n1. Generating precision curves...")
    plot_precision_curves(df, figures_dir)
    
    print("\n2. Generating stage-wise curves...")
    plot_stagewise_curves(df, figures_dir)
    
    print("\n3. Generating Stages 1-3 configs table...")
    best_single, best_pairs, best_triplets = plot_stages_1to3_configs(df, figures_dir)
    
    print("\n4. Generating Stage 4 by complexity table...")
    stage4_data = plot_stage4_by_complexity(df, figures_dir)
    
    print("\n5. Generating top objectives bar charts...")
    plot_top_objectives_bar(df, figures_dir)
    
    print(f"\nAll plots saved to: {figures_dir}")

if __name__ == "__main__":
    # Define objective mapping here for use in functions
    objective_mapping = {
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
    main()