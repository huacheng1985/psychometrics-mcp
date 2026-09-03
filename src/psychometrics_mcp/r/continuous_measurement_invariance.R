#!/usr/bin/env Rscript

suppressPackageStartupMessages(library(jsonlite))
suppressPackageStartupMessages(library(lavaan))

payload <- fromJSON(file("stdin"), simplifyVector = FALSE)
x <- do.call(rbind, lapply(payload$values, unlist))
storage.mode(x) <- "numeric"
indicator_ids <- unlist(payload$indicator_ids)
indicator_names <- unlist(payload$indicator_names)
colnames(x) <- indicator_ids
groups <- unlist(payload$groups)
estimator <- as.character(unlist(payload$estimator)[[1]])

factor_ids <- vapply(payload$factors, function(value) value$id, character(1))
factor_names <- vapply(payload$factors, function(value) value$name, character(1))
factor_name_map <- setNames(factor_names, factor_ids)
indicator_name_map <- setNames(indicator_names, indicator_ids)
group_ids <- vapply(payload$group_map, function(value) value$id, character(1))
group_labels <- lapply(payload$group_map, function(value) value$label)
group_label_map <- setNames(group_labels, group_ids)

model_lines <- vapply(payload$factors, function(value) {
  paste(value$id, "=~", paste(unlist(value$indicators), collapse = " + "))
}, character(1))
model_syntax <- paste(model_lines, collapse = "\n")

data <- as.data.frame(x)
data$group_id <- factor(groups, levels = group_ids)

stages <- list(
  configural = character(),
  metric = c("loadings"),
  scalar = c("loadings", "intercepts"),
  strict = c("loadings", "intercepts", "residuals")
)

captured_warnings <- character()
capture_stage <- function(stage, expression) {
  withCallingHandlers(
    expression,
    warning = function(value) {
      captured_warnings <<- c(
        captured_warnings,
        paste0(stage, ": ", conditionMessage(value))
      )
      invokeRestart("muffleWarning")
    }
  )
}

fits <- lapply(names(stages), function(stage) {
  fit_arguments <- list(
    model = model_syntax,
    data = data,
    group = "group_id",
    estimator = estimator,
    std.lv = TRUE,
    missing = "listwise",
    meanstructure = TRUE
  )
  if (length(stages[[stage]]) > 0) {
    fit_arguments$group.equal <- stages[[stage]]
  }
  capture_stage(
    stage,
    do.call("cfa", fit_arguments)
  )
})
names(fits) <- names(stages)

nullable <- function(value) {
  if (length(value) == 0 || is.na(value[[1]]) || !is.finite(value[[1]])) NULL else unname(value[[1]])
}

measure <- function(measures, name) {
  if (name %in% names(measures)) nullable(measures[[name]]) else NULL
}

minimum_eigenvalue <- function(value) {
  matrices <- if (is.list(value)) value else list(value)
  min(vapply(matrices, function(matrix) {
    min(eigen(as.matrix(matrix), symmetric = TRUE, only.values = TRUE)$values)
  }, numeric(1)))
}

stage_rows <- lapply(names(stages), function(stage) {
  fit <- fits[[stage]]
  measures <- fitMeasures(fit)
  theta <- lavInspect(fit, "theta")
  theta_matrices <- if (is.list(theta)) theta else list(theta)
  minimum_residual <- min(vapply(theta_matrices, function(matrix) {
    min(diag(as.matrix(matrix)))
  }, numeric(1)))
  latent_minimum <- minimum_eigenvalue(lavInspect(fit, "cov.lv"))
  list(
    stage = stage,
    equality_constraints = as.list(stages[[stage]]),
    converged = isTRUE(lavInspect(fit, "converged")),
    post_check = isTRUE(lavInspect(fit, "post.check")),
    free_parameters = unname(lavInspect(fit, "npar")),
    fit = list(
      standard = list(
        chi_square = measure(measures, "chisq"),
        degrees_of_freedom = measure(measures, "df"),
        p_value = measure(measures, "pvalue"),
        cfi = measure(measures, "cfi"),
        tli = measure(measures, "tli"),
        rmsea = measure(measures, "rmsea"),
        rmsea_ci_lower = measure(measures, "rmsea.ci.lower"),
        rmsea_ci_upper = measure(measures, "rmsea.ci.upper"),
        srmr = measure(measures, "srmr"),
        aic = measure(measures, "aic"),
        bic = measure(measures, "bic")
      ),
      scaled = list(
        chi_square = measure(measures, "chisq.scaled"),
        degrees_of_freedom = measure(measures, "df.scaled"),
        p_value = measure(measures, "pvalue.scaled"),
        scaling_correction = measure(measures, "chisq.scaling.factor")
      ),
      robust = list(
        cfi = measure(measures, "cfi.robust"),
        tli = measure(measures, "tli.robust"),
        rmsea = measure(measures, "rmsea.robust"),
        rmsea_ci_lower = measure(measures, "rmsea.ci.lower.robust"),
        rmsea_ci_upper = measure(measures, "rmsea.ci.upper.robust")
      )
    ),
    diagnostics = list(
      minimum_residual_variance = minimum_residual,
      residual_variances_nonnegative = minimum_residual >= 0,
      minimum_latent_covariance_eigenvalue = latent_minimum,
      latent_covariances_positive_definite = latent_minimum > 1e-10
    )
  )
})
names(stage_rows) <- names(stages)

