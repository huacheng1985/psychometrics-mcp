#!/usr/bin/env Rscript
# Install into a task-owned library; never replace the system R library.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1) stop("Supply the isolated target library path.")
target <- args[[1]]
dir.create(target, recursive = TRUE, showWarnings = FALSE)
target <- normalizePath(target, mustWork = TRUE)
.libPaths(c(target, .libPaths()))
Sys.setenv(R_LIBS = paste(.libPaths(), collapse = .Platform$path.sep))
versions <- c(lavaan = "0.7-2", semTools = "0.5-9")
for (package in names(versions)) {
  version <- versions[[package]]
  filename <- paste0(package, "_", version, ".tar.gz")
  destination <- tempfile(fileext = ".tar.gz")
  urls <- c(paste0("https://cloud.r-project.org/src/contrib/", filename),
            paste0("https://cloud.r-project.org/src/contrib/Archive/", package, "/", filename))
  downloaded <- FALSE
  for (url in urls) {
    downloaded <- tryCatch({download.file(url, destination, mode = "wb"); TRUE}, error = function(e) FALSE)
    if (downloaded) break
  }
  if (!downloaded) stop(paste("Unable to download", package, version))
  install.packages(destination, lib = target, repos = NULL, type = "source")
  installed <- as.character(packageVersion(package, lib.loc = target))
  if (package_version(installed) != package_version(version)) stop("Installed version mismatch.")
}
cat("Isolated ordinal invariance dependencies installed in", target, "\n")
