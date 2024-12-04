from .experiment import Experiment, search, field

def main(): 
	import argparse, importlib, sys, os, pickle, dataclasses
	from .experiment import Experiment as ExperimentClass
	from .shared import EXPERIMENTS_DIR

	# parse inputs
	parser = argparse.ArgumentParser()
	parser.add_argument('experiment', help = 'module.Experiment to run')
	parser.add_argument('--resume', default=False, action = 'store_true', help = 'resume last run?')
	parser.add_argument('--no-resume', action = 'store_false', help= 'no resume prompt?')
	parser.add_argument('--n_proc', type=int, default=1, help = 'multiprocessing?')
	parser.add_argument('--debug', action='store_true', help = 'enter pdb on error?')
	parser.add_argument('--clean', action='store_true', help = 'clean the progress for this experiment?')
	parser.add_argument('--rerun', action='store_true', help = 'rerun the experiment? (saves to same parquet)')
	parser.add_argument('--from_pickle', help='load a pickled Experiment, intended for programmatic control')
	args, unknown = parser.parse_known_args()

	# To find the experiment:
	# 1. check if we are already in a EXPERIMENTS_DIR. 
	#		if yes, add the parent dir to the sys.path 
	#		so that the package is recognised by the interpreter 
	#
	#		(this assumes EXPERIMENTS_DIR is only one level deep, 
	#		 but so does `python -m`)
	#
	#		 Then, update the progress_dir to be inside EXPERIMENTS_DIR
	#
	# 2. check if EXPERIMENTS_DIR is present in the cwd and cd into it 
	#		cool we should be in the top-level package.
	#		though there is no real way to be sure, in case EXPERIMENTS_DIR
	#		is more than one level deep 

	# if the user is inside the experiments directory 
	# (which we assume to be only one level deep in the package), 
	# then add the package root to sys.path 

	is_experiments_dir = lambda dirname: \
		os.path.basename(dirname) == EXPERIMENTS_DIR
	cwd = os.getcwd()

	package_path = os.path.dirname(cwd) if is_experiments_dir(cwd) else cwd
	sys.path.insert(0, package_path)

	module, experiment_class = args.experiment.rsplit('.', maxsplit=1)

	if not module.split('.')[0] == EXPERIMENTS_DIR: 
		module = f'{EXPERIMENTS_DIR}.{module}'

	# todo: for relative imports 
	# this __package__ is indeed the top-level package 
	# but I don't know if that is because we are in the superparams package, 
	# or whether it's working as intended. Probably need to test this 
	# in another repository to be sure

	# paths = '\n'.join(sys.path)
	# print(f'''
	# \033[1mhello, from {__file__} in {__package__}\033[0m
	# cwd: {os.getcwd()}
	# module: {module}
	# exp:	{experiment_class}
	# path: {paths}
	# ''', flush=True)

	# import the Experiment
	module = importlib.import_module(module)
	Experiment : ExperimentClass = getattr(module, experiment_class)

	# load extra kwargs into an Experiment
	if len(unknown) > 0: 
		# thanks to the fact that it's a dataclass, we can use the (potentially uninitialised) 
		# fields to determine what type to cast the unknown (Experiment-specific) args to. 
		field_types = {field.name: field.type for field in dataclasses.fields(Experiment)}
		unknown_kwargs = {}

		for k, v in zip(unknown[::2], unknown[1::2]):
			k = k.strip('-')
			if k not in field_types: 
				raise ValueError(f'{k} does not exist in {Experiment}')

			unknown_kwargs[k] = field_types[k](v)
		experiment_class = Experiment(**unknown_kwargs)

	# base: assume all experiment attributes are defined in its class
	else: 
		experiment_class = Experiment()

	experiment_class.run_all(
		resume=args.resume, no_resume=args.no_resume, 
		n_proc=args.n_proc, debug=args.debug,
		clean=args.clean, rerun=args.rerun,
	)
