import os
import pathlib
import re

import nbformat
from numpy import arange
from numpy.random import choice

class Jitter:
    """Jitter class that takes in a master notebook and the number of versions"""
    def __init__(self, path: pathlib.Path, versions: int = 1):
        self.path = path
        self.versions = versions
        self.ranges, self.clean_nb = self._get_ranges()
        self.jitter_values = self._generate()
        self.assigned_nb = None


    def _get_ranges(self):
        """ Finds the values to be jittered and stores the
            cleaned notebook and values in the object"""

        notebook = nbformat.read(self.path, as_version=4)

        regex = r'\(\(\d+?,([\s])?\d+?([\,]([\s])?\d+?(.\d+?)?)?\)\)'

        ranges = {}
        question_name = ''
        has_jitter = False

        for idx, cell in enumerate(notebook['cells']):
            if '# ASSIGNMENT CONFIG' in cell.source:
                mod_cell = cell.source.split('\n')
                
                if not any('files' in line for line in mod_cell):
                    mod_cell.append('files:')
                
                if not any('- jv.pkl' in line for line in mod_cell):
                    for i, line in enumerate(mod_cell):
                        if 'files' in line:
                            mod_cell.insert(i+1, ' ' * 4 + '- jv.pkl')
                            break
                
                notebook.cells[idx].source = '\n'.join(mod_cell)
            
            if '# BEGIN QUESTION' in cell['source'].upper():
                question_name = [line.split(':')[1] for line in cell['source'].split('\n') \
                    if 'name' in line.lower()][0].strip()
                ranges[question_name] = []

                if 'jitter' in cell['source'].lower():
                    has_jitter = [line.split(':')[1] for line in cell['source'].split('\n') \
                        if 'jitter' in line.lower()][0].strip().lower() == 'true'

            elif '# END QUESTION' in cell['source'].upper() or not has_jitter:
                # reset to default values when current question ends
                question_name = ''
                has_jitter = False
                continue

            if has_jitter:
                if bool(re.search(regex, cell['source'])):
                    local_ranges, length = self._clean(re.finditer(regex, cell['source']))
                    ranges[question_name].extend(local_ranges)

                    for jitter_num in range(length):
                        notebook['cells'][idx]['source'] = re.sub(regex, \
                            f'(({jitter_num}))', cell['source'], 1)


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

    def full_modify(self, cur_ver: int):
        """stuff"""
        full_regex = r'\(\(\d+?,([\s])?\d+?([\,]([\s])?\d+?(.\d+?)?)?\)\)'
        regex = r'\(\(\d+?\)\)'
        question_name = ''

        new_notebook = self.assigned_nb

        for idx, cell in enumerate(new_notebook['cells']):
            if 'ver =' in cell['source']:
                tmp = cell['source'].split('\n')
                
                for i, line in enumerate(tmp):
                    if 'ver = ' in line:
                        tmp[i] = tmp[i].replace('0', str(cur_ver))
                        new_notebook['cells'][idx]['source'] = '\n'.join(tmp)
                        break
            
            
            if 'question' in cell['source'].lower():
                question_name = 'q' + re.search(r'Question\s(\d+)', cell['source']).group(1)

            while bool(re.search(regex, cell['source'])):
                all_match = re.finditer(regex, cell['source'])

                for match in all_match:
                    new_notebook['cells'][idx]['source'] = re.sub(regex, \
                        str(self.jitter_values[cur_ver][question_name][int(match.group()[2:-2])]), \
                            cell['source'], 1)
        return new_notebook

def version_handler(nb_path, versions: int = 1):
    """ Handles and creates the multiple versions of the notebook"""
    ver_folder = pathlib.Path(f'{nb_path.parent}/versions')
    ver_folder.mkdir(parents=True, exist_ok=True)

    jitter = Jitter(nb_path, versions)

    for i in range(versions):
        nbformat.write(jitter.full_modify(i), \
            f'{ver_folder}/{str(nb_path.name).split(".", maxsplit=1)[0]}_v{i}.ipynb')

    return jitter.jitter_values


if __name__ == '__main__':
    master = pathlib.Path(os.path.abspath('jitter/jitter_base_assignment.ipynb'))

    print(version_handler(master))
