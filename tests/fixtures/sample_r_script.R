suppressMessages(library(optparse))
suppressMessages(library(DESeq2))

option_list <- list(
  make_option(c("-i", "--input"), type="character", default=NULL, help="Input counts CSV file"),
  make_option(c("-t", "--threshold"), type="double", default=0.05, help="Significance threshold"),
  make_option(c("-o", "--output-dir"), type="character", default=".", help="Where to write results"),
  make_option(c("-v", "--verbose"), action="store_true", default=FALSE, help="Verbose output")
)
opt <- parse_args(OptionParser(option_list=option_list))
