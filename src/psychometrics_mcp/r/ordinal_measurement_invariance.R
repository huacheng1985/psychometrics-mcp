#!/usr/bin/env Rscript
suppressPackageStartupMessages(library(jsonlite))
suppressPackageStartupMessages(library(lavaan))
suppressPackageStartupMessages(library(semTools))

payload <- fromJSON(file("stdin"), simplifyVector = FALSE)
active_stage <- NULL
phase <- "input"
abort <- function(code, message) {
  stop(structure(list(message = message, call = NULL, code = code, stage = active_stage),
                 class = c("invariance_error", "error", "condition")))
}
run_analysis <- function() {
indicators <- unlist(payload$indicators)
x <- do.call(rbind, lapply(payload$values, unlist))
colnames(x) <- indicators
data <- as.data.frame(x)
group_ids <- vapply(payload$group_map, function(x) x$id, character(1))
data$group_id <- factor(unlist(payload$groups), levels = group_ids)
for (name in indicators) data[[name]] <- ordered(data[[name]])
model <- paste(vapply(payload$factors, function(x) {
  paste(x$id, "=~", paste(unlist(x$indicators), collapse = " + "))
}, character(1)), collapse = "\n")
constraints <- list(
  configural = character(), thresholds = "thresholds",
  metric = c("thresholds", "loadings"),
  scalar = c("thresholds", "loadings", "intercepts"),
  strict = c("thresholds", "loadings", "intercepts", "residuals")
)
if (payload$category_profile == "binary") {
  constraints <- list(configural = character(), joint = c("thresholds", "loadings", "intercepts"))
}
index <- match(payload$stage, names(constraints))
if (is.na(index)) abort("STAGE_UNSUPPORTED", "Unsupported stage for this category profile.")
stages <- names(constraints)[seq.int(max(1L, index - 1L), index)]
warnings <- character()
capture <- function(stage, expression) {
  withCallingHandlers(expression, warning = function(w) {
    warnings <<- c(warnings, paste0(stage, ": ", conditionMessage(w)))
    invokeRestart("muffleWarning")
  })
}
number <- function(x) {
  if (length(x) == 0 || !is.finite(x[[1]])) NULL else unname(x[[1]])
}
measure <- function(x, name) number(x[name])
as_matrices <- function(x) if (is.list(x)) x else list(x)
min_eigen <- function(x) min(vapply(as_matrices(x), function(m) {
  min(eigen(as.matrix(m), symmetric = TRUE, only.values = TRUE)$values)
}, numeric(1)))
fits <- list()
rows <- list()
for (stage in stages) {
  active_stage <<- stage
  phase <<- "identification"
  syntax_arguments <- list(
    configural.model = model, data = data, ordered = indicators, group = "group_id",
    parameterization = "theta", ID.fac = "std.lv", ID.cat = "Wu.Estabrook.2016"
  )
  if (length(constraints[[stage]]) > 0) syntax_arguments$group.equal <- constraints[[stage]]
  syntax <- capture(stage, as.character(do.call("measEq.syntax", syntax_arguments)))
  phase <<- "estimation"
  fit <- capture(stage, cfa(
    model = syntax, data = data, ordered = indicators, group = "group_id",
    estimator = "WLSMV", parameterization = "theta", missing = "listwise"
  ))
  if (!isTRUE(lavInspect(fit, "converged"))) abort("NONCONVERGENCE", paste(stage, "did not converge."))
  phase <<- "diagnostics"
  post_check <- capture(stage, isTRUE(lavInspect(fit, "post.check")))
  theta <- as_matrices(lavInspect(fit, "theta"))
  min_residual <- min(vapply(theta, function(m) min(diag(m)), numeric(1)))
  latent_min <- min_eigen(lavInspect(fit, "cov.lv"))
  sample_min <- min_eigen(lapply(lavInspect(fit, "sampstat"), function(x) x$cov))
  if (!post_check || min_residual <= 0 || latent_min <= 1e-10 || sample_min <= 1e-10) {
    abort("INADMISSIBLE_SOLUTION", paste(stage, "failed admissibility or positive-definite covariance checks."))
  }
  variance <- capture(stage, vcov(fit))
  if (is.null(variance) || any(!is.finite(variance))) {
    abort("IDENTIFICATION_FAILURE", paste(stage, "has unavailable parameter covariance."))
  }
  vcov_min <- min_eigen(variance)
  if (vcov_min < -1e-8 * max(1, max(abs(diag(variance))))) {
    abort("IDENTIFICATION_FAILURE", paste(stage, "has invalid parameter covariance."))
  }
  parameters <- capture(stage, parameterEstimates(fit))
  threshold_rows <- parameters[parameters$op == "|", ]
  threshold_sets <- split(threshold_rows$est, interaction(threshold_rows$group, threshold_rows$lhs))
  if (any(vapply(threshold_sets, function(x) any(diff(x) <= 0), logical(1)))) {
    abort("INADMISSIBLE_SOLUTION", paste(stage, "has non-increasing thresholds."))
  }
  fm <- capture(stage, fitMeasures(fit))
  if (!is.finite(fm[["chisq"]]) || !is.finite(fm[["chisq.scaled"]])) {
    abort("INADMISSIBLE_SOLUTION", paste(stage, "has non-finite fit statistics."))
  }
  if (is.null(measure(fm, "cfi.robust")) || is.null(measure(fm, "rmsea.robust"))) {
    warnings <- c(warnings, paste(stage, "robust fit indices are unavailable; no substitution made."))
  }
  if (fm[["df"]] == 0) warnings <- c(warnings, paste(stage, "is just-identified; global fit is not informative."))
  pt <- parTable(fit)
  if (any(!is.finite(pt$se[pt$free > 0]))) {
    abort("IDENTIFICATION_FAILURE", paste(stage, "has unavailable standard errors."))
  }
  keep <- pt$op %in% c("=~", "|", "~1", "~~")
  audit <- pt[keep, c("lhs", "op", "rhs", "group", "free", "label", "est", "se")]
  rows[[stage]] <- list(
    stage = stage, equality_constraints = as.list(constraints[[stage]]),
    generated_syntax = syntax, parameter_audit = audit,
    converged = TRUE, post_check = post_check,
    diagnostics = list(minimum_residual_variance = min_residual,
      minimum_parameter_covariance_eigenvalue = vcov_min,
      minimum_latent_covariance_eigenvalue = latent_min,
      minimum_sample_polychoric_eigenvalue = sample_min, thresholds_increasing = TRUE),
    fit = list(
      standard = list(chi_square = measure(fm, "chisq"), degrees_of_freedom = measure(fm, "df"),
        p_value = measure(fm, "pvalue"), cfi = measure(fm, "cfi"), tli = measure(fm, "tli"),
        rmsea = measure(fm, "rmsea"), srmr = measure(fm, "srmr")),
      scaled = list(chi_square = measure(fm, "chisq.scaled"), degrees_of_freedom = measure(fm, "df.scaled"),
        p_value = measure(fm, "pvalue.scaled"), scaling_correction = measure(fm, "chisq.scaling.factor"),
        cfi = measure(fm, "cfi.scaled"), tli = measure(fm, "tli.scaled"), rmsea = measure(fm, "rmsea.scaled")),
      robust = list(cfi = measure(fm, "cfi.robust"), tli = measure(fm, "tli.robust"),
        rmsea = measure(fm, "rmsea.robust"), rmsea_ci_lower = measure(fm, "rmsea.ci.lower.robust"),
        rmsea_ci_upper = measure(fm, "rmsea.ci.upper.robust"))
    )
  )
  fits[[stage]] <- fit
}
delta <- function(x, y) if (is.null(x) || is.null(y)) NULL else x - y
comparisons <- list()
if (length(stages) == 2) {
  phase <<- "comparison"
  df <- rows[[2]]$fit$standard$degrees_of_freedom - rows[[1]]$fit$standard$degrees_of_freedom
  identification_only <- payload$category_profile == "three_category" && payload$stage == "thresholds"
  test <- if (df > 0 && !identification_only) tryCatch(
    capture("comparison", lavTestLRT(fits[[1]], fits[[2]], method = "satorra.2000",
      A.method = "delta", scaled.shifted = TRUE)), error = function(e) NULL
  ) else NULL
  statistic <- if (is.null(test)) NULL else number(test[["Chisq diff"]][2])
  p <- if (is.null(test)) NULL else number(test[["Pr(>Chisq)"]][2])
  valid <- !is.null(statistic) && statistic >= 0 && !is.null(df) && df > 0 &&
    !is.null(p) && p >= 0 && p <= 1
  code <- if (valid) NULL else if (identification_only || df == 0) "NOT_INDEPENDENTLY_TESTABLE" else "COMPARISON_UNAVAILABLE"
  reason <- if (valid) NULL else if (identification_only) {
    "Three-category threshold equality releases location/scale identification restrictions; it is not an independent invariance test."
  } else "Adjusted comparison unavailable or invalid; do not interpret its p value."
  if (!valid) warnings <- c(warnings, reason)
  previous <- rows[[1]]$fit
  current <- rows[[2]]$fit
  comparisons[[1]] <- list(
    previous_stage = stages[[1]], current_stage = stages[[2]], comparison_valid = valid,
    code = code, reason = reason, identification_only = identification_only,
    adjusted_difference_test = list(method = "Satorra (2000) scaled-shifted; A.method=delta",
      chi_square_difference = if (valid) statistic else NULL,
      degrees_of_freedom_difference = df, p_value = if (valid) p else NULL),
    fit_change = list(
      standard_delta_cfi = delta(current$standard$cfi, previous$standard$cfi),
      standard_delta_rmsea = delta(current$standard$rmsea, previous$standard$rmsea),
      delta_srmr = delta(current$standard$srmr, previous$standard$srmr),
      scaled_delta_cfi = delta(current$scaled$cfi, previous$scaled$cfi),
      scaled_delta_rmsea = delta(current$scaled$rmsea, previous$scaled$rmsea),
      robust_delta_cfi = delta(current$robust$cfi, previous$robust$cfi),
      robust_delta_rmsea = delta(current$robust$rmsea, previous$robust$rmsea)),
    automatic_decision = NULL
  )
}
result <- list(
  status = "success",
  model = list(name = "Stagewise ordinal multi-group measurement invariance",
    category_profile = payload$category_profile, available_stages = as.list(names(constraints)),
    engine = "semTools::measEq.syntax + lavaan::cfa + lavaan::lavTestLRT",
    estimator = "WLSMV", parameterization = "theta", identification = "Wu.Estabrook.2016",
    factor_identification = "std.lv via semTools generated syntax", missing = "listwise",
    requested_stage = payload$stage, automatic_decision = FALSE, partial_invariance_search = FALSE),
  mappings = list(indicators = payload$indicator_map, factors = payload$factors, groups = payload$group_map),
  models = unname(rows), comparisons = comparisons,
  package_versions = list(R = as.character(getRversion()), lavaan = as.character(packageVersion("lavaan")),
    semTools = as.character(packageVersion("semTools")), jsonlite = as.character(packageVersion("jsonlite"))),
  warnings = as.list(unique(warnings))
)
result
}
result <- tryCatch(run_analysis(), error = function(e) {
  if (inherits(e, "invariance_error")) {
    list(status = "error", error = list(code = e$code, message = e$message, stage = e$stage))
  } else {
    list(status = "error", error = list(
      code = if (phase == "identification") "IDENTIFICATION_FAILURE" else "ENGINE_FAILURE",
      message = paste("Fixed R adapter failed during", phase), stage = active_stage))
  }
})
cat(toJSON(result, auto_unbox = TRUE, dataframe = "rows", null = "null", na = "null", digits = 15))
