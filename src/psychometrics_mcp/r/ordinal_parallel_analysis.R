#!/usr/bin/env Rscript

suppressPackageStartupMessages(library(jsonlite))
suppressPackageStartupMessages(library(psych))

payload <- fromJSON(file("stdin"), simplifyVector = FALSE)
x <- do.call(rbind, lapply(payload$values, unlist))
storage.mode(x) <- "numeric"
variable_names <- unlist(payload$variable_names)
colnames(x) <- variable_names
extraction <- as.character(unlist(payload$extraction)[[1]])
iterations <- as.integer(unlist(payload$iterations)[[1]])
percentile <- as.numeric(unlist(payload$percentile)[[1]])
seed <- as.integer(unlist(payload$seed)[[1]])
continuity_correction <- as.numeric(unlist(payload$continuity_correction)[[1]])

captured_warnings <- character()
capture_analysis <- function(expression) {
  withCallingHandlers(
    expression,
    warning = function(value) {
      captured_warnings <<- c(captured_warnings, conditionMessage(value))
      invokeRestart("muffleWarning")
    }
  )
}

validate_correlation <- function(value, label) {
  value <- as.matrix(value)
  if (!all(dim(value) == c(ncol(x), ncol(x))) || any(!is.finite(value))) {
    stop(paste(label, "correlation matrix was incomplete or non-finite."))
  }
  minimum_eigenvalue <- min(eigen(value, symmetric = TRUE, only.values = TRUE)$values)
  if (minimum_eigenvalue <= 1e-10) {
    stop(paste(label, "correlation matrix was not positive definite."))
  }
  value
}

polychoric_matrix <- function(value) {
  fit <- capture_analysis(
    psych::polychoric(
      value,
      smooth = FALSE,
      global = FALSE,
      ML = FALSE,
      std.err = FALSE,
      correct = continuity_correction,
      progress = FALSE,
      na.rm = FALSE,
      delete = FALSE,
      max.cat = 10
    )
  )
  validate_correlation(fit$rho, "Unsmoothed polychoric")
}

pearson_matrix <- function(value) {
  validate_correlation(stats::cor(value), "Pearson")
}

spectra <- function(correlation, label) {
  principal_components <- eigen(
    correlation,
    symmetric = TRUE,
    only.values = TRUE
  )$values
  factor_fit <- suppressWarnings(
    psych::fa(
      correlation,
      n.obs = nrow(x),
      nfactors = 1,
      rotate = "none",
      fm = extraction,
      SMC = FALSE,
      scores = "none",
      residuals = FALSE,
      warnings = FALSE
    )
  )
  common_factor <- as.numeric(factor_fit$values)
  if (length(common_factor) != ncol(x) || any(!is.finite(common_factor))) {
    stop(paste(label, "common-factor spectrum was incomplete or non-finite."))
  }
  list(principal_components = principal_components, common_factor = common_factor)
}

retained_before_first_crossing <- function(observed, reference) {
  comparisons <- observed > reference
  first_crossing <- which(!comparisons)
  if (length(first_crossing) == 0) length(comparisons) else first_crossing[[1]] - 1L
}

observed_polychoric <- polychoric_matrix(x)
observed_pearson <- pearson_matrix(x)
observed <- list(
  polychoric = spectra(observed_polychoric, "Observed polychoric"),
  pearson = spectra(observed_pearson, "Observed Pearson")
)

set.seed(seed)
reference <- list(
  polychoric_principal_components = matrix(NA_real_, nrow = iterations, ncol = ncol(x)),
  polychoric_common_factor = matrix(NA_real_, nrow = iterations, ncol = ncol(x)),
  pearson_principal_components = matrix(NA_real_, nrow = iterations, ncol = ncol(x)),
  pearson_common_factor = matrix(NA_real_, nrow = iterations, ncol = ncol(x))
)
successful <- 0L
attempted <- 0L
maximum_attempts <- iterations * 3L
failure_reasons <- character()

while (successful < iterations && attempted < maximum_attempts) {
  attempted <- attempted + 1L
  permuted <- vapply(
    seq_len(ncol(x)),
    function(index) sample(x[, index], size = nrow(x), replace = FALSE),
    numeric(nrow(x))
  )
  attempt <- tryCatch(
    {
      polychoric <- polychoric_matrix(permuted)
      pearson <- pearson_matrix(permuted)
      list(
        polychoric = spectra(polychoric, "Permuted polychoric"),
        pearson = spectra(pearson, "Permuted Pearson")
      )
    },
    error = function(value) value
  )
  if (inherits(attempt, "error")) {
    failure_reasons <- c(failure_reasons, conditionMessage(attempt))
    next
  }
  successful <- successful + 1L
  reference$polychoric_principal_components[successful, ] <-
    attempt$polychoric$principal_components
  reference$polychoric_common_factor[successful, ] <- attempt$polychoric$common_factor
  reference$pearson_principal_components[successful, ] <-
    attempt$pearson$principal_components
  reference$pearson_common_factor[successful, ] <- attempt$pearson$common_factor
}

if (successful < iterations) {
  reason_table <- sort(table(failure_reasons), decreasing = TRUE)
  reason_text <- if (length(reason_table)) names(reason_table)[[1]] else "unknown failure"
  stop(
    paste0(
      "Only ", successful, " of ", iterations,
      " valid unsmoothed permutation references were obtained in ", attempted,
      " attempts. Most frequent failure: ", reason_text
    )
  )
}

reference_summary <- lapply(reference, function(value) {
  list(
    mean = colMeans(value),
    percentile = apply(value, 2, stats::quantile, probs = percentile, names = FALSE)
  )
})

