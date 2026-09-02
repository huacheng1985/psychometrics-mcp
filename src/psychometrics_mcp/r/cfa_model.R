#!/usr/bin/env Rscript

suppressPackageStartupMessages(library(jsonlite))
suppressPackageStartupMessages(library(lavaan))

payload <- fromJSON(file("stdin"), simplifyVector = FALSE)
x <- do.call(rbind, lapply(payload$values, unlist))
storage.mode(x) <- "numeric"
colnames(x) <- unlist(payload$indicator_ids)

factor_ids <- vapply(payload$factors, function(value) value$id, character(1))
factor_names <- vapply(payload$factors, function(value) value$name, character(1))
indicator_ids <- unlist(payload$indicator_ids)
indicator_names <- unlist(payload$indicator_names)
factor_name_map <- setNames(factor_names, factor_ids)
indicator_name_map <- setNames(indicator_names, indicator_ids)

model_lines <- vapply(payload$factors, function(value) {
  paste(value$id, "=~", paste(unlist(value$indicators), collapse = " + "))
}, character(1))
model_syntax <- paste(model_lines, collapse = "\n")

captured_warnings <- character()
fit <- withCallingHandlers(
  cfa(
    model = model_syntax,
    data = as.data.frame(x),
    estimator = payload$estimator,
    std.lv = TRUE,
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
  level = payload$confidence_level
)

nullable <- function(value) {
  if (length(value) == 0 || is.na(value) || !is.finite(value)) NULL else unname(value)
}

parameter_row <- function(row) {
  lhs <- row$lhs
  rhs <- row$rhs
  if (lhs %in% names(factor_name_map)) lhs <- factor_name_map[[lhs]]
  if (rhs %in% names(factor_name_map)) rhs <- factor_name_map[[rhs]]
  if (lhs %in% names(indicator_name_map)) lhs <- indicator_name_map[[lhs]]
  if (rhs %in% names(indicator_name_map)) rhs <- indicator_name_map[[rhs]]
  list(
    lhs = lhs,
    operator = row$op,
    rhs = rhs,
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

result <- list(
  model = list(
    name = "Confirmatory factor analysis",
    engine = "lavaan::cfa",
    estimator = payload$estimator,
    identification = "latent variances fixed to 1 (std.lv = TRUE)",
    missing = "listwise",
    converged = isTRUE(lavInspect(fit, "converged")),
    post_check = isTRUE(lavInspect(fit, "post.check")),
    free_parameters = unname(lavInspect(fit, "npar")),
    degrees_of_freedom = measure("df")
  ),
  fit = list(
    chi_square = measure("chisq"),
    degrees_of_freedom = measure("df"),
    p_value = measure("pvalue"),
    cfi = measure("cfi"),
    tli = measure("tli"),
    rmsea = measure("rmsea"),
    rmsea_ci_lower = measure("rmsea.ci.lower"),
    rmsea_ci_upper = measure("rmsea.ci.upper"),
    srmr = measure("srmr"),
    aic = measure("aic"),
    bic = measure("bic"),
    robust = list(
      cfi = measure("cfi.robust"),
      tli = measure("tli.robust"),
      rmsea = measure("rmsea.robust"),
      rmsea_ci_lower = measure("rmsea.ci.lower.robust"),
      rmsea_ci_upper = measure("rmsea.ci.upper.robust")
    )
  ),
  loadings = loading_rows,
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
