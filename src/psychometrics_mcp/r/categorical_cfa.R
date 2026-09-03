#!/usr/bin/env Rscript

suppressPackageStartupMessages(library(jsonlite))
suppressPackageStartupMessages(library(lavaan))

payload <- fromJSON(file("stdin"), simplifyVector = FALSE)
x <- do.call(rbind, lapply(payload$values, unlist))
storage.mode(x) <- "numeric"
indicator_ids <- unlist(payload$indicator_ids)
indicator_names <- unlist(payload$indicator_names)
colnames(x) <- indicator_ids

factor_ids <- vapply(payload$factors, function(value) value$id, character(1))
factor_names <- vapply(payload$factors, function(value) value$name, character(1))
factor_name_map <- setNames(factor_names, factor_ids)
indicator_name_map <- setNames(indicator_names, indicator_ids)
category_map <- setNames(
  lapply(payload$category_values, function(value) as.numeric(unlist(value))),
  indicator_ids
)

data <- as.data.frame(x)
for (indicator in indicator_ids) {
  data[[indicator]] <- ordered(data[[indicator]], levels = category_map[[indicator]])
}

model_lines <- vapply(payload$factors, function(value) {
  paste(value$id, "=~", paste(unlist(value$indicators), collapse = " + "))
}, character(1))
model_syntax <- paste(model_lines, collapse = "\n")

captured_warnings <- character()
fit <- withCallingHandlers(
  cfa(
    model = model_syntax,
    data = data,
    ordered = indicator_ids,
    estimator = "WLSMV",
    std.lv = TRUE,
    parameterization = "delta",
    missing = "listwise"
  ),
  warning = function(value) {
    captured_warnings <<- c(captured_warnings, conditionMessage(value))
    invokeRestart("muffleWarning")
  }
)

parameters <- parameterEstimates(
  fit,
  standardized = TRUE,
  ci = TRUE,
  level = as.numeric(unlist(payload$confidence_level)[[1]])
)

nullable <- function(value) {
  if (length(value) == 0 || is.na(value[[1]]) || !is.finite(value[[1]])) NULL else unname(value[[1]])
}

mapped_name <- function(value) {
  if (value %in% names(factor_name_map)) return(factor_name_map[[value]])
  if (value %in% names(indicator_name_map)) return(indicator_name_map[[value]])
  value
}

parameter_row <- function(row) {
  list(
    lhs = mapped_name(row$lhs),
    operator = row$op,
    rhs = mapped_name(row$rhs),
    estimate = nullable(row$est),
    standard_error = nullable(row$se),
    z_statistic = nullable(row$z),
    p_value = nullable(row$pvalue),
    confidence_interval_lower = nullable(row$ci.lower),
    confidence_interval_upper = nullable(row$ci.upper),
    standardized_estimate = nullable(row$std.all)
  )
}

loadings_frame <- parameters[parameters$op == "=~", , drop = FALSE]
loading_rows <- lapply(seq_len(nrow(loadings_frame)), function(index) {
  parameter_row(loadings_frame[index, , drop = FALSE])
})

threshold_frame <- parameters[parameters$op == "|", , drop = FALSE]
threshold_rows <- lapply(seq_len(nrow(threshold_frame)), function(index) {
  row <- threshold_frame[index, , drop = FALSE]
  threshold_index <- as.integer(sub("^t", "", row$rhs))
  categories <- category_map[[row$lhs]]
  list(
    variable = indicator_name_map[[row$lhs]],
    threshold = row$rhs,
    lower_category = categories[[threshold_index]],
    upper_category = categories[[threshold_index + 1L]],
    estimate = nullable(row$est),
    standard_error = nullable(row$se),
    z_statistic = nullable(row$z),
    p_value = nullable(row$pvalue),
    confidence_interval_lower = nullable(row$ci.lower),
    confidence_interval_upper = nullable(row$ci.upper)
  )
})

factor_covariance_frame <- parameters[
  parameters$op == "~~" & parameters$lhs %in% factor_ids &
    parameters$rhs %in% factor_ids & parameters$lhs != parameters$rhs,
  ,
  drop = FALSE
]
factor_covariance_rows <- lapply(seq_len(nrow(factor_covariance_frame)), function(index) {
  parameter_row(factor_covariance_frame[index, , drop = FALSE])
})

residual_frame <- parameters[
  parameters$op == "~~" & parameters$lhs %in% indicator_ids &
    parameters$lhs == parameters$rhs,
  ,
  drop = FALSE
]
residual_rows <- lapply(seq_len(nrow(residual_frame)), function(index) {
  parameter_row(residual_frame[index, , drop = FALSE])
})

measures <- fitMeasures(fit)
measure <- function(name) {
  if (name %in% names(measures)) nullable(measures[[name]]) else NULL
}
theta <- as.matrix(lavInspect(fit, "theta"))
latent_covariance <- as.matrix(lavInspect(fit, "cov.lv"))
latent_eigenvalues <- eigen(latent_covariance, symmetric = TRUE, only.values = TRUE)$values

result <- list(
  model = list(
    name = "Categorical confirmatory factor analysis",
    engine = "lavaan::cfa",
    requested_estimator = "WLSMV",
    estimation = "diagonally weighted least squares",
    standard_errors = "robust",
    test_statistic = "mean- and variance-adjusted",
    link = "probit latent response",
    parameterization = "delta",
    identification = "latent variances fixed to 1 (std.lv = TRUE)",
    missing = "listwise",
    converged = isTRUE(lavInspect(fit, "converged")),
    post_check = isTRUE(lavInspect(fit, "post.check")),
    free_parameters = unname(lavInspect(fit, "npar")),
    degrees_of_freedom = measure("df.scaled")
  ),
  fit = list(
    standard = list(
      chi_square = measure("chisq"),
      degrees_of_freedom = measure("df"),
      p_value = measure("pvalue"),
      cfi = measure("cfi"),
      tli = measure("tli"),
      rmsea = measure("rmsea"),
      rmsea_ci_lower = measure("rmsea.ci.lower"),
      rmsea_ci_upper = measure("rmsea.ci.upper")
    ),
    robust_scaled = list(
      chi_square = measure("chisq.scaled"),
      degrees_of_freedom = measure("df.scaled"),
      p_value = measure("pvalue.scaled"),
      cfi = measure("cfi.scaled"),
      tli = measure("tli.scaled"),
      rmsea = measure("rmsea.scaled"),
      rmsea_ci_lower = measure("rmsea.ci.lower.scaled"),
      rmsea_ci_upper = measure("rmsea.ci.upper.scaled"),
      cfi_robust = measure("cfi.robust"),
      tli_robust = measure("tli.robust"),
      rmsea_robust = measure("rmsea.robust")
    ),
    srmr = measure("srmr")
  ),
  diagnostics = list(
    minimum_residual_variance = min(diag(theta)),
    latent_covariance_positive_definite = min(latent_eigenvalues) > 1e-10,
    minimum_latent_covariance_eigenvalue = min(latent_eigenvalues)
  ),
  loadings = loading_rows,
  thresholds = threshold_rows,
  factor_covariances = factor_covariance_rows,
  residual_variances = residual_rows,
  package_versions = list(
    R = as.character(getRversion()),
    lavaan = as.character(packageVersion("lavaan")),
    jsonlite = as.character(packageVersion("jsonlite"))
  ),
  warnings = as.list(unique(captured_warnings))
)

cat(toJSON(result, auto_unbox = TRUE, null = "null", na = "null", digits = 15))
