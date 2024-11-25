import os 

# search for classes in this directory
EXPERIMENTS_DIR = 'experiments'

PROGRESS_DIR = (
	'progress/' 
	if os.path.basename(os.getcwd()) == EXPERIMENTS_DIR
	else f'{EXPERIMENTS_DIR}/progress/'
)



