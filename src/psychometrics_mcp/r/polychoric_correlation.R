#!/usr/bin/env Rscript

suppressPackageStartupMessages(library(jsonlite))
suppressPackageStartupMessages(library(psych))

payload <- fromJSON(file("stdin"), simplifyVector = FALSE)
x <- do.call(rbind, lapply(payload$values, unlist))
storage.mode(x) <- "numeric"
variable_names <- unlist(payload$variable_names)
colnames(x) <- variable_names
continuity_correction <- as.numeric(unlist(payload$continuity_correction)[[1]])

captured_warnings <- character()
fit <- withCallingHandlers(
  psych::polychoric(
    x,
    smooth = FALSE,
    global = FALSE,
    ML = FALSE,
    std.err = FALSE,
    correct = continuity_correction,
    progress = FALSE,
    na.rm = FALSE,
    delete = FALSE,
    max.cat = 10
  ),
  warning = function(value) {
    captured_warnings <<- c(captured_warnings, conditionMessage(value))
    invokeRestart("muffleWarning")
  }
)

rho <- as.matrix(fit$rho)
if (!all(dim(rho) == c(ncol(x), ncol(x))) || any(!is.finite(rho))) {
  stop("The polychoric correlation matrix was incomplete or non-finite.")
}
rownames(rho) <- variable_names
colnames(rho) <- variable_names
eigenvalues <- eigen(rho, symmetric = TRUE, only.values = TRUE)$values

correlations <- lapply(seq_len(nrow(rho)), function(index) {
  as.list(setNames(as.numeric(rho[index, ]), variable_names))
})

threshold_rows <- lapply(seq_along(variable_names), function(index) {
  categories <- sort(unique(x[, index]))
  counts <- tabulate(match(x[, index], categories), nbins = length(categories))
  cumulative <- cumsum(counts) / sum(counts)
  thresholds <- qnorm(cumulative[-length(cumulative)])
  list(
    variable = variable_names[[index]],
    thresholds = lapply(seq_along(thresholds), function(threshold_index) {
      list(
        lower_category = categories[[threshold_index]],
        upper_category = categories[[threshold_index + 1]],
        estimate = thresholds[[threshold_index]]
      )
    })
  )
})

boundary_pairs <- list()
for (first in seq_len(ncol(rho) - 1L)) {
  for (second in seq.int(first + 1L, ncol(rho))) {
    if (abs(rho[first, second]) >= 0.999) {
      boundary_pairs[[length(boundary_pairs) + 1L]] <- list(
        variable_1 = variable_names[[first]],
        variable_2 = variable_names[[second]],
        estimate = rho[first, second]
      )
    }
  }
}

result <- list(
  method = list(
    name = "Two-step polychoric correlation",
    engine = "psych::polychoric",
    latent_response_distribution = "bivariate normal",
    missing = "listwise",
    global_thresholds = FALSE,
    continuity_correction = continuity_correction,
    smoothing = FALSE
  ),
  variables = as.list(variable_names),
  correlations = correlations,
  thresholds = threshold_rows,
  diagnostics = list(
    positive_definite = min(eigenvalues) > 1e-10,
    minimum_eigenvalue = min(eigenvalues),
    eigenvalues = as.list(as.numeric(eigenvalues)),
    boundary_pairs = boundary_pairs
  ),
  package_versions = list(
    R = as.character(getRversion()),
    psych = as.character(packageVersion("psych")),
    jsonlite = as.character(packageVersion("jsonlite"))
  ),
  warnings = as.list(unique(captured_warnings))
)

cat(toJSON(result, auto_unbox = TRUE, null = "null", na = "null", digits = 15))
