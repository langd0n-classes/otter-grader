"""Assignment creation tool for Otter-Grader"""

import os
import pathlib
import warnings

from pickle import dump
from nbformat import write, read

from .jitter import Jitter
from .assignment import Assignment
from .output import write_output_directories
from .utils import run_tests, write_otter_config_file, run_generate_autograder

from ..export import export_notebook, WkhtmltopdfNotFoundError
from ..plugins import PluginCollection
from ..utils import chdir, get_relpath, knit_rmd_file, loggers, NBFORMAT_VERSION


LOGGER = loggers.get_logger(__name__)


def main(master, result, *, no_pdfs=False, no_run_tests=False, username=None, password=None,
         debug=False, v0=False, jitter=0):
    """
    Runs Otter Assign on a master notebook.

    Args:
        master (``str``): path to master notebook
        result (``str``): path to result directory
        no_pdfs (``bool``): whether to ignore any configurations indicating PDF generation for this run
        no_run_tests (``bool``): prevents Otter tests from being automatically run on the solutions 
            notebook
        username (``str``): a username for Gradescope for generating a token
        password (``str``): a password for Gradescope for generating a token
        debug (``bool``): whether to run in debug mode (without ignoring errors during testing)
        v0 (``bool``): whether to use Otter Assign Format v0 instead of v1
        jitter (``int``): number of versions to generate
    """
    if v0:
        warnings.warn(
            "The Otter Assign v0 format is now deprecated and will be removed in Otter v5.",
            FutureWarning)

        from .v0 import main as v0_main
        return v0_main(master, result, no_pdfs=no_pdfs, no_run_tests=no_run_tests, username=username,
            password=password, debug=debug)

    LOGGER.debug(f"User-specified master path: {master}")
    LOGGER.debug(f"User-specified result path: {result}")
    master, result = pathlib.Path(os.path.abspath(master)), pathlib.Path(os.path.abspath(result))

    if jitter:
        jitter_obj = Jitter(master, jitter)

        # create and store jitter values
        with open(f'{master.parent}/jv.pkl', 'w+b') as jitter_file:
            dump(jitter_obj.jitter_values, jitter_file)

        master_name = master.name

        # substitute true master notebook with jittered master notebook
        write(jitter_obj.clean_nb, f"{master.parent}/jmaster.ipynb")
        master = pathlib.Path(os.path.abspath(f"{master.parent}/jmaster.ipynb"))


    assignment = Assignment()

    result = get_relpath(master.parent, result)

    assignment.master, assignment.result = master, result
    LOGGER.debug(f"Normalized master path: {master}")
    LOGGER.debug(f"Normalized result path: {result}")

    with chdir(master.parent):
        LOGGER.info("Generating views")
        write_output_directories(assignment)

        # update seed variables
        if assignment.seed.variable:
            LOGGER.debug("Processing seed dict")
            if assignment.generate_enabled:
                LOGGER.debug("Otter Generate configuration found while processing seed dict")
                assignment.generate.seed = assignment.seed.autograder_value
                assignment.generate.seed_variable = assignment.seed.variable
                LOGGER.debug("Added seed information to assignment.generate")

        # check that we have a seed if needed
        if assignment.seed_required:
            LOGGER.debug("Assignment seed is required")
            if assignment.generate_enabled and \
                    not isinstance(assignment.generate.seed, int):
                raise RuntimeError("Seeding cell found but no or invalid seed provided")

        plugins, pc = assignment.plugins, None
        if plugins:
            LOGGER.debug("Processing plugins")
            pc = PluginCollection(plugins, "", {})
            pc.run("during_assign", assignment)
            if assignment.generate_enabled:
                LOGGER.debug("Adding plugin configurations to Otter Generate configuration")
                assignment.generate.plugins.extend(plugins)

        # generate Gradescope autograder zipfile
        if assignment.generate_enabled:
            LOGGER.info("Generating autograder zipfile")
            run_generate_autograder(assignment, username, password, plugin_collection=pc)

        # generate PDF of solutions
        if assignment.solutions_pdf and not no_pdfs:
            LOGGER.info("Generating solutions PDF")
            filtering = assignment.solutions_pdf == 'filtered'

            src = os.path.abspath(str(assignment.get_ag_path(master.name)))
            dst = os.path.abspath(str(assignment.get_ag_path(master.stem + '-sol.pdf')))

            if not assignment.is_rmd:
                LOGGER.debug(f"Exporting {src} as notebook to {dst}")
                try:
                    LOGGER.debug("Attempting PDF via HTML export")
                    export_notebook(
                        src,
                        dest=dst,
                        filtering=filtering,
                        pagebreaks=filtering,
                        exporter_type="html",
                    )
                    LOGGER.debug("PDF via HTML export successful")

                except WkhtmltopdfNotFoundError:
                    LOGGER.debug("PDF via HTML export failed; attempting PDF via LaTeX export")
                    export_notebook(
                        src,
                        dest=dst,
                        filtering=filtering,
                        pagebreaks=filtering,
                    )
                    LOGGER.debug("PDF via LaTeX export successful")

            else:
                LOGGER.debug(f"Knitting {src} to {dst}")
                if filtering:
                    raise ValueError("Filtering is not supported with RMarkdown assignments")

                knit_rmd_file(src, dst)

        # generate a template PDF for Gradescope
        if assignment.template_pdf and not no_pdfs:
            LOGGER.info("Generating template PDF")

            src = os.path.abspath(str(assignment.get_ag_path( master.name)))
            dst = os.path.abspath(str(assignment.get_ag_path(master.stem + '-template.pdf')))

            if not assignment.is_rmd:
                LOGGER.debug("Attempting PDF via LaTeX export")
                export_notebook(
                    src,
                    dest=dst, 
                    filtering=True, 
                    pagebreaks=True, 
                    exporter_type="latex",
                )
                LOGGER.debug("PDF via LaTeX export successful")

            else:
                raise ValueError(f"Filtering is not supported with RMarkdown assignments; use " + \
                    "solutions_pdf to generate a Gradescope template instead.")

        # generate the .otter file if needed
        if not assignment.is_rmd and assignment.save_environment:
            LOGGER.debug("Processing environment serialization configuration")
            if assignment.is_r:
                warnings.warn(
                    "Otter Service and serialized environments are unsupported with R, "
                    "configurations ignored")
            else:
                write_otter_config_file(assignment)

        # run tests on autograder notebook
        if assignment.run_tests and not no_run_tests and assignment.is_python:
            LOGGER.info("Running tests against the solutions notebook")

            seed = assignment.generate.seed if assignment.generate_enabled else None
            LOGGER.debug(f"Resolved seed for running tests: {seed}")

            if assignment.generate_enabled:
                LOGGER.debug("Retrieving updated plugins from otter_config.json for running tests")
                test_pc = PluginCollection(
                    assignment.generate.plugins, assignment.ag_notebook_path, {})

            else:
                LOGGER.debug("Using pre-configured plugins for running tests")
                test_pc = pc

            run_tests(
                assignment.get_ag_path(master.name),
                debug=debug,
                seed=seed,
                plugin_collection=test_pc,
            )

            LOGGER.info("All autograder tests passed.")

    if jitter:
        os.remove(pathlib.Path(os.path.abspath(f"{master.parent}/jmaster.ipynb")))
        os.remove(pathlib.Path(os.path.abspath(f"{master.parent}/jv.pkl")))

        # jmaster.ipynb is the temporary notebook used for processing Jitter
        os.rename(f"{result}/autograder/jmaster.ipynb", f"{result}/autograder/{master_name}")

        jitter_obj.assigned_nb = read(f"{result}/student/jmaster.ipynb", as_version=4)
        os.remove(f"{result}/student/jmaster.ipynb")

        for i in range(jitter):
            write(jitter_obj.full_modify(i), \
                f'{result}/student/{str(master_name).split(".", maxsplit=1)[0]}_v{i}.ipynb')
        