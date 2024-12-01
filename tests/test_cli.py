''' 
when invoking from cli, we mainly want to be sure of
two things: 

1.  directories are navigated and created correctly
	i.e. experiments are found & progress dir is 
	created in the correct location 

2.  cli args work as intended. 
'''

import os, time, warnings, subprocess, glob, shutil, itertools

PROGRESS_DIR = 'tests/assets/experiments/progress/'

def verify_experiment(cls): 
	''' verifies an experiment's progress dir is created and the full 
		experiment is ran (according to *.progress file)
	'''

	progress_dir = os.path.join(
		PROGRESS_DIR, 
		cls.__module__.rsplit('.', maxsplit=1)[-1], 
		cls.__name__, 
	)
	assert os.path.isdir(progress_dir), f'no progress dir at {progress_dir}'

	files = glob.glob(os.path.join(
		progress_dir,
		'*.progress'
	))
	assert len(files) >= 1, f'no *.progress file created in {progress_dir}'

	with open(sorted(files)[-1]) as f: 
		n_experiments = len(f.readlines())

	experiment = cls()
	assert len(experiment) == n_experiments, \
		f'n experiments ({n_experiments}) does not match class def ' \
		f'({len(experiment)}) for {cls}'

	# cleanup
	warnings.warn(UserWarning(f'\033[1mdeleting {progress_dir}\033[0m'))
	time.sleep(1)
	shutil.rmtree(progress_dir)
	# wait at least 1 second


def test_cli(): 
	''' 
	Check if we can run experiments from the root dir and within 
	the experiments dir, supporting both module and shorthand
	experiment definitions: 
		dummy.Dummy 
		experiment.dummy.Dummy
	'''

	from tests.assets.experiments.dummy import Dummy

	# using --no-resume to avoid interactivity
	commands = [
		'experiment dummy.Dummy --no-resume', 
		'experiment experiments.dummy.Dummy --no-resume',
	]
	locations = [ 'tests/assets', 'tests/assets/experiments' ] 

	for location, command in itertools.product(locations, commands): 
		subprocess.check_call(f'''
			cd {location} 
			uv run -- {command}
		'''.strip(), shell=True)

		verify_experiment(Dummy)


def test_cli_with_imports(): 
	''' 
	Check if an experiment can correctly import library assets 
	from sibling directories to the experiments dir

	I.e. verify that we set up the experiment in the correct package
	'''
	import sys, os 

	# assuming tests are ran from the repo root, we want to 
	# add our assets dir (mock package) to the pythonpath 
	# to properly import the classes for experiments
	sys.path.insert(0, os.path.abspath('tests/assets'))
	from tests.assets.experiments.subdir.sub_dummy import Dummy

	# using --no-resume to avoid interactivity
	commands = [
		'experiment subdir.sub_dummy.Dummy --no-resume', 
		'experiment experiments.subdir.sub_dummy.Dummy --no-resume',
	]
	locations = [ 'tests/assets', 'tests/assets/experiments' ] 

	for location, command in itertools.product(locations, commands): 
		subprocess.check_call(f'''
			cd {location} 
			uv run -- {command}
		'''.strip(), shell=True)

		verify_experiment(Dummy)
 
