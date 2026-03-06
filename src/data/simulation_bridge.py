"""Python-R bridge for GRN data simulation."""

import subprocess
import pandas as pd
import os
from pathlib import Path
import logging
import time
from typing import Dict, List, Optional, Tuple, Union
import yaml

logger = logging.getLogger(__name__)

class RSimulationBridge:
    """Bridge to run R simulation scripts from Python."""
    
    def __init__(self, rscript_path: str = "Rscript", config_path: Optional[str] = None):
        """
        Initialize the R bridge.
        
        Args:
            rscript_path: Path to Rscript executable
            config_path: Path to simulation configuration file
        """
        self.rscript_path = rscript_path
        self.project_root = Path(__file__).parent.parent.parent
        self.r_scripts_dir = self.project_root / "r_scripts"
        
        # Load configuration if provided
        self.config = {}
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: str) -> Dict:
        """Load simulation configuration from YAML file."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        logger.info(f"Loaded simulation config from {config_path}")
        return self.config
    
    def check_r_installation(self) -> bool:
        """Check if R is installed and accessible."""
        try:
            result = subprocess.run(
                [self.rscript_path, "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            version_line = result.stdout.splitlines()[0] if result.stdout else "Unknown"
            logger.info(f"R found: {version_line}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("R not found. Please install R and add to PATH.")
            return False
    
    def install_dependencies(self) -> bool:
        """Install required R packages."""
        logger.info("Installing R dependencies...")
        
        install_script = self.r_scripts_dir / "install_dependencies.R"
        
        if not install_script.exists():
            logger.error(f"Install script not found: {install_script}")
            return False
        
        try:
            result = subprocess.run(
                [self.rscript_path, str(install_script)],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info("R dependencies installed successfully")
            if result.stdout:
                logger.debug(result.stdout)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install R dependencies: {e.stderr}")
            return False
    
    def simulate_dataset(
        self,
        output_dir: str,
        num_sources: int,
        max_out_degree: int,
        n_datasets: int = 10,
        n_cells: int = 500,
        mor_mean: float = 5,
        mor_sd: float = 1,
        seed: int = 42,
        generate_plots: bool = True,
        simulation_params: Optional[Dict] = None,
        timeout: Optional[int] = 7200
    ) -> Tuple[bool, Dict]:
        """
        Run R simulation script to generate datasets.
        
        Args:
            output_dir: Directory to save simulated data
            num_sources: Number of source nodes
            max_out_degree: Maximum outgoing connections
            n_datasets: Number of datasets to generate
            n_cells: Number of cells per dataset
            mor_mean: Mean for MOR values
            mor_sd: Standard deviation for MOR values
            seed: Random seed
            generate_plots: Generate t-SNE plots
            simulation_params: Additional simulation parameters
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (success, metadata)
        """
        if not self.check_r_installation():
            return False, {}
        
        # Ensure output directory exists
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Path to simulation script
        sim_script = self.r_scripts_dir / "simulate_data.R"
        
        if not sim_script.exists():
            logger.error(f"Simulation script not found: {sim_script}")
            return False, {}
        
        # Build command - FIX: Replace backslashes with forward slashes
        output_dir_str = str(output_dir).replace('\\', '/')
        cmd = [
            self.rscript_path,
            str(sim_script),
            f"--output_dir={output_dir_str}",
            f"--num_sources={num_sources}",
            f"--max_out_degree={max_out_degree}",
            f"--n_datasets={n_datasets}",
            f"--n_cells={n_cells}",
            f"--mor_mean={mor_mean}",
            f"--mor_sd={mor_sd}",
            f"--seed={seed}",
            f"--generate_plots={'TRUE' if generate_plots else 'FALSE'}"
        ]
        
        # Add simulation parameters if provided
        if simulation_params:
            param_mapping = {
                'num.cif': '--num_cif',
                'discrete.cif': '--discrete_cif',
                'cif.sigma': '--cif_sigma',
                'speed.up': '--speed_up',
                'diff.cif.fraction': '--diff_cif_fraction',
                'unregulated.gene.ratio': '--unregulated_gene_ratio',
                'do.velocity': '--do_velocity',
                'intrinsic.noise': '--intrinsic_noise'
            }
            
            for r_param, cmd_param in param_mapping.items():
                if r_param in simulation_params:
                    value = simulation_params[r_param]
                    # Convert boolean to R-style logical
                    if isinstance(value, bool):
                        value = 'TRUE' if value else 'FALSE'
                    cmd.append(f"{cmd_param}={value}")
        
        logger.info(f"Running R simulation: {' '.join(cmd)}")
        
        try:
            # Run simulation with timeout
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=timeout
            )
            elapsed = time.time() - start_time
            
            logger.info(f"R simulation completed in {elapsed:.1f} seconds")
            
            # Log output for debugging
            if result.stdout:
                for line in result.stdout.splitlines():
                    if "✓" in line or "Dataset" in line:
                        logger.info(line)
                    else:
                        logger.debug(line)
            
            # Check if files were created
            data_dir = output_path / "data"
            nets_dir = output_path / "nets"
            
            if data_dir.exists() and nets_dir.exists():
                data_files = list(data_dir.glob("data_*.tsv"))
                net_files = list(nets_dir.glob("network_*.tsv"))
                
                logger.info(f"Generated {len(data_files)} data files and {len(net_files)} network files")
                
                # Load metadata
                metadata = self.load_simulation_metadata(output_dir)
                
                success = len(data_files) > 0 and len(net_files) > 0
                return success, {
                    'data_files': [str(f) for f in data_files],
                    'network_files': [str(f) for f in net_files],
                    'metadata': metadata,
                    'elapsed_time': elapsed
                }
            else:
                logger.warning("No output files found")
                return False, {}
                
        except subprocess.TimeoutExpired:
            logger.error(f"R simulation timed out after {timeout} seconds")
            return False, {'error': 'timeout'}
        except subprocess.CalledProcessError as e:
            logger.error(f"R simulation failed with error: {e.stderr}")
            return False, {'error': e.stderr}
    
    def generate_all_complexities(
        self,
        base_output_dir: Optional[str] = None,
        complexity_configs: Optional[Dict] = None
    ) -> Dict[str, Dict]:
        """
        Generate datasets for all complexity levels.
        
        Args:
            base_output_dir: Base output directory (if None, uses from config)
            complexity_configs: Dictionary mapping complexity to parameters
                              If None, uses config file
            
        Returns:
            Dictionary mapping complexity to results
        """
        if complexity_configs is None:
            if not self.config:
                raise ValueError("No configuration provided. Either pass complexity_configs or load config first.")
            complexity_configs = self.config.get('simulation', {}).get('complexities', {})
        
        # If base_output_dir not provided, get it from config
        if base_output_dir is None:
            base_output_dir = self.config.get('simulation', {}).get('base_output_dir', 'data/simulated')
            logger.info(f"Using base output directory from config: {base_output_dir}")
        
        results = {}
        total_start = time.time()
        
        for complexity, params in complexity_configs.items():
            logger.info(f"\n{'='*50}")
            logger.info(f"Generating {complexity} datasets...")
            logger.info(f"{'='*50}")
            
            # DEBUG LINES
            logger.info(f"DEBUG - complexity key: '{complexity}'")
            logger.info(f"DEBUG - complexity type: {type(complexity)}")
            logger.info(f"DEBUG - params: {params}")
            logger.info(f"DEBUG - base_output_dir: {base_output_dir}")
            
            output_dir = Path(base_output_dir) / complexity
            logger.info(f"DEBUG - constructed output_dir: {output_dir}")
            
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Get simulation parameters from config if available
            sim_params = None
            if self.config:
                sim_params = self.config.get('simulation', {}).get('simulation_params')
            
            # Run simulation
            success, metadata = self.simulate_dataset(
                output_dir=str(output_dir),
                num_sources=params['num_sources'],
                max_out_degree=params['max_out_degree'],
                n_datasets=params['n_datasets'],
                n_cells=params.get('n_cells', 500),
                mor_mean=self.config.get('simulation', {}).get('mor', {}).get('mean', 5),
                mor_sd=self.config.get('simulation', {}).get('mor', {}).get('sd', 1),
                seed=self.config.get('simulation', {}).get('seed', 42),
                generate_plots=self.config.get('simulation', {}).get('generate_plots', True),
                simulation_params=sim_params,
                timeout=self.config.get('simulation', {}).get('timeout', 7200)
            )
            
            results[complexity] = {
                'success': success,
                'output_dir': str(output_dir),
                'metadata': metadata,
                'params': params
            }
            
            if success:
                logger.info(f"Successfully generated {complexity} datasets")
            else:
                logger.error(f"Failed to generate {complexity} datasets")
        
        total_elapsed = time.time() - total_start
        logger.info(f"\nTotal simulation time: {total_elapsed/60:.1f} minutes")
        
        return results
    
    def load_simulation_metadata(self, complexity_dir: str) -> Optional[pd.DataFrame]:
        """Load simulation metadata from CSV file."""
        metadata_file = Path(complexity_dir) / "simulation_metadata.csv"
        
        if metadata_file.exists():
            try:
                df = pd.read_csv(metadata_file)
                logger.debug(f"Loaded metadata from {metadata_file}")
                return df
            except Exception as e:
                logger.warning(f"Could not load metadata: {e}")
                return None
        else:
            logger.debug(f"No metadata file found at {metadata_file}")
            return None
    
    def verify_datasets(self, base_dir: str, complexity: str, expected_datasets: int) -> bool:
        """Verify that all expected datasets were generated."""
        data_dir = Path(base_dir) / complexity / "data"
        nets_dir = Path(base_dir) / complexity / "nets"
        
        if not data_dir.exists() or not nets_dir.exists():
            return False
        
        data_files = list(data_dir.glob("data_*.tsv"))
        net_files = list(nets_dir.glob("network_*.tsv"))
        
        # Check if we have the expected number
        if len(data_files) != expected_datasets or len(net_files) != expected_datasets:
            logger.warning(f"Expected {expected_datasets} datasets, found {len(data_files)} data files and {len(net_files)} network files")
            return False
        
        # Check if indices match
        data_indices = {int(f.stem.split('_')[1]) for f in data_files}
        net_indices = {int(f.stem.split('_')[1]) for f in net_files}
        
        if data_indices != net_indices:
            logger.warning("Data and network indices don't match")
            return False
        
        logger.info(f"Verified {len(data_files)} complete datasets for {complexity}")
        return True