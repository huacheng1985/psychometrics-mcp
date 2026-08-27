#!/usr/bin/env Rscript

suppressPackageStartupMessages(library(eRm))
suppressPackageStartupMessages(library(jsonlite))

payload <- fromJSON(file("stdin"), simplifyVector = TRUE)
x <- as.matrix(payload$responses)
storage.mode(x) <- "numeric"
colnames(x) <- payload$item_names

fit <- RM(x, se = TRUE, sum0 = TRUE)
persons <- person.parameter(fit)
item_fit <- itemfit(persons)

easiness <- as.numeric(fit$betapar)
easiness_se <- as.numeric(fit$se.beta)
item_names <- names(fit$betapar)
item_rows <- lapply(seq_along(easiness), function(index) {
  list(
    item = item_names[[index]],
    easiness = easiness[[index]],
    easiness_se = easiness_se[[index]],
    location = -easiness[[index]],
    outfit_msq = unname(item_fit$i.outfitMSQ[[index]]),
    infit_msq = unname(item_fit$i.infitMSQ[[index]]),
    outfit_z = unname(item_fit$i.outfitZ[[index]]),
    infit_z = unname(item_fit$i.infitZ[[index]]),
    discrimination = unname(item_fit$i.disc[[index]])
  )
})

theta <- persons$theta.table
person_rows <- lapply(seq_len(nrow(theta)), function(index) {
  list(
    row = index,
    estimate = unname(theta[index, "Person Parameter"]),
    standard_error = unname(theta[index, "Std.Error"]),
    interpolated = unname(theta[index, "Interpolated"])
  )
})

result <- list(
  model = list(
    name = "Rasch model",
    engine = "eRm::RM",
    estimator = "conditional maximum likelihood",
    identification = "sum-zero item easiness parameters",
    conditional_log_likelihood = unname(fit$loglik),
    iterations = unname(fit$iter),
    convergence_code = unname(fit$convergence),
    estimated_basic_parameters = unname(fit$npar)
  ),
  items = item_rows,
  persons = person_rows,
  package_versions = list(
    R = as.character(getRversion()),
    eRm = as.character(packageVersion("eRm")),
    jsonlite = as.character(packageVersion("jsonlite"))
  ),
  warnings = list(
    "eRm reports beta as item easiness; location is returned as -beta.",
    "Person parameters for extreme scores may be interpolated by eRm."
  )
)

cat(toJSON(result, auto_unbox = TRUE, na = "null", digits = 15))