delta <- function(current, previous) {
  if (is.null(current) || is.null(previous)) NULL else current - previous
}

comparisons <- lapply(seq.int(2L, length(stages)), function(index) {
  previous_stage <- names(stages)[[index - 1L]]
  current_stage <- names(stages)[[index]]
  comparison <- capture_stage(
    paste(previous_stage, "to", current_stage),
    lavTestLRT(fits[[previous_stage]], fits[[current_stage]])
  )
  current_fit <- stage_rows[[current_stage]]$fit
  previous_fit <- stage_rows[[previous_stage]]$fit
  list(
    previous_stage = previous_stage,
    current_stage = current_stage,
    constraints_added = as.list(setdiff(stages[[current_stage]], stages[[previous_stage]])),
    comparison_valid = TRUE,
    likelihood_ratio_test = list(
      method = if (estimator == "MLR") {
        "Satorra-Bentler scaled difference test (lavaan default)"
      } else {
        "standard chi-square difference test"
      },
      chi_square_difference = nullable(comparison[["Chisq diff"]][[2]]),
      degrees_of_freedom_difference = nullable(comparison[["Df diff"]][[2]]),
      p_value = nullable(comparison[["Pr(>Chisq)"]][[2]])
    ),
    fit_change = list(
      standard_delta_cfi = delta(
        current_fit$standard$cfi, previous_fit$standard$cfi
      ),
      standard_delta_rmsea = delta(
        current_fit$standard$rmsea, previous_fit$standard$rmsea
      ),
      delta_srmr = delta(
        current_fit$standard$srmr, previous_fit$standard$srmr
      ),
      robust_delta_cfi = delta(
        current_fit$robust$cfi, previous_fit$robust$cfi
      ),
      robust_delta_rmsea = delta(
        current_fit$robust$rmsea, previous_fit$robust$rmsea
      )
    ),
    automatic_decision = NULL
  )
})

mapped_name <- function(value) {
  if (value %in% names(factor_name_map)) return(factor_name_map[[value]])
  if (value %in% names(indicator_name_map)) return(indicator_name_map[[value]])
  value
}

configural_parameters <- parameterEstimates(
  fits$configural,
  standardized = TRUE,
  ci = FALSE
)
parameter_rows <- function(frame) {
  lapply(seq_len(nrow(frame)), function(index) {
    row <- frame[index, , drop = FALSE]
    list(
      group = group_label_map[[group_ids[[row$group]]]],
      lhs = mapped_name(row$lhs),
      operator = row$op,
      rhs = mapped_name(row$rhs),
      estimate = nullable(row$est),
      standard_error = nullable(row$se),
      standardized_estimate = nullable(row$std.all)
    )
  })
}

loading_frame <- configural_parameters[
  configural_parameters$op == "=~", , drop = FALSE
]
intercept_frame <- configural_parameters[
  configural_parameters$op == "~1" & configural_parameters$lhs %in% indicator_ids,
  ,
  drop = FALSE
]
residual_frame <- configural_parameters[
  configural_parameters$op == "~~" &
    configural_parameters$lhs %in% indicator_ids &
    configural_parameters$lhs == configural_parameters$rhs,
  ,
  drop = FALSE
]

result <- list(
  model = list(
    name = "Continuous-indicator multi-group measurement invariance",
    engine = "lavaan::cfa + lavaan::lavTestLRT",
    estimator = estimator,
    identification = "latent variances fixed to 1 in configural model (std.lv = TRUE)",
    missing = "listwise",
    sequence = as.list(names(stages)),
    automatic_decision = FALSE,
    partial_invariance_search = FALSE,
    group_map = payload$group_map
  ),
  models = unname(stage_rows),
  comparisons = comparisons,
  configural_parameters = list(
    loadings = parameter_rows(loading_frame),
    indicator_intercepts = parameter_rows(intercept_frame),
    residual_variances = parameter_rows(residual_frame)
  ),
  package_versions = list(
    R = as.character(getRversion()),
    lavaan = as.character(packageVersion("lavaan")),
    jsonlite = as.character(packageVersion("jsonlite"))
  ),
  warnings = as.list(unique(captured_warnings))
)

cat(toJSON(result, auto_unbox = TRUE, null = "null", na = "null", digits = 15))
