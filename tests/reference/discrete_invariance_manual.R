# Hand-written identification logic. No semTools syntax generation is used.
# Same lavaan estimator: this is an adapter/identification check, not solver independence.
suppressPackageStartupMessages(library(lavaan))
suppressPackageStartupMessages(library(jsonlite))
p <- fromJSON(file("stdin"))
d <- as.data.frame(p$values); names(d) <- paste0("u", 1:6); d$g <- factor(p$groups)
items <- paste0("u", 1:6)
stages <- if (p$profile == "binary") c("configural", "joint") else c("configural", "thresholds")
fits <- list()
for (stage in stages) {
  joint <- stage == "joint"
  thresholds <- stage != "configural"
  loadings <- vapply(items, function(item) {
    if (joint) paste0("c(NA,NA)*", item, " + c(l", item, ",l", item, ")*", item) else paste0("c(NA,NA)*", item)
  }, character(1))
  syntax <- c(paste("f =~", paste(loadings, collapse = "+")),
    if (joint) "f ~~ c(1,NA)*f" else "f ~~ c(1,1)*f",
    if (joint) "f ~ c(0,NA)*1" else "f ~ c(0,0)*1")
  for (item in items) {
    syntax <- c(syntax, paste0(item, " ~ c(0,", if (stage == "thresholds") "NA" else "0", ")*1"),
      paste0(item, " ~~ c(1,", if (thresholds) "NA" else "1", ")*", item))
    n <- if (p$profile == "binary") 1L else 2L
    labels <- vapply(seq_len(n), function(k) {
      modifier <- if (thresholds) paste0("c(t", item, k, ",t", item, k, ")") else "c(NA,NA)"
      paste0(modifier, "*t", k)
    }, character(1))
    syntax <- c(syntax, paste(item, "|", paste(labels, collapse = "+")))
  }
  f <- cfa(paste(syntax, collapse = "\n"), data = d, group = "g", ordered = items,
           estimator = "WLSMV", parameterization = "theta")
  if (!lavInspect(f, "converged")) stop("Manual reference did not converge.")
  fits[[stage]] <- as.list(fitMeasures(f)[c("chisq", "chisq.scaled", "df")])
}
cat(toJSON(fits, auto_unbox = TRUE, digits = 15))
