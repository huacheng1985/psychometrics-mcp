# Independent syntax construction for configural and threshold invariance.
# This deliberately does not call semTools::measEq.syntax. Estimation still
# uses lavaan, so this verifies identification mapping, not an independent solver.
suppressPackageStartupMessages(library(lavaan))
data <- semTools::datCat
indicators <- paste0("u", 1:8)
base <- c(
  paste("f1 =~", paste(paste0("c(NA,NA)*u", 1:4), collapse = "+")),
  paste("f2 =~", paste(paste0("c(NA,NA)*u", 5:8), collapse = "+")),
  "f1 ~~ c(1,1)*f1", "f2 ~~ c(1,1)*f2",
  "f1 ~ c(0,0)*1", "f2 ~ c(0,0)*1"
)
fits <- list()
for (stage in c("configural", "thresholds")) {
  syntax <- base
  for (item in indicators) {
    free <- if (stage == "thresholds") "NA" else "0"
    variance <- if (stage == "thresholds") "NA" else "1"
    syntax <- c(syntax, paste0(item, " ~ c(0,", free, ")*1"),
                paste0(item, " ~~ c(1,", variance, ")*", item))
    thresholds <- vapply(1:4, function(k) {
      label <- paste0(item, "t", k)
      modifier <- if (stage == "thresholds") paste0("c(", label, ",", label, ")") else "c(NA,NA)"
      paste0(modifier, "*t", k)
    }, character(1))
    syntax <- c(syntax, paste(item, "|", paste(thresholds, collapse = "+")))
  }
  fits[[stage]] <- cfa(paste(syntax, collapse = "\n"), data = data, group = "g",
    ordered = indicators, estimator = "WLSMV", parameterization = "theta")
}
result <- lapply(fits, function(fit) as.list(fitMeasures(fit)[c("chisq", "chisq.scaled", "df")]))
cat(jsonlite::toJSON(result, auto_unbox = TRUE, digits = 15))
