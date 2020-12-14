"""
"""

__all__ = ["export_notebook", "grade_submission"]

import os
import sys
import shutil
import tempfile

from contextlib import redirect_stdout, nullcontext

from .argparser import get_parser
from .export import export_notebook
from .run import main as run_grader

PARSER = get_parser()
ARGS_STARTER = ["run"]

def grade_submission(ag_path, submission_path, quiet=False):
    """
    Runs non-containerized grading on a single submission at ``submission_path`` using the autograder 
    configuration file at ``ag_path``. 
    
    Creates a temporary grading directory using the ``tempfile`` library and grades the submission 
    by replicating the autograder tree structure in that folder and running the autograder there. Does
    not run environment setup files (e.g. ``setup.sh``) or install requirements, so any requirements 
    should be available in the environment being used for grading. 
    
    Print statements executed during grading can be suppressed with ``quiet``.

    Args:
        ag_path (``str``): path to autograder zip file
        submission_path (``str``): path to submission file
        quiet (``bool``, optional): whether to suppress print statements during grading; default 
            ``False``

    Returns:
        ``otter.test_files.GradingResults``: the results object produced during the grading of the
            submission.
    """

    dp = tempfile.mkdtemp()

    args_list = ARGS_STARTER.copy()
    args_list.extend([
        "-a", ag_path,
        "-o", dp,
        submission_path,
        "--no-logo"
    ])

    args = PARSER.parse_args(args_list)

    if quiet:
        f = open(os.devnull, "w")
        cm = redirect_stdout(f)
    else:
        cm = nullcontext()
        
    with cm:
        results = run_grader(args)

    if quiet:
        f.close()

    shutil.rmtree(dp)

    return results
