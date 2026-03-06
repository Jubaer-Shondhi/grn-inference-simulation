#!/usr/bin/env Rscript

#' Install required R packages for GRN simulation
#'
#' This script installs all necessary R packages for running the
#' GRN simulation pipeline.

install_dependencies <- function() {
 
  cat("========================================\n")
  cat("Installing R dependencies for GRN Simulation\n")
  cat("========================================\n\n")
 
  # ============================================
  # Set personal library path (for shared systems)
  # ============================================
  personal_lib <- Sys.getenv("R_LIBS_USER")
  if (personal_lib == "") {
    personal_lib <- file.path(Sys.getenv("HOME"), "R/library")
  }
  if (!file.exists(personal_lib)) {
    dir.create(personal_lib, recursive = TRUE)
  }
  .libPaths(c(personal_lib, .libPaths()))
  cat("Using personal library:", personal_lib, "\n")
 
  # Install BiocManager if needed
  if (!requireNamespace("BiocManager", quietly = TRUE)) {
    cat("\nInstalling BiocManager...\n")
    install.packages("BiocManager", lib = personal_lib, repos = "https://cloud.r-project.org")
  }
 
  # ============================================
  # Install all CRAN dependencies first
  # ============================================
  cat("\n========================================\n")
  cat("Installing CRAN dependencies...\n")
  cat("========================================\n")
 
  cran_deps <- c(
    "ape",           # For phytools
    "maps",          # For phytools
    "mnormt",        # For phytools  
    "numDeriv",      # For phytools
    "plotrix",       # For phytools
    "combinat",      # For phytools (critical - old version causes errors)
    "phytools",      # Needed for scMultiSim
    "data.table",    # For efficient data handling
    "dplyr",         # For data manipulation
    "ggplot2",       # For plotting
    "argparse",      # For command line arguments
    "reticulate"     # For Python integration
  )
 
  for (pkg in cran_deps) {
    if (!requireNamespace(pkg, quietly = TRUE)) {
      cat(sprintf("\nInstalling %s...\n", pkg))
      tryCatch({
        install.packages(pkg, lib = personal_lib, repos = "https://cloud.r-project.org", dependencies = TRUE)
        if (requireNamespace(pkg, quietly = TRUE)) {
          cat(sprintf("✓ %s installed successfully\n", pkg))
        } else {
          cat(sprintf("✗ %s installation failed\n", pkg))
        }
      }, error = function(e) {
        cat(sprintf("✗ Error installing %s: %s\n", pkg, e$message))
      })
    } else {
      cat(sprintf("✓ %s already installed\n", pkg))
    }
  }
 
  # ============================================
  # Install Bioconductor packages
  # ============================================
  cat("\n========================================\n")
  cat("Installing Bioconductor packages...\n")
  cat("========================================\n")
 
  bioc_packages <- c(
    "OmnipathR",     # For decoupleR
    "decoupleR",     # For CollectRI network
    "scMultiSim"     # For simulation
  )
 
  for (pkg in bioc_packages) {
    if (!requireNamespace(pkg, quietly = TRUE)) {
      cat(sprintf("\nInstalling %s...\n", pkg))
      tryCatch({
        BiocManager::install(pkg, lib = personal_lib, update = FALSE, ask = FALSE)
        if (requireNamespace(pkg, quietly = TRUE)) {
          cat(sprintf("✓ %s installed successfully\n", pkg))
        } else {
          cat(sprintf("✗ %s installation failed\n", pkg))
        }
      }, error = function(e) {
        cat(sprintf("✗ Error installing %s: %s\n", pkg, e$message))
      })
    } else {
      cat(sprintf("✓ %s already installed\n", pkg))
    }
  }
 
  # ============================================
  # Verify all installations
  # ============================================
  cat("\n========================================\n")
  cat("Verifying all packages...\n")
  cat("========================================\n")
 
  all_packages <- c(cran_deps, bioc_packages)
  installed <- c()
  failed <- c()
 
  for (pkg in all_packages) {
    if (requireNamespace(pkg, quietly = TRUE)) {
      cat(sprintf("✓ %s installed\n", pkg))
      installed <- c(installed, pkg)
    } else {
      cat(sprintf("✗ %s NOT installed\n", pkg))
      failed <- c(failed, pkg)
    }
  }
 
  # Print summary
  cat("\n\n========================================\n")
  cat("Installation Summary\n")
  cat("========================================\n")
  cat(sprintf("Successfully installed: %d packages\n", length(installed)))
  if (length(failed) > 0) {
    cat(sprintf("Failed to install: %d packages\n", length(failed)))
    cat("Failed packages: ", paste(failed, collapse = ", "), "\n")
  } else {
    cat("✓ All packages installed successfully!\n")
  }
 
  # Test CollectRI network loading
  cat("\n========================================\n")
  cat("Testing CollectRI network loading...\n")
  cat("========================================\n")
 
  if (requireNamespace("decoupleR", quietly = TRUE)) {
    tryCatch({
      collectri <- decoupleR::get_collectri()
      cat(sprintf("✓ CollectRI loaded successfully: %d edges\n", nrow(collectri)))
    }, error = function(e) {
      cat(sprintf("✗ Failed to load CollectRI: %s\n", e$message))
    })
  } else {
    cat("✗ Cannot test CollectRI: decoupleR not installed\n")
  }
 
  # Test scMultiSim
  cat("\nTesting scMultiSim...\n")
  if (requireNamespace("scMultiSim", quietly = TRUE)) {
    cat("✓ scMultiSim is available\n")
  } else {
    cat("✗ scMultiSim not available\n")
  }
 
  cat("\n========================================\n")
  cat("Installation complete!\n")
  cat("========================================\n")
 
  invisible(list(installed = installed, failed = failed))
}

# Run installation if script is executed directly
if (sys.nframe() == 0) {
  install_dependencies()
}
