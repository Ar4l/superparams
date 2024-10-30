import subprocess, glob, shutil

PROGRESS_DIR = 'tests/experiments/progress/'

def test_cli():

	command = ''' 
	experiment dummy.Dummy --no-resume
	'''.strip()

	subprocess.check_call(f'''
		cd tests/experiments
		uv run -- {command}
	'''.strip(), shell=True)

	with open(glob.glob(PROGRESS_DIR + 'dummy/Dummy/*.progress')[0]) as f:
		n_experiments = len(f.readlines())

	from tests.experiments.dummy import Dummy
	assert len(Dummy()) == n_experiments

	# cleanup
	shutil.rmtree(PROGRESS_DIR)
