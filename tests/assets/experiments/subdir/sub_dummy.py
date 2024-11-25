from superparams import Experiment, search
from dataclasses import dataclass

import os, sys 
paths = '\n'.join(sys.path)
print(f'''
\033[1mhello, from {__file__} in {__package__}\033[0m
cwd: {os.getcwd()}
path: {paths}
''', flush=True)


# test imports from the package root (assets), 
# to ensure they work
from sibling_lib import add 
from subdir.subdir_lib import mult

@dataclass 
class Dummy(Experiment):

	a :int = 1
	b :int = search(2,3)

	def run(self):
		return {
			'ab': mult(self.a,self.b), 
			'a+b': add(self.a,self.b),
		}
 
	# todo: assert error thrown in duplicate names


print(f'imported {add} and {mult}')
