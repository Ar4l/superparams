''' 
testing sibling imports. 
ideally calling experiment from cli is as intuitive as 

python -m experiment_dir.sub_dir.file.class
'''

import os, sys 

def add(a:int, b:int) -> int:
	# test whether the package is navigable both
	# with absolute and relative imports 

	paths = '\n'.join(sys.path)
	print(f'''
	\033[1mFUN CALL {__file__} in {__package__}\033[0m
	cwd: {os.getcwd()}
	path: {paths}
	''', flush=True)

	import subdir.subdir_lib
	from subdir.subdir_lib import mult

	# todo: relative imports 
	# from .subdir.subdir_lib import mult
	
	return a + b


if __name__ == '__main__': 
	print(add(1,2))
