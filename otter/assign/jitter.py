"""Jitter for questions in Otter Assign"""

import re
from numpy.random import choice


class Jitter:
    """
    A class for jittering a notebook.
    
    Searches for all instances of ``<<int, int[, int]>>`` in markdown cells and 
    replaces them with a random value as specified by the range.
    
    Args:
        notebook (``nbformat.NotebookNode``): the notebook to be jittered
    """
    def __init__(self, notebook):
        self.notebook = notebook
        self.values = []
        self.counter = 0


    def get_value(self) -> str:
        """
        Args:
            None - called on a ``Jitter`` object
        Returns:
            ``str``: the next value in ``self.values``
        """
        value = self.values[self.counter]
        self.counter += 1
        return str(value)


    def value_from_range(self, matches) -> None:
        """ 
        Args:
            matches (``re.Match callable_iterator``): a list of matches from a regex search
        Returns:
            None - sets ``self.values`` to a list of values from the ranges in ``matches``   
        """

        # becomes [['int', 'int', 'int'], ...]
        str_range = [re.sub(r'<<|>>', '', x.group()).split(',') for x in matches]

        # becomes [[int, int, int], ...]
        int_range = [[int(x) for x in cleaned_match] for cleaned_match in str_range]

        # choose a random value from each range
        self.values = [choice(range(*set_of_values)) for set_of_values in int_range]


    def jitter(self):
        """
        Args:
            None - called on a ``Jitter`` object

        Returns:
            ``nbformat.NotebookNode``: the jitter transformed notebook
        """
        for i, cell in enumerate(self.notebook['cells']):
            if cell['cell_type'] in ['raw', 'markdown'] and bool(re.search(r'<<.+?>>', cell['source'])):

                all_match = re.finditer(r'<<\d+?,([\s])?\d+?([\,]([\s])?\d+?)?>>', cell['source'])

                self.value_from_range(all_match)

                while bool(re.search(r'<<.+?>>', cell['source'])):
                    self.notebook['cells'][i]['source'] = re.sub(r'<<.+?>>', self.get_value(), cell['source'], 1)

        return self.notebook
