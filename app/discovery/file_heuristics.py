"""Shared name/help-text heuristic for guessing file/directory parameter types.

Neither argparse nor optparse scripts reliably declare a dedicated file type
(usually just type=str / type="character"), so the parameter name and help
text are the only signal available.
ponytail: name-based heuristic, ceiling is false positives on oddly-named
string params — upgrade path is a tool.yaml override of param_type.
"""
from app.core.tool import ParameterType

_DIR_WORDS = ("dir", "directory", "folder")
_OUTPUT_WORDS = ("output", "outfile", "outdir", "out_dir", "out_file", "save", "dest")
_FILE_WORDS = ("file", "path", "input", "csv", "fasta", "reference", "infile")


def is_output_param(name: str) -> bool:
    """True for names like output, output_dir, outdir, save_to, dest — used to point
    the "where do results land" UI at the right field regardless of its resolved type."""
    return any(w in name.lower() for w in _OUTPUT_WORDS)


def guess_file_type(name: str, help_text: str) -> ParameterType | None:
    name_l = name.lower()
    haystack = f"{name_l} {help_text.lower()}"
    is_output = any(w in name_l for w in _OUTPUT_WORDS)
    is_dir = any(w in name_l for w in _DIR_WORDS)
    if is_dir:
        return ParameterType.DIRECTORY
    if is_output:
        return ParameterType.FILE_OUT
    if any(w in haystack for w in _FILE_WORDS):
        return ParameterType.FILE_IN
    return None
