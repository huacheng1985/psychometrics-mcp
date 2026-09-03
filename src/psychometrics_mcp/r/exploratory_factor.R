#!/usr/bin/env Rscript

suppressPackageStartupMessages(library(jsonlite))
suppressPackageStartupMessages(library(psych))

payload <- fromJSON(file("stdin"), simplifyVector = FALSE)
x <- do.call(rbind, lapply(payload$values, unlist))
storage.mode(x) <- "numeric"
variable_names <- unlist(payload$variable_names)
colnames(x) <- variable_names

scalar_character <- function(value) as.character(unlist(value)[[1]])
scalar_integer <- function(value) as.integer(unlist(value)[[1]])
scalar_numeric <- function(value) as.numeric(unlist(value)[[1]])

nullable <- function(value) {
  if (length(value) == 0 || is.na(value[[1]]) || !is.finite(value[[1]])) NULL else unname(value[[1]])
}

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

extraction <- scalar_character(payload$extraction)
action <- scalar_character(payload$action)

if (action == "parallel_analysis") {
  iterations <- scalar_integer(payload$iterations)
  percentile <- scalar_numeric(payload$percentile)
  seed <- scalar_integer(payload$seed)
  set.seed(seed)

  observed_fit <- capture_analysis(
    psych::fa(
      x,
      nfactors = 1,
      rotate = "none",
      fm = extraction,
      SMC = FALSE,
      scores = "none",
      residuals = FALSE,
      warnings = FALSE
    )
  )
  observed <- as.numeric(observed_fit$values)
  if (length(observed) != ncol(x) || any(!is.finite(observed))) {
    stop("Observed common-factor eigenvalues were not finite.")
  }
  simulated <- vapply(seq_len(iterations), function(index) {
    simulated_data <- matrix(rnorm(nrow(x) * ncol(x)), nrow = nrow(x), ncol = ncol(x))
    simulated_correlation <- cor(simulated_data)
    simulated_fit <- capture_analysis(
      psych::fa(
        simulated_correlation,
        nfactors = 1,
        rotate = "none",
        fm = extraction,
        SMC = FALSE,
        scores = "none",
        residuals = FALSE,
        warnings = FALSE
      )
    )
    as.numeric(simulated_fit$values)
  }, numeric(ncol(x)))
  if (any(!is.finite(simulated))) {
    stop("One or more simulated common-factor eigenvalues were not finite.")
  }

  simulated_mean <- rowMeans(simulated)
  simulated_percentile <- apply(
    simulated,
    1,
    quantile,
    probs = percentile,
    names = FALSE,
    type = 7
  )
  first_failure <- which(!(observed > simulated_percentile))[1]
  suggested_factors <- if (is.na(first_failure)) {
    ncol(x) - 1L
  } else {
    max(0L, first_failure - 1L)
  }
  suggested_factors <- min(suggested_factors, ncol(x) - 1L)

  eigenvalue_rows <- lapply(seq_len(ncol(x)), function(index) {
    list(
      component = index,
      observed_common_factor_eigenvalue = observed[[index]],
      simulated_mean = simulated_mean[[index]],
      simulated_percentile = simulated_percentile[[index]],
      retained_by_contiguous_rule = index <= suggested_factors
    )
  })
  result <- list(
    analysis = list(
      name = "Horn-style common-factor parallel analysis",
      engine = "psych::fa with explicit normal-data simulation",
      extraction = extraction,
      correlation = "Pearson",
      missing = "listwise",
      iterations = iterations,
      percentile = percentile,
      seed = seed,
      random_generator = "R stats::rnorm",
      comparison_rule = "retain leading observed eigenvalues strictly above simulated percentile"
    ),
    suggested_factors = suggested_factors,
    eigenvalues = eigenvalue_rows,
    package_versions = list(
      R = as.character(getRversion()),
      psych = as.character(packageVersion("psych")),
      jsonlite = as.character(packageVersion("jsonlite"))
    ),
    warnings = as.list(unique(captured_warnings))
  )
} else if (action == "exploratory_factor_analysis") {
  factors <- scalar_integer(payload$factors)
  requested_rotation <- scalar_character(payload$rotation)
  effective_rotation <- if (factors == 1L) "none" else requested_rotation
  if (factors == 1L && requested_rotation != "none") {
    captured_warnings <- c(
      captured_warnings,
      "Rotation was set to none because a one-factor solution cannot be rotated."
    )
  }

  fit <- capture_analysis(
    psych::fa(
      x,
      nfactors = factors,
      rotate = effective_rotation,
      fm = extraction,
      SMC = TRUE,
      scores = "none",
      residuals = TRUE,
      warnings = TRUE
    )
  )

  loadings <- unclass(fit$loadings)
  if (is.null(dim(loadings))) loadings <- matrix(loadings, ncol = factors)
  if (any(!is.finite(loadings))) stop("The EFA solution contains non-finite loadings.")
  factor_names <- paste0("factor_", seq_len(factors))

  signs <- vapply(seq_len(factors), function(index) {
    column <- loadings[, index]
    anchor <- which.max(abs(column))
    if (column[[anchor]] < 0) -1 else 1
  }, numeric(1))
  loadings <- sweep(loadings, 2, signs, "*")
  colnames(loadings) <- factor_names
  rownames(loadings) <- variable_names

  if (is.null(fit$Phi)) {
    phi <- diag(factors)
  } else {
    phi <- as.matrix(fit$Phi)
    sign_matrix <- diag(signs)
    phi <- sign_matrix %*% phi %*% sign_matrix
  }
  colnames(phi) <- factor_names
  rownames(phi) <- factor_names
  structure <- loadings %*% phi
  colnames(structure) <- factor_names
  rownames(structure) <- variable_names

  loading_rows <- lapply(seq_along(variable_names), function(index) {
    list(
      variable = variable_names[[index]],
      pattern_loadings = as.list(setNames(as.numeric(loadings[index, ]), factor_names)),
      structure_coefficients = as.list(setNames(as.numeric(structure[index, ]), factor_names)),
      communality = nullable(fit$communality[[index]]),
      uniqueness = nullable(fit$uniquenesses[[index]])
    )
  })
  correlation_rows <- lapply(seq_len(factors), function(index) {
    list(
      factor = factor_names[[index]],
      correlations = as.list(setNames(as.numeric(phi[index, ]), factor_names))
    )
  })

  accounted <- as.matrix(fit$Vaccounted)
  accounted_value <- function(row_name, column) {
    if (row_name %in% rownames(accounted)) nullable(accounted[row_name, column]) else NULL
  }
  variance_rows <- lapply(seq_len(factors), function(index) {
    list(
      factor = factor_names[[index]],
      ss_loadings = accounted_value("SS loadings", index),
      proportion_variance = accounted_value("Proportion Var", index),
      cumulative_variance = accounted_value("Cumulative Var", index),
      proportion_explained = accounted_value("Proportion Explained", index),
      cumulative_proportion = accounted_value("Cumulative Proportion", index)
    )
  })

  residual <- as.matrix(fit$residual)
  residual_indices <- which(upper.tri(residual), arr.ind = TRUE)
  residual_rows <- lapply(seq_len(nrow(residual_indices)), function(index) {
    row <- residual_indices[index, 1]
    column <- residual_indices[index, 2]
    list(
      variable_1 = variable_names[[row]],
      variable_2 = variable_names[[column]],
      residual_correlation = residual[row, column],
      absolute_residual = abs(residual[row, column])
    )
  })
  residual_order <- order(
    vapply(residual_rows, function(value) value$absolute_residual, numeric(1)),
    decreasing = TRUE
  )
  residual_rows <- residual_rows[head(residual_order, 25)]
  minimum_uniqueness <- min(as.numeric(fit$uniquenesses), na.rm = TRUE)
  maximum_communality <- max(as.numeric(fit$communality), na.rm = TRUE)
  maximum_absolute_residual <- max(abs(residual[upper.tri(residual)]), na.rm = TRUE)

  rmsea <- fit$RMSEA
  rmsea_value <- if (!is.null(rmsea) && "RMSEA" %in% names(rmsea)) rmsea[["RMSEA"]] else NULL
  rmsea_lower <- if (!is.null(rmsea) && "lower" %in% names(rmsea)) rmsea[["lower"]] else NULL
  rmsea_upper <- if (!is.null(rmsea) && "upper" %in% names(rmsea)) rmsea[["upper"]] else NULL

  result <- list(
    model = list(
      name = "Exploratory factor analysis",
      engine = "psych::fa",
      extraction = extraction,
      requested_rotation = requested_rotation,
      effective_rotation = effective_rotation,
      correlation = "Pearson",
      missing = "listwise",
      factors = factors,
      solution_available = TRUE,
      sign_orientation = "largest absolute pattern loading in each factor is positive"
    ),
    fit = list(
      objective = nullable(fit$objective),
      chi_square = nullable(fit$STATISTIC),
      degrees_of_freedom = nullable(fit$dof),
      p_value = nullable(fit$PVAL),
      rmsea = nullable(rmsea_value),
      rmsea_ci_lower = nullable(rmsea_lower),
      rmsea_ci_upper = nullable(rmsea_upper),
      tli = nullable(fit$TLI),
      cfi = nullable(fit$CFI),
      rmsr = nullable(fit$rms),
      corrected_rmsr = nullable(fit$crms),
      bic = nullable(fit$BIC),
      fit_index = nullable(fit$fit),
      off_diagonal_fit = nullable(fit$fit.off)
    ),
    diagnostics = list(
      heywood_case_detected = minimum_uniqueness < 0 || maximum_communality > 1,
      minimum_uniqueness = nullable(minimum_uniqueness),
      maximum_communality = nullable(maximum_communality),
      maximum_absolute_residual_correlation = nullable(maximum_absolute_residual),
      convergence_note = paste(
        "psych::fa returned a finite solution; this adapter does not infer a universal",
        "convergence flag across MINRES and ML, so warnings and diagnostics must be reviewed"
      )
    ),
    loadings = loading_rows,
    factor_correlations = correlation_rows,
    variance_accounted = variance_rows,
    largest_residual_correlations = residual_rows,
    package_versions = list(
      R = as.character(getRversion()),
      psych = as.character(packageVersion("psych")),
      GPArotation = as.character(packageVersion("GPArotation")),
      jsonlite = as.character(packageVersion("jsonlite"))
    ),
    warnings = as.list(unique(captured_warnings))
  )
} else {
  stop("Unsupported fixed exploratory-factor action.")
}

cat(toJSON(result, auto_unbox = TRUE, null = "null", na = "null", digits = 15))
