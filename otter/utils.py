######################################
##### Utilities for Otter-Grader #####
######################################

MISSING_PACKAGES = False

import os
import sys
import pathlib
import random
import string
import pandas as pd

from contextlib import contextmanager
from IPython import get_ipython

try:
    from psycopg2 import connect, extensions
except ImportError:
    MISSING_PACKAGES = True


@contextmanager
def block_print():
    """
    Context manager that disables printing to stdout.
    """
    sys.stdout = open(os.devnull, 'w')
    try:
        yield
    finally:
        try:
            sys.stdout.close()
        except:
            pass
        sys.stdout = sys.__stdout__

def list_files(path):
    """Returns a list of all non-hidden files in a directory
    
    Args:
        path (``str``): path to a directory
    
    Returns:
        ``list`` of ``str``: list of filenames in the given directory

    """
    return [file for file in os.listdir(path) if os.path.isfile(os.path.join(path, file)) and file[0] != "."]

def merge_csv(dataframes):
    """Merges dataframes along the vertical axis
    
    Args:
        dataframes (``list`` of ``pandas.core.frame.DataFrame``): list of dataframes with same columns
    
    Returns:
        ``pandas.core.frame.DataFrame``: A merged dataframe resulting from 'stacking' all input dataframes

    """
    final_dataframe = pd.concat(dataframes, axis=0, join='inner').sort_index()
    return final_dataframe

def connect_db(host="localhost", username="admin", password="", port="5432", db="otter_db"):
    """Connects to a specific Postgres database with provided parameters/credentials

    Arguments:
        host (``str``, optional): hostname for database (default 'localhost')
        username (``str``, optional): username with proper read/write permissions for Postgres
        password (``str``, optional): password for provided username
        port (``str``, optional): port on which Postgres is running

    Returns:
        ``connection``: connection object for executing SQL commands on Postgres database

    Raises:
        ``ImportError``: if psycopg2 is not installed
    """
    if MISSING_PACKAGES:
        raise ImportError(
            "Missing some packages required for otter service. "
            "Please install all requirements at "
            "https://raw.githubusercontent.com/ucbds-infra/otter-grader/master/requirements.txt"
        )
        
    conn = connect(dbname=db,
               user=username,
               host=host,
               password=password,
               port=port)
    conn.set_isolation_level(extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    return conn

def flush_inline_matplotlib_plots():
    """
    Flush matplotlib plots immediately, rather than asynchronously
    
    Basically, the inline backend only shows the plot after the entire cell executes, which means we 
    can't easily use a context manager to suppress displaying it. See https://github.com/jupyter-widgets/ipywidgets/issues/1181/ 
    and https://github.com/ipython/ipython/issues/10376 for more details. This function displays flushes 
    any pending matplotlib plots if we are using the inline backend. Stolen from 
    https://github.com/jupyter-widgets/ipywidgets/blob/4cc15e66d5e9e69dac8fc20d1eb1d7db825d7aa2/ipywidgets/widgets/interaction.py#L35
    """
    if 'matplotlib' not in sys.modules:
        # matplotlib hasn't been imported, nothing to do.
        return

    try:
        import matplotlib as mpl
        from ipykernel.pylab.backend_inline import flush_figures
    except ImportError:
        return
    # except KeyError:
    #     return

    if mpl.get_backend() == 'module://ipykernel.pylab.backend_inline':
        flush_figures()

@contextmanager
def hide_outputs():
    """
    Context manager for hiding outputs from ``display()`` calls. IPython handles matplotlib outputs 
    specially, so those are supressed too.
    """
    ipy = get_ipython()
    if ipy is None:
        # Not running inside ipython!
        yield
        return
    old_formatters = ipy.display_formatter.formatters
    ipy.display_formatter.formatters = {}
    try:
        yield
    finally:
        # flush_inline_matplotlib_plots()
        ipy.display_formatter.formatters = old_formatters

def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    """Used to generate a dynamic variable name for grading functions

    This function generates a random name using the given length and character set.
    
    Args:
        size (``int``): length of output name
        chars (``str``, optional): set of characters used to create function name
    
    Returns:
        ``str``: randomized string name for grading function
    """
    return ''.join(random.choice(chars) for _ in range(size))

def str_to_doctest(code_lines, lines):
    """
    Converts a list of lines of Python code ``code_lines`` to a list of doctest-formatted lines ``lines``

    Args:
        code_lines (``list``): list of lines of python code
        lines (``list``): set of characters used to create function name
    
    Returns:
        ``list`` of ``str``: doctest formatted list of lines
    """
    if len(code_lines) == 0:
        return lines
    line = code_lines.pop(0)
    if line.startswith(" ") or line.startswith("\t"):
        return str_to_doctest(code_lines, lines + ["... " + line])
    elif line.startswith("except:") or line.startswith("elif ") or line.startswith("else:") or line.startswith("finally:"):
        return str_to_doctest(code_lines, lines + ["... " + line])
    elif len(lines) > 0 and lines[-1].strip().endswith("\\"):
        return str_to_doctest(code_lines, lines + ["... " + line])
    else:
        return str_to_doctest(code_lines, lines + [">>> " + line])

def get_variable_type(obj):
    """
    """
    return  type(obj).__module__ + "." + type(obj).__name__
