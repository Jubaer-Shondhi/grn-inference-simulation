#!/usr/bin/env Rscript

# Load required libraries
suppressPackageStartupMessages({
  library(decoupleR)
  library(scMultiSim)
  library(data.table)
  library(ggplot2)
  library(dplyr)
  library(argparse)
  library(reticulate)
})

# # ============================================
# # FIX: Set Python path for reticulate
# # ============================================
# Sys.setenv(PYTHON = "C:/Users/Jubaer Shondhi/anaconda3/envs/grn_env/python.exe")
# Sys.setenv(RETICULATE_PYTHON = "C:/Users/Jubaer Shondhi/anaconda3/envs/grn_env/python.exe")
# reticulate::use_python("C:/Users/Jubaer Shondhi/anaconda3/envs/grn_env/python.exe", required = TRUE)
# cat("Python path:", reticulate::py_config()$python, "\n")

# ============================================
# Set Python path for reticulate - DYNAMIC
# ============================================
# Try to find Python in common locations
python_paths <- c(
  Sys.which("python"),                    # System Python
  "python",                                # Default command
  Sys.getenv("PYTHON"),                    # Environment variable
  Sys.getenv("RETICULATE_PYTHON")          # Reticulate environment variable
)

python_paths <- python_paths[python_paths != ""]

if (length(python_paths) > 0) {
  # Use the first valid Python
  python_path <- python_paths[1]
  Sys.setenv(PYTHON = python_path)
  Sys.setenv(RETICULATE_PYTHON = python_path)
  reticulate::use_python(python_path, required = TRUE)
  cat("Using Python:", python_path, "\n")
} else {
  cat("WARNING: No Python found. Using reticulate default.\n")
}

personal_lib <- "~/R/library"
if (dir.exists(personal_lib)) {
  .libPaths(c(personal_lib, .libPaths()))
  cat("Using R library:", personal_lib, "\n")
}

#' Subsample and sparsify a regulatory network
#'
#' @param network Original network data.table
#' @param num_sources Number of source nodes to sample
#' @param max_out_degree Maximum outgoing connections per source
#' @return Subsample and sparsified network
subsample_and_sparsify_network <- function(network, num_sources, max_out_degree) {
 
  network_dt <- as.data.table(network)
  all_sources <- unique(network_dt$source)
 
  message("DEBUG - Total sources in network: ", length(all_sources))
 
  if (length(all_sources) < num_sources) {
    stop(sprintf("Not enough unique source nodes: need %d, have %d",
                 num_sources, length(all_sources)))
  }
 
  sampled_sources <- sample(all_sources, num_sources, replace = FALSE)
  message("DEBUG - Sampled sources: ", paste(sampled_sources, collapse=", "))
 
  subnetwork <- network_dt[source %in% sampled_sources]
  message("DEBUG - subnetwork before sparsify: ", nrow(subnetwork), " edges")
 
  sparsified_subnetwork <- subnetwork %>%
    group_by(source) %>%
    slice_head(n = max_out_degree) %>%
    ungroup() %>%
    as.data.table()
 
  message("DEBUG - after sparsify: ", nrow(sparsified_subnetwork), " edges")
 
  sparsified_subnetwork <- sparsified_subnetwork[!(source %in% sparsified_subnetwork$target)]
  message("DEBUG - after removing self-loops: ", nrow(sparsified_subnetwork), " edges")
 
  return(sparsified_subnetwork)
}

#' Simulate gene expression data using scMultiSim
#'
#' @param network GRN network
#' @param n_cells Number of cells to simulate
#' @param sim_params Additional simulation parameters
#' @return Simulation results or NULL if failed
simulate_expression_data <- function(network, n_cells, sim_params) {
 
  # Prepare simulation parameters
  params <- list(
    GRN = network,
    tree = Phyla1(),  # Single cluster
    num.cells = n_cells,
    num.cif = sim_params$num.cif,
    discrete.cif = sim_params$discrete.cif,
    cif.sigma = sim_params$cif.sigma,
    speed.up = sim_params$speed.up,
    diff.cif.fraction = sim_params$diff.cif.fraction,
    unregulated.gene.ratio = sim_params$unregulated.gene.ratio,
    do.velocity = sim_params$do.velocity,
    intrinsic.noise = sim_params$intrinsic.noise
  )
 
  # Run simulation with error handling
  results <- tryCatch({
    sim_results <- sim_true_counts(params)
    return(sim_results)
  }, error = function(e) {
    message("Simulation failed: ", e$message)
    return(NULL)
  })
 
  return(results)
}

