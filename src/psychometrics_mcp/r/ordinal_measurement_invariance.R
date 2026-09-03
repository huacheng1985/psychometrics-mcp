#!/usr/bin/env Rscript
suppressPackageStartupMessages(library(jsonlite))
suppressPackageStartupMessages(library(lavaan))
suppressPackageStartupMessages(library(semTools))

payload <- fromJSON(file("stdin"), simplifyVector = FALSE)
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
index <- match(payload$stage, names(constraints))
if (is.na(index)) stop("Unsupported stage.")
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
  syntax_arguments <- list(
    configural.model = model, data = data, ordered = indicators, group = "group_id",
    parameterization = "theta", ID.fac = "std.lv", ID.cat = "Wu.Estabrook.2016"
  )
  if (length(constraints[[stage]]) > 0) syntax_arguments$group.equal <- constraints[[stage]]
  syntax <- capture(stage, as.character(do.call("measEq.syntax", syntax_arguments)))
  fit <- capture(stage, cfa(
    model = syntax, data = data, ordered = indicators, group = "group_id",
    estimator = "WLSMV", parameterization = "theta", missing = "listwise"
  ))
  if (!isTRUE(lavInspect(fit, "converged"))) stop(paste(stage, "did not converge."))
  post_check <- capture(stage, isTRUE(lavInspect(fit, "post.check")))
  theta <- as_matrices(lavInspect(fit, "theta"))
  min_residual <- min(vapply(theta, function(m) min(diag(m)), numeric(1)))
  latent_min <- min_eigen(lavInspect(fit, "cov.lv"))
  sample_min <- min_eigen(lapply(lavInspect(fit, "sampstat"), function(x) x$cov))
  if (!post_check || min_residual <= 0 || latent_min <= 1e-10 || sample_min <= 1e-10) {
    stop(paste(stage, "failed admissibility or positive-definite sample/latent covariance checks."))
  }
  parameters <- parameterEstimates(fit)
  threshold_rows <- parameters[parameters$op == "|", ]
  threshold_sets <- split(threshold_rows$est, interaction(threshold_rows$group, threshold_rows$lhs))
  if (any(vapply(threshold_sets, function(x) any(diff(x) <= 0), logical(1)))) {
    stop(paste(stage, "has non-increasing thresholds."))
  }
  fm <- capture(stage, fitMeasures(fit))
  if (!is.finite(fm[["chisq"]]) || !is.finite(fm[["chisq.scaled"]])) {
    stop(paste(stage, "has non-finite fit statistics."))
  }
  if (is.null(measure(fm, "cfi.robust")) || is.null(measure(fm, "rmsea.robust"))) {
    warnings <- c(warnings, paste(stage, "robust fit indices are unavailable; no substitution made."))
  }
  if (fm[["df"]] == 0) warnings <- c(warnings, paste(stage, "is just-identified; global fit is not informative."))
  pt <- parTable(fit)
  keep <- pt$op %in% c("=~", "|", "~1", "~~")
  audit <- pt[keep, c("lhs", "op", "rhs", "group", "free", "label", "est", "se")]
  rows[[stage]] <- list(
    stage = stage, equality_constraints = as.list(constraints[[stage]]),
    generated_syntax = syntax, parameter_audit = audit,
    converged = TRUE, post_check = post_check,
    diagnostics = list(minimum_residual_variance = min_residual,
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
  test <- capture("comparison", lavTestLRT(fits[[1]], fits[[2]], method = "satorra.2000",
    A.method = "delta", scaled.shifted = TRUE))
  statistic <- number(test[["Chisq diff"]][2])
  df <- number(test[["Df diff"]][2])
  p <- number(test[["Pr(>Chisq)"]][2])
  valid <- !is.null(statistic) && statistic >= 0 && !is.null(df) && df > 0 &&
    !is.null(p) && p >= 0 && p <= 1
  if (!valid) warnings <- c(warnings, "Adjusted comparison unavailable or invalid; do not interpret its p value.")
  previous <- rows[[1]]$fit
  current <- rows[[2]]$fit
  comparisons[[1]] <- list(
    previous_stage = stages[[1]], current_stage = stages[[2]], comparison_valid = valid,
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
  model = list(name = "Stagewise ordinal multi-group measurement invariance",
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
cat(toJSON(result, auto_unbox = TRUE, dataframe = "rows", null = "null", na = "null", digits = 15))
