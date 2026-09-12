# Counts rows in a CSV whose column value exceeds a threshold.
# No dependencies beyond optparse and base R — safe to actually run end-to-end.
suppressMessages(library(optparse))

option_list <- list(
  make_option(c("-i", "--input"), type="character", default=NULL, help="Input CSV file"),
  make_option(c("-c", "--column"), type="character", default="value", help="Column to threshold on"),
  make_option(c("-t", "--threshold"), type="double", default=0.05, help="Significance threshold")
)
opt <- parse_args(OptionParser(option_list=option_list))

df <- read.csv(opt$input)
count <- sum(df[[opt$column]] > opt$threshold)
cat(sprintf("%d of %d rows above threshold %.2f\n", count, nrow(df), opt$threshold))
cat("Done.\n")
