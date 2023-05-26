"""Jitter for questions in Otter Assign"""

import re

from nbformat.notebooknode import NotebookNode
from numpy import arange
from numpy.random import choice


class Jitter:
    def __init__(self, nb):
        self.nb = nb
        self.values = {}


    def value_from_range(self, matches) -> list:
        """ Takes an iterator of match objects and returns a list of lists of integers for range()
        """
        
        # becomes [['num', 'num', 'num'], ...]
        str_range = [re.sub(r'<<|>>', '', x.group()).split(',') for x in matches]

        # becomes [[float, float, float], ...]
        input_range = [[float(x) for x in cleaned_match] for cleaned_match in str_range]

        # choose a random value from each range
        random_nums = [choice(arange(*set_of_values)) for set_of_values in input_range] # using numpy to allow for floats

        for idx, val in enumerate(random_nums):
            if int(val) == val:
                random_nums[idx] = int(val)

        return random_nums


    def jitter(self) -> NotebookNode:
        for i, cell in enumerate(self.nb['cells']):
            regex = r'<<\d+?,([\s])?\d+?([\,]([\s])?\d+?(.\d+?)?)?>>'

            if bool(re.search(regex, cell['source'])):
                all_match = re.finditer(regex, cell['source'])
                local_values = self.value_from_range(all_match)

                while local_values:
                    self.nb['cells'][i]['source'] = re.sub(regex, f'<<{len(self.values)}>>', cell['source'], 1)
                    self.values[len(self.values)] = local_values.pop(0)

        for i, cell in enumerate(self.nb['cells']):
            if bool(re.search(r'<<\d+?>>', cell['source'])):
                all_match = re.finditer(r'<<\d+?>>', cell['source'])

                for match in all_match:
                    self.nb['cells'][i]['source'] = re.sub(r'<<\d+?>>', str(self.values[int(match.group()[2:-2])]), cell['source'], 1)

        print(self.values)

        return self.nb
  