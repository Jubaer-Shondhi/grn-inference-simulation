# GRN Inference Pipeline

A modular, reproducible pipeline for Gene Regulatory Network inference using XGBoost with various objectives and distributions.

## Features
- **Modular design**: Separated data loading, preprocessing, modeling, and evaluation
- **Hyperparameter tuning**: Multi-stage exploration (single, pairs, triples, refined)
- **Multiple objectives**: Support for both standard XGBoost objectives and XGBoost-Distribution
- **Parallel execution**: Efficient parallel processing of gene targets
- **Reproducible**: Full configuration management and logging

## Installation

### Option 1: Using pip
1. Clone the repository:
```bash
git clone https://github.com/Jubaer-Shondhi/grn-inference-pipeline
cd grn-inference-pipeline
```

2. Create and activate virtual environment:

Linux:
```bash
python3 -m venv venv
source venv/bin/activate  

# If you get "No module named venv", first run:
# sudo apt update
# sudo apt install python3-venv
```

Windows (Command Prompt):
```bash
python -m venv venv
venv\Scripts\activate  
```

Windows (Gitbash)
```bash
python -m venv venv
source venv/Scripts/activate
```

3. Install dependencies from requirements.txt:
```bash
python -m pip install -r requirements.txt
python -m pip install -e .
```

## Usage

### Data Options

#### Use Provided Datasets (Quick Start)
The repository includes example datasets in the `data/` folder for testing. **Each complexity folder contains 1 dataset**:
**Note:** By default, the configuration is set to run only the **5_sources** dataset (1 dataset). This allows you to run the complete pipeline, to verify everything works.

Run immediately:

```bash
python scripts/run_experiment.py
```

### Generate Plots
After running the experiment, generate visualization plots:

```bash
python scripts/generate_plots.py
```

The script generates:
- Precision curves for all objectives
- Stage-wise precision comparisons
- Best configurations tables (Stages 1-3)
- Stage 4 configurations by network complexity
- Top objectives bar charts at key thresholds

All plots are saved in `results/figures/`.

## Project Structure
```
├── configs/                    # Configuration files (.yaml)
│   ├── config.yaml             # Main configuration
│   ├── objectives.yaml         # Objectives and distributions
├── data/                       # datasets
│   ├── 5_sources/
│   ├── 10_sources/
│   ├── 20_sources/
├── results/                    # Generated outputs (populated after running)
│   └── .gitkeep                # (placeholder to keep empty folder in Git)
├── scripts/                    # Main executable scripts
│   ├── generate_plots.py
│   └── run_experiment.py
├── src/                        # Source code modules
│   ├── data/
│   │   ├── loader.py
│   │   ├── preprocessor.py
│   ├── evaluation/
│   │   └── metrics.py
│   ├── models/
│   │   └── inference.py
│   ├── pipeline/
│   │   └── stages.py
│   └── utils/
│       ├── config_manager.py
│       ├── logger.py
│       └── parallel.py
├── .gitignore
├── environment.yml
├── pyproject.toml
├── README.md
└── requirements.txt
```                  

## Output Structure
After running the pipeline, results are organized as:
```
results/
├── precision_metrics.csv           
├── GRN_Inference_RESULTS.csv       
└── figures/                        # Generated plots
    ├── precision_curves.pdf
    ├── precision_curves_stagewise.pdf
    ├── stages_1to3_configs.pdf
    ├── stage4_by_complexity.pdf
    └── top_objectives_bar.pdf
```
**Note:** The `.gitkeep` file is only to keep the empty folder in Git. It does not affect the pipeline and will remain after generating results.

## Large-Scale Datasets (For more experiment)

For users who want to run experiments with larger datasets, I have pre-simulated **approximately 1000 datasets** available on Google Drive (public access).

### How to Use

1. **Download** `simulated.zip` to your project folder:
```bash
# Install gdown if needed
pip install gdown
   
# Download directly to your project
gdown --fuzzy "https://drive.google.com/file/d/1Em-t7wTsmqDHLDAWIpidKYtdS-8chFBj/view?usp=drive_link"
```


2. **Extract** the datasets into the simulated folder:

Linux:
```
# Extract contents
unzip simulated.zip -d data/
```

Windows:
```
# Extract contents
tar -xf simulated.zip -C data/
```

3. **Verify** the datasets in data/simulated folder for 5, 10 and 20_sources. The structure should look like:
```
data/simulated/
├── 5_sources/
│   ├── data/
│   │   ├── data_1.tsv
│   │   └── ...
│   └── nets/
│       ├── network_1.tsv
│       └── ...
├── 10_sources/
└── 20_sources/
```

4. Manually edit configs/config.yaml to use the large datasets:
Open `configs/config.yaml` in any text editor (nano, vim, VSCode, Notepad, etc.) and change:

```yaml
# In configs/config.yaml
paths:
  base_data: "data/simulated"  # Change from "data" to "data/simulated"
```
5. **Configure** dataset complexities/counts manually to run by yourself:
In the same file, adjust how many datasets to use:

```yaml
# In configs/config.yaml
datasets:
  complexities:
    5_sources: 2   # Use first 2 datasets for 5_sources (Update as your need)
    10_sources: 2  # Use first 2 datasets for 10_sources (Update as your need)
    20_sources: 1  # Use first 1 datasets for 20_sources (Update as your need)
  max_search_trials: 50  # Must be updated as per your largest dataset number request per source like (e.g. 60 or 80)
```
When run, The pipeline reads datasets and automatically skips any missing indices and goes to next file.

6. **Run** the pipeline as usual:

```bash
python scripts/run_experiment.py
python scripts/generate_plots.py
```

## Configuration
Edit configs/config.yaml to modify:
- Data paths: Input data and output directories
- Model hyperparameters: Base parameters
- Pipeline settings: Batch size, thresholds

## Reproducibility
- All parameters stored in YAML configuration files
- Complete pipeline from data loading to visualization

## Requirements
- Python: 3.10 or higher
- Operating System: Windows/Linux/macOS

Main Python packages:
- pandas, numpy, scikit-learn
- xgboost, xgboost-distribution
- scanpy, matplotlib, seaborn
- pyyaml