configurations <- list(
  list("polychoric", "principal_components", "mean"),
  list("polychoric", "principal_components", "percentile"),
  list("polychoric", "common_factor", "mean"),
  list("polychoric", "common_factor", "percentile"),
  list("pearson", "principal_components", "mean"),
  list("pearson", "principal_components", "percentile"),
  list("pearson", "common_factor", "mean"),
  list("pearson", "common_factor", "percentile")
)

sensitivity_results <- lapply(configurations, function(configuration) {
  correlation <- configuration[[1]]
  spectrum <- configuration[[2]]
  cutoff <- configuration[[3]]
  observed_values <- observed[[correlation]][[spectrum]]
  reference_key <- paste(correlation, spectrum, sep = "_")
  reference_values <- reference_summary[[reference_key]][[cutoff]]
  list(
    correlation = correlation,
    spectrum = if (spectrum == "common_factor") paste0("common_factor_", extraction) else spectrum,
    cutoff = cutoff,
    cutoff_probability = if (cutoff == "percentile") percentile else NULL,
    suggested_factors = retained_before_first_crossing(observed_values, reference_values),
    decision_rule = "retain consecutive leading roots until the first observed <= reference root"
  )
})

primary <- sensitivity_results[[1]]
suggestions <- vapply(sensitivity_results, function(value) value$suggested_factors, integer(1))
if (length(unique(suggestions)) > 1) {
  captured_warnings <- c(
    captured_warnings,
    paste0(
      "Retention sensitivity variants disagree (range ", min(suggestions), "-",
      max(suggestions), "); do not treat the primary suggestion as definitive."
    )
  )
}
if (attempted > iterations) {
  captured_warnings <- c(
    captured_warnings,
    paste0(
      attempted - iterations,
      " permutation draws were rejected because an unsmoothed correlation or spectrum was invalid."
    )
  )
}
if (primary$suggested_factors == ncol(x)) {
  captured_warnings <- c(
    captured_warnings,
    "Every primary-spectrum root exceeded its reference; the suggested count is not fit-able by the fixed EFA tool."
  )
}

eigenvalue_rows <- lapply(seq_len(ncol(x)), function(index) {
  list(
    root = index,
    observed = list(
      polychoric_principal_components = observed$polychoric$principal_components[[index]],
      polychoric_common_factor = observed$polychoric$common_factor[[index]],
      pearson_principal_components = observed$pearson$principal_components[[index]],
      pearson_common_factor = observed$pearson$common_factor[[index]]
    ),
    permutation_mean = list(
      polychoric_principal_components =
        reference_summary$polychoric_principal_components$mean[[index]],
      polychoric_common_factor = reference_summary$polychoric_common_factor$mean[[index]],
      pearson_principal_components =
        reference_summary$pearson_principal_components$mean[[index]],
      pearson_common_factor = reference_summary$pearson_common_factor$mean[[index]]
    ),
    permutation_percentile = list(
      probability = percentile,
      polychoric_principal_components =
        reference_summary$polychoric_principal_components$percentile[[index]],
      polychoric_common_factor =
        reference_summary$polychoric_common_factor$percentile[[index]],
      pearson_principal_components =
        reference_summary$pearson_principal_components$percentile[[index]],
      pearson_common_factor =
        reference_summary$pearson_common_factor$percentile[[index]]
    )
  )
})

failure_counts <- if (length(failure_reasons)) {
  reason_table <- sort(table(failure_reasons), decreasing = TRUE)
  lapply(seq_along(reason_table), function(index) {
    list(reason = names(reason_table)[[index]], count = unname(reason_table[[index]]))
  })
} else {
  list()
}

result <- list(
  method = list(
    name = "Ordinal permutation parallel analysis with sensitivity variants",
    engine = "psych::polychoric + psych::fa + base R eigen",
    primary_correlation = "unsmoothed two-step polychoric",
    primary_spectrum = "principal components",
    primary_cutoff = "mean",
    sensitivity_correlations = list("polychoric", "pearson"),
    sensitivity_spectra = list("principal_components", paste0("common_factor_", extraction)),
    sensitivity_cutoffs = list("mean", "requested_percentile"),
    reference_generation = paste(
      "independent within-column permutation without replacement; exact observed ordinal",
      "margins are preserved and cross-variable associations are broken"
    ),
    exact_univariate_margins_preserved = TRUE,
    smoothing = FALSE,
    missing = "listwise",
    continuity_correction = continuity_correction,
    common_factor_extraction = extraction,
    percentile = percentile,
    seed = seed
  ),
  suggested_factors = primary$suggested_factors,
  primary_suggestion = primary,
  sensitivity_results = sensitivity_results,
  eigenvalues = eigenvalue_rows,
  simulation = list(
    requested_iterations = iterations,
    successful_iterations = successful,
    attempted_iterations = attempted,
    rejected_iterations = attempted - successful,
    maximum_attempts = maximum_attempts,
    rejection_reasons = failure_counts
  ),
  diagnostics = list(
    observed_polychoric_positive_definite = TRUE,
    permutation_margins_preserved_by_construction = TRUE,
    minimum_observed_polychoric_eigenvalue = min(
      eigen(observed_polychoric, symmetric = TRUE, only.values = TRUE)$values
    ),
    sensitivity_minimum = min(suggestions),
    sensitivity_maximum = max(suggestions),
    sensitivity_agreement = length(unique(suggestions)) == 1
  ),
  package_versions = list(
    R = as.character(getRversion()),
    psych = as.character(packageVersion("psych")),
    jsonlite = as.character(packageVersion("jsonlite"))
  ),
  warnings = as.list(unique(captured_warnings))
)

cat(toJSON(result, auto_unbox = TRUE, null = "null", na = "null", digits = 15))
