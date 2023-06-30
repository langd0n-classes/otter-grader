import pathlib
import re

from nbformat.notebooknode import NotebookNode

import nbformat
from numpy import arange
from numpy.random import choice

class Jitter:
    """Jitter class that takes in a master notebook and the number of versions"""
    def __init__(self, path: pathlib.Path, versions: int):
        self.path = path
        self.versions = versions
        self.r = [
            r'\(\(\d+?,([\s])?\d+?([\,]([\s])?\d+?(.\d+?)?)?\)\)',
            r'\(\((\d+?)\)\)'
        ]

        self.ranges, self.clean_nb = self._get_ranges()
        self.jitter_values = self._generate()
        self.assigned_nb: NotebookNode


    def _get_ranges(self):
        """ Finds the values to be jittered and stores the
            cleaned notebook and values in the object"""

        notebook = nbformat.read(self.path, as_version=4)

        ranges = {}
        question_counter = 0
        jtag_location = []
        in_tests = False

        for idx, cell in enumerate(notebook['cells']):
            if '# BEGIN QUESTION' in cell['source'].upper():
                ranges[question_counter] = []

            elif '# END QUESTION' in cell['source'].upper():
                jtag_location.append(idx+1)
                question_counter += 1
                continue

            if '# BEGIN TESTS' in cell['source'].upper():
                in_tests = True

            elif '# END TESTS' in cell['source'].upper():
                in_tests = False

            if bool(re.search(self.r[0], cell['source'])):
                local_ranges, length = self._clean(re.finditer(self.r[0], cell['source']))
                ranges[question_counter].extend(local_ranges)

                for jitter_num in range(length):
                    notebook['cells'][idx]['source'] = re.sub(self.r[0], \
                        f'(({jitter_num}))', cell['source'], 1)

            if in_tests and bool(re.search(self.r[1], cell['source'])):
                all_match = re.finditer(self.r[1], cell['source'])

                for match in all_match:
                    notebook['cells'][idx]['source'] = re.sub(self.r[1], \
                        f'jv[ver][{question_counter}][{match.group(1)}]', cell['source'], 1)


        jtag_location = jtag_location[::-1]
        notebook['cells'].append(nbformat.v4.new_markdown_cell("<!--jtag-->"))
        for i in jtag_location:
            notebook['cells'].insert(i, nbformat.v4.new_markdown_cell("<!--jtag-->"))

        return ranges, notebook

    def _clean(self, match) -> tuple:
        """Cleans the regex matches and returns the ranges and length"""

        tmp = [re.sub(r'\(\(|\)\)', '', x.group()).split(',') for x in match]
        return ([[float(x) for x in y] for y in tmp], len(tmp))

    def _generate(self):
        jitter_values = {}

        for ver in range(self.versions):
            jitter_values[ver] = {}

            for question in self.ranges:
                jitter_values[ver][question] = []
                
                for i in self.ranges[question]:
                    tmp = choice(arange(*i))
                    
                    # if the value is an integer, cast it to an int
                    if int(tmp) == tmp:
                        jitter_values[ver][question].append(int(tmp))
                        continue
                    
                    jitter_values[ver][question].append(tmp)

        return jitter_values

    def full_modify(self, ver: int):
        """stuff"""
        question_index = 0

        new_notebook = self.assigned_nb

        for idx, cell in enumerate(new_notebook['cells']):
            if 'ver =' in cell['source']:
                tmp = cell['source'].split('\n')
                
                for i, line in enumerate(tmp):
                    if 'ver = ' in line:
                        tmp[i] = f'ver = {ver}'
                        new_notebook['cells'][idx]['source'] = '\n'.join(tmp)
                        break
            
            if '<!--jtag-->' in cell['source']:
                question_index += 1
                continue

            if bool(re.search(self.r[1], cell['source'])):
                
                all_match = re.finditer(self.r[1], cell['source'])

                for match in all_match:
                    new_notebook['cells'][idx]['source'] = re.sub(self.r[1], \
                            str(self.jitter_values[ver][question_index][int(match.group(1))]), \
                                    cell['source'], 1)

        return new_notebook
