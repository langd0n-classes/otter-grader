"""Jitter for questions in Otter Assign"""

import re

from nbformat.notebooknode import NotebookNode
from numpy import arange
from numpy.random import choice



class Jitter:
    """Jitter for questions in Otter Assign"""
    def __init__(self, notebook):
        self.notebook = notebook
        self.has_jitter = False
        self.values = {}
        self.question_name = ''
        self.question_values = []


    def value_from_range(self, matches) -> list:
        """ Takes an iterator of match objects and returns a list of lists of integers for range()
        """

        # becomes [['num', 'num', 'num'], ...]
        str_range = [re.sub(r'\(\(|\)\)', '', x.group()).split(',') for x in matches]

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

        regex = r'\(\(\d+?,([\s])?\d+?([\,]([\s])?\d+?(.\d+?)?)?\)\)'
        short_regex = r'\(\(\d+?\)\)'

        for i, cell in enumerate(self.notebook['cells']):
            if '# BEGIN QUESTION' in cell['source'].upper():
                self.question_name = [line.split(':')[1] for line in cell['source'].split('\n') \
                    if 'name' in line.lower()][0]

                if 'jitter' in cell['source'].lower():
                    self.has_jitter = [line.split(':')[1] for line in cell['source'].split('\n') \
                        if 'jitter' in line.lower()][0].strip().lower() == 'true'

                self.values[self.question_name] = []

            elif '# END QUESTION' in cell['source'].upper() or not self.has_jitter:
                # reset to default values when current question ends
                self.question_name = ''
                self.has_jitter = False
                continue

            if bool(re.search(regex, cell['source'])):
                all_match = re.finditer(regex, cell['source'])
                local_values = self.value_from_range(all_match)
                full_len = len(local_values)

                self.values[self.question_name].extend(local_values)

                while local_values:
                    self.notebook['cells'][i]['source'] = re.sub(regex, \
                        f'(({full_len - len(local_values)}))', cell['source'], 1)

                    local_values.pop(0)

            if bool(re.search(short_regex, cell['source'])):
                while bool(re.search(short_regex, cell['source'])):
                    all_match = re.finditer(short_regex, cell['source'])

                    for match in all_match:
                        self.notebook['cells'][i]['source'] = re.sub(short_regex, \
                            str(self.values[self.question_name][int(match.group()[2:-2])]), \
                                cell['source'], 1)


        return self.notebook
  