#' Save simulation results to files
#'
#' @param results Simulation results
#' @param output_dir Output directory
#' @param dataset_index Dataset index
#' @param generate_plots Whether to generate t-SNE plots
#' @return List of saved file paths
save_simulation_results <- function(results, output_dir, dataset_index, generate_plots = TRUE) {
 
  # DEBUG LINE
  message("\n>>> DEBUG - save_simulation_results received output_dir: ", output_dir)
 
  # Create directories
  network_dir <- file.path(output_dir, "nets")
  data_dir <- file.path(output_dir, "data")
  plots_dir <- file.path(output_dir, "plots")
 
  dir.create(network_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(data_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(plots_dir, recursive = TRUE, showWarnings = FALSE)
 
  saved_files <- list()
 
  # ============================================
  # Save network - Use original network if available
  # ============================================
  network_file <- file.path(network_dir, paste0("network_", dataset_index, ".tsv"))
 
  # First check if we have the original network (which we know has correct format)
  if (!is.null(results$original_network)) {
    message("DEBUG - Using original_network with ", nrow(results$original_network), " edges")
    network_dt <- as.data.table(results$original_network)
   
    # Make sure it has source and target columns
    if (all(c("source", "target") %in% colnames(network_dt))) {
      network_dt <- network_dt[, .(source, target)]
      message("DEBUG - Using source and target columns")
    } else {
      # If not, use first two columns
      message("DEBUG - Source/target columns not found, using first two columns")
      network_dt <- network_dt[, 1:2]
      setnames(network_dt, c("source", "target"))
    }
   
  } else {
    # Fall back to trying to find GRN in results
    message("DEBUG - No original_network, trying to find GRN in results")
   
    # Try to find GRN data in various possible locations
    grn_data <- NULL
    if (!is.null(results$GRN)) {
      grn_data <- results$GRN
      message("DEBUG - Found GRN in results$GRN")
    } else if (!is.null(results$network)) {
      grn_data <- results$network
      message("DEBUG - Found GRN in results$network")
    } else if (!is.null(results$edges)) {
      grn_data <- results$edges
      message("DEBUG - Found GRN in results$edges")
    }
   
    if (!is.null(grn_data)) {
      message("DEBUG - GRN class: ", class(grn_data))
     
      # Convert to data.table
      if (is.data.frame(grn_data)) {
        network_dt <- as.data.table(grn_data)
        # Try to find source/target columns
        if (all(c("source", "target") %in% colnames(network_dt))) {
          network_dt <- network_dt[, .(source, target)]
        } else {
          network_dt <- network_dt[, 1:2]
          setnames(network_dt, c("source", "target"))
        }
      } else if (is.matrix(grn_data)) {
        network_dt <- as.data.table(as.data.frame(grn_data))[, 1:2]
        setnames(network_dt, c("source", "target"))
      } else {
        message("  WARNING: Unknown GRN format")
        network_dt <- data.table(source = character(), target = character())
      }
    } else {
      message("  WARNING: No network data found anywhere!")
      network_dt <- data.table(source = character(), target = character())
    }
  }
 
  # Clean the data - remove invalid rows
  network_dt <- network_dt[!is.na(target) & target != ""]
  network_dt <- network_dt[!is.na(source) & source != ""]
  network_dt <- network_dt[source != target]
 
  message("DEBUG - Final network has ", nrow(network_dt), " edges")
  if (nrow(network_dt) > 0) {
    message("DEBUG - First few edges:")
    print(head(network_dt))
  } else {
    message("  WARNING: Network has 0 edges after cleaning!")
  }
 
  # Save the file
  fwrite(network_dt, network_file, sep = '\t')
  saved_files$network <- network_file
  message(sprintf("  Network saved: %s with %d edges", basename(network_file), nrow(network_dt)))
 
  # ============================================
  # Save expression data
  # ============================================
  if (!is.null(results$counts)) {
    gex_data <- as.data.table(results$counts, keep.rownames = "gene")
    setcolorder(gex_data, c("gene", colnames(results$counts)))
    data_file <- file.path(data_dir, paste0("data_", dataset_index, ".tsv"))
    fwrite(gex_data, file = data_file, sep = '\t', row.names = FALSE)
    saved_files$data <- data_file
    message(sprintf("  Data saved: %s with %d genes and %d cells",
                    basename(data_file), nrow(gex_data), ncol(gex_data)-1))
  } else {
    message("  WARNING: No expression data to save")
  }
 
  # ============================================
  # Generate and save t-SNE plot if requested
  # ============================================
  if (generate_plots && !is.null(results$counts) && !is.null(results$cell_meta)) {
    tryCatch({
      plot_file <- file.path(plots_dir, paste0("data_", dataset_index, "_plot.pdf"))
      plot_data <- plot_tsne(results$counts, results$cell_meta$pop) +
        theme_bw() +
        xlab('TSNE1') +
        ylab('TSNE2') +
        ggtitle(sprintf("Dataset %d - t-SNE Visualization", dataset_index))
     
      ggsave(plot_data, file = plot_file, height = 15, width = 16, units = 'cm')
      saved_files$plot <- plot_file
      message(sprintf("  Plot saved: %s", basename(plot_file)))
    }, error = function(e) {
      message("  Warning: Could not generate t-SNE plot: ", e$message)
    })
  }
 
  return(saved_files)
}

#' Create multiple simulated datasets
#'
#' @param collectri_net CollectRI network
#' @param outpath Output directory path
#' @param num_sources Number of sources to sample
#' @param max_out_degree Maximum outgoing connections
#' @param n_datasets Number of datasets to generate
#' @param n_cells Number of cells per dataset
#' @param mor_mean Mean for MOR values
#' @param mor_sd Standard deviation for MOR values
#' @param sim_params Additional simulation parameters
#' @param generate_plots Whether to generate plots
#' @param seed Random seed
#' @return List of results
create_datasets <- function(collectri_net,
                            outpath,
                            num_sources = 5,
                            max_out_degree = 20,
                            n_datasets = 10,
                            n_cells = 1000,
                            mor_mean = 5,
                            mor_sd = 1,
                            sim_params = NULL,
                            generate_plots = TRUE,
                            seed = 42) {
 
  # DEBUG LINE
  message("\n>>> DEBUG - create_datasets received outpath: ", outpath)
 
  # Set seed for reproducibility
  set.seed(seed)
 
  # Default simulation parameters
  default_sim_params <- list(
    num.cif = 40,
    discrete.cif = TRUE,
    cif.sigma = 0.25,
    speed.up = TRUE,
    diff.cif.fraction = 0.05,
    unregulated.gene.ratio = 0.05,
    do.velocity = FALSE,
    intrinsic.noise = 1.0
  )
 
  # Merge with user parameters
  if (is.null(sim_params)) {
    sim_params <- default_sim_params
  } else {
    sim_params <- modifyList(default_sim_params, sim_params)
  }
 
  message(sprintf("\nGenerating %d datasets with %d sources, %d cells each",
                  n_datasets, num_sources, n_cells))
  message("Output directory: ", outpath)
 
  # Create main output directory
  dir.create(outpath, recursive = TRUE, showWarnings = FALSE)
 
  successful <- 0
  failed <- 0
  all_results <- list()
 
  for (i in 1:n_datasets) {
    message(sprintf("\n[%d/%d] Generating dataset...", i, n_datasets))
   
    # Step 1: Subsample network
    net_sub <- subsample_and_sparsify_network(
      network = collectri_net,
      num_sources = num_sources,
      max_out_degree = max_out_degree
    )

    message("DEBUG - net_sub has ", nrow(net_sub), " rows")
   
    # Check if network has edges
    if(nrow(net_sub) > 0) {
      message("DEBUG - First few rows of net_sub:")
      print(head(net_sub))
     
      # Step 2: Add MOR values (ONLY if network not empty)
      net_sub$mor <- rnorm(nrow(net_sub), mean = mor_mean, sd = mor_sd)
      net_sub <- as.data.table(net_sub)
     
      # Step 3: Simulate expression data (ONLY if network not empty)
      results <- simulate_expression_data(net_sub, n_cells, sim_params)
     
    } else {
      message("DEBUG - WARNING: net_sub is EMPTY! Skipping this dataset")
      results <- NULL
    }
   
    if (is.null(results)) {
      message(sprintf("  ✗ Dataset %d failed", i))
      failed <- failed + 1
      next
    }
   
    # Step 4: Save results - BUT use the original network we created
    # Create a modified results object that includes our original network
    results_with_network <- results
    results_with_network$original_network <- net_sub
   
    saved_files <- save_simulation_results(
      results = results_with_network,
      output_dir = outpath,
      dataset_index = i,
      generate_plots = generate_plots
    )
   
    all_results[[i]] <- list(
      index = i,
      network = net_sub,
      results = results,
      files = saved_files
    )
   
    successful <- successful + 1
    message(sprintf("  ✓ Dataset %d completed", i))
  }
 
  # Save summary
  summary <- data.frame(
    parameter = c("num_sources", "max_out_degree", "n_datasets", "n_cells",
                  "successful", "failed", "seed"),
    value = c(num_sources, max_out_degree, n_datasets, n_cells,
              successful, failed, seed)
  )
 
  summary_file <- file.path(outpath, "simulation_metadata.csv")
  fwrite(summary, summary_file)
  message(sprintf("\nSimulation complete: %d successful, %d failed", successful, failed))
  message(sprintf("Metadata saved to: %s", summary_file))
 
  return(invisible(list(
    successful = successful,
    failed = failed,
    results = all_results,
    metadata_file = summary_file
  )))
}

#' Main function
main <- function(args) {
 
  message("\n========================================")
  message("GRN Data Simulation")
  message("========================================\n")
 
  # Load CollectRI network
  message("Loading CollectRI network...")
  collectri <- decoupleR::get_collectri()
  message(sprintf("CollectRI loaded: %d edges", nrow(collectri)))
 
  # Parse simulation parameters
  sim_params <- list(
    num.cif = args$num_cif,
    discrete.cif = args$discrete_cif,
    cif.sigma = args$cif_sigma,
    speed.up = args$speed_up,
    diff.cif.fraction = args$diff_cif_fraction,
    unregulated.gene.ratio = args$unregulated_gene_ratio,
    do.velocity = args$do_velocity,
    intrinsic.noise = args$intrinsic_noise
  )
 
  # DEBUG BLOCK
  message("\n========================================")
  message("DEBUG - args$output_dir: ", args$output_dir)
  message("========================================\n")
 
  # Generate datasets
  result <- create_datasets(
    collectri_net = collectri,
    outpath = args$output_dir,
    num_sources = args$num_sources,
    max_out_degree = args$max_out_degree,
    n_datasets = args$n_datasets,
    n_cells = args$n_cells,
    mor_mean = args$mor_mean,
    mor_sd = args$mor_sd,
    sim_params = sim_params,
    generate_plots = args$generate_plots,
    seed = args$seed
  )
 
  message("\n========================================")
  message("Simulation finished successfully!")
  message("========================================")
}

# Parse command line arguments
if (sys.nframe() == 0) {
 
  parser <- ArgumentParser(description = 'Generate simulated GRN data')
 
  # Required arguments
  parser$add_argument('--output_dir', type = "character", required = TRUE,
                      help = 'Output directory')
  parser$add_argument('--num_sources', type = "integer", required = TRUE,
                      help = 'Number of source nodes')
  parser$add_argument('--max_out_degree', type = "integer", required = TRUE,
                      help = 'Maximum outgoing connections')
 
  # Optional arguments with defaults
  parser$add_argument('--n_datasets', type = "integer", default = 10,
                      help = 'Number of datasets to generate [default: %(default)s]')
  parser$add_argument('--n_cells', type = "integer", default = 500,
                      help = 'Number of cells per dataset [default: %(default)s]')
  parser$add_argument('--mor_mean', type = "double", default = 5,
                      help = 'Mean for MOR values [default: %(default)s]')
  parser$add_argument('--mor_sd', type = "double", default = 1,
                      help = 'Standard deviation for MOR values [default: %(default)s]')
  parser$add_argument('--seed', type = "integer", default = 42,
                      help = 'Random seed [default: %(default)s]')
  parser$add_argument('--generate_plots', type = "logical", default = TRUE,
                      help = 'Generate t-SNE plots [default: %(default)s]')
 
  # Simulation parameters
  parser$add_argument('--num_cif', type = "integer", default = 40,
                      help = 'Number of CIFs [default: %(default)s]')
  parser$add_argument('--discrete_cif', type = "logical", default = TRUE,
                      help = 'Discrete CIFs [default: %(default)s]')
  parser$add_argument('--cif_sigma', type = "double", default = 0.25,
                      help = 'CIF sigma [default: %(default)s]')
  parser$add_argument('--speed_up', type = "logical", default = TRUE,
                      help = 'Speed up simulation [default: %(default)s]')
  parser$add_argument('--diff_cif_fraction', type = "double", default = 0.05,
                      help = 'Differential CIF fraction [default: %(default)s]')
  parser$add_argument('--unregulated_gene_ratio', type = "double", default = 0.05,
                      help = 'Unregulated gene ratio [default: %(default)s]')
  parser$add_argument('--do_velocity', type = "logical", default = FALSE,
                      help = 'Do velocity [default: %(default)s]')
  parser$add_argument('--intrinsic_noise', type = "double", default = 1.0,
                      help = 'Intrinsic noise [default: %(default)s]')
 
  args <- parser$parse_args()
 
  main(args)
}

