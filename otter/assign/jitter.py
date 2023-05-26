"""Jitter for questions in Otter Assign"""

import re

from nbformat.notebooknode import NotebookNode
from numpy import arange
from numpy.random import choice


class Jitter:
    """Jitter for questions in Otter Assign"""
    def __init__(self, notebook):
        self.notebook = notebook
        self.values = {}


    def value_from_range(self, matches) -> list:
        """ Takes an iterator of match objects and returns a list of lists of integers for range()
        """

        # becomes [['num', 'num', 'num'], ...]
        str_range = [re.sub(r'<<|>>', '', x.group()).split(',') for x in matches]

        # becomes [[float, float, float], ...]
        input_range = [[float(x) for x in cleaned_match] for cleaned_match in str_range]

        # choose a random value from each range, numpy to allow floats
        random_nums = [choice(arange(*set_of_values)) for set_of_values in input_range]

        for idx, val in enumerate(random_nums):
            if int(val) == val:
                random_nums[idx] = int(val)

        return random_nums


    def jitter(self) -> NotebookNode:
        """Jitters the notebook"""

        # find all ranges and replace with <<num>>
        for i, cell in enumerate(self.notebook['cells']):
            regex = r'<<\d+?,([\s])?\d+?([\,]([\s])?\d+?(.\d+?)?)?>>'

            if bool(re.search(regex, cell['source'])):
                all_match = re.finditer(regex, cell['source'])
                local_values = self.value_from_range(all_match)

                while local_values:
                    self.notebook['cells'][i]['source'] = re.sub(regex, \
                        f'<<{len(self.values)}>>', cell['source'], 1)

                    self.values[len(self.values)] = local_values.pop(0)

        # replace all <<num>> with values
        for i, cell in enumerate(self.notebook['cells']):
            if bool(re.search(r'<<\d+?>>', cell['source'])):
                all_match = re.finditer(r'<<\d+?>>', cell['source'])

                for match in all_match:
                    self.notebook['cells'][i]['source'] = re.sub(r'<<\d+?>>', \
                        str(self.values[int(match.group()[2:-2])]), cell['source'], 1)

        return self.notebook
  