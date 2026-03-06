#!/usr/bin/env python
"""Script to generate simulated GRN data using R."""

import argparse
import sys
from pathlib import Path
import logging
import yaml

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.data.simulation_bridge import RSimulationBridge
from src.utils.logger import setup_logging

def main():
    parser = argparse.ArgumentParser(
        description="Generate simulated GRN data using R",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate all datasets using config file
  python scripts/generate_simulated_data.py --config configs/simulation_config.yaml
  
  # Generate specific complexity
  python scripts/generate_simulated_data.py --output_dir data/simulated/5_sources \\
      --num_sources 5 --max_out_degree 50 --n_datasets 333 --n_cells 500
  
  # Install R dependencies first
  python scripts/generate_simulated_data.py --install_deps
  
  # Generate with custom R path
  python scripts/generate_simulated_data.py --config configs/simulation_config.yaml \\
      --rscript_path "C:/Program Files/R/R-4.2.0/bin/Rscript.exe"
        """
    )
    
    # Config file option
    parser.add_argument("--config", type=str, 
                       help="Path to simulation configuration file")
    
    # Individual parameters (used if no config file)
    parser.add_argument("--output_dir", type=str,
                       help="Base output directory for simulated data")
    parser.add_argument("--num_sources", type=int,
                       help="Number of source nodes")
    parser.add_argument("--max_out_degree", type=int,
                       help="Maximum outgoing connections")
    parser.add_argument("--n_datasets", type=int, default=10,
                       help="Number of datasets to generate (default: 10)")
    parser.add_argument("--n_cells", type=int, default=500,
                       help="Number of cells per dataset (default: 500)")
    parser.add_argument("--mor_mean", type=float, default=5,
                       help="Mean for MOR values (default: 5)")
    parser.add_argument("--mor_sd", type=float, default=1,
                       help="Standard deviation for MOR values (default: 1)")
    
    # Global options
    parser.add_argument("--rscript_path", type=str, default="Rscript",
                       help="Path to Rscript executable (default: Rscript)")
    parser.add_argument("--install_deps", action="store_true",
                       help="Install R dependencies first")
    parser.add_argument("--verify_only", action="store_true",
                       help="Only verify existing datasets, don't generate")
    parser.add_argument("--complexity", type=str, 
                       choices=["5_sources", "10_sources", "20_sources", "all"],
                       default="all", help="Which complexity to generate (default: all)")
    parser.add_argument("--log_level", type=str, 
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       default="INFO", help="Logging level")
    parser.add_argument("--seed", type=int, default=42,
                       help="Random seed for reproducibility (default: 42)")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(level=getattr(logging, args.log_level))
    logger = logging.getLogger(__name__)
    
    # Initialize bridge
    bridge = RSimulationBridge(
        rscript_path=args.rscript_path,
        config_path=args.config
    )
    
    # Install dependencies if requested
    if args.install_deps:
        logger.info("Installing R dependencies...")
        if not bridge.install_dependencies():
            logger.error("Failed to install R dependencies")
            sys.exit(1)
        logger.info("R dependencies installed successfully")
        if not args.config and not args.output_dir:
            # If only installing deps, exit successfully
            sys.exit(0)
    
    # Verify only mode
    if args.verify_only:
        if not args.config:
            logger.error("Config file required for verification")
            sys.exit(1)
        
        # Load config to get complexities
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
        
        complexities = config.get('simulation', {}).get('complexities', {})
        base_dir = args.output_dir or "data/simulated"
        
        all_verified = True
        for comp_name, params in complexities.items():
            if args.complexity != "all" and comp_name != args.complexity:
                continue
                
            verified = bridge.verify_datasets(
                base_dir=base_dir,
                complexity=comp_name,
                expected_datasets=params['n_datasets']
            )
            
            if verified:
                logger.info(f"{comp_name}: Verified")
            else:
                logger.error(f"{comp_name}: Verification failed")
                all_verified = False
        
        sys.exit(0 if all_verified else 1)
    
    # Generate data
    if args.config:
        # Use config file
        logger.info(f"Using configuration from {args.config}")
        
        # Get output directory from args or use default from config
        base_output_dir = args.output_dir
        
        # Generate all complexities
        results = bridge.generate_all_complexities(
            base_output_dir=base_output_dir,
            complexity_configs=None  # Will use config file
        )
        
        # Print summary
        logger.info("\n" + "="*50)
        logger.info("SIMULATION SUMMARY")
        logger.info("="*50)
        
        all_successful = True
        for complexity, result in results.items():
            status = "SUCCESS" if result.get('success') else "FAILED"
            logger.info(f"{complexity}: {status}")
            if result.get('metadata'):
                logger.info(f"   Output: {result.get('output_dir')}")
            all_successful = all_successful and result.get('success', False)
        
        if all_successful:
            logger.info("\nAll datasets generated successfully!")
        else:
            logger.error("\nSome datasets failed to generate")
            sys.exit(1)
    
    else:
        # Use command line arguments
        logger.info("Generating dataset from command line arguments")
        
        # Validate required arguments
        if not all([args.output_dir, args.num_sources, args.max_out_degree]):
            logger.error("When not using config file, --output_dir, --num_sources, and --max_out_degree are required")
            logger.error("Example: python scripts/generate_simulated_data.py --output_dir data/simulated/test --num_sources 5 --max_out_degree 50 --n_datasets 2 --n_cells 100")
            sys.exit(1)
        
        # Run single simulation
        logger.info(f"Generating {args.n_datasets} datasets with {args.num_sources} sources, {args.n_cells} cells each")
        
        # Simulation parameters
        sim_params = {
            'num.cif': 40,
            'discrete.cif': True,
            'cif.sigma': 0.25,
            'speed.up': True,
            'diff.cif.fraction': 0.05,
            'unregulated.gene.ratio': 0.05,
            'do.velocity': False,
            'intrinsic.noise': 1.0
        }
        
        success, metadata = bridge.simulate_dataset(
            output_dir=args.output_dir,
            num_sources=args.num_sources,
            max_out_degree=args.max_out_degree,
            n_datasets=args.n_datasets,
            n_cells=args.n_cells,
            mor_mean=args.mor_mean,
            mor_sd=args.mor_sd,
            seed=args.seed,
            generate_plots=True,
            simulation_params=sim_params
        )
        
        if success:
            logger.info(f"Dataset generated successfully in {args.output_dir}")
            if metadata:
                data_files = metadata.get('data_files', [])
                net_files = metadata.get('network_files', [])
                logger.info(f"   Generated {len(data_files)} data files and {len(net_files)} network files")
        else:
            logger.error("Failed to generate dataset")
            sys.exit(1)

if __name__ == "__main__":
    main()