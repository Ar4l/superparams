from .experiment import Experiment, search 

def main(): 
	import argparse, importlib, sys, os, pickle, dataclasses
	from .experiment import Experiment as ExperimentClass

	# print(f'''
	# hello, from {__file__}
	# cwd: {os.getcwd()}
	# ''', flush=True)

	# parse inputs
	parser = argparse.ArgumentParser()
	parser.add_argument('experiment', help = 'module.Experiment to run')
	parser.add_argument('--resume', default=False, action = 'store_true', help = 'resume last run?')
	parser.add_argument('--no-resume', action = 'store_false', help= 'no resume prompt?')
	parser.add_argument('--num_proc', type=int, default=1, help = 'multiprocessing?')
	parser.add_argument('--debug', action='store_true', help = 'enter pdb on error?')
	parser.add_argument('--clean', action='store_true', help = 'clean the progress for this experiment?')
	parser.add_argument('--rerun', action='store_true', help = 'rerun the experiment? (saves to same parquet)')
	parser.add_argument('--from_pickle', help='load a pickled Experiment, intended for programmatic control')
	args, unknown = parser.parse_known_args()

	# Python does not seem to include editable packages in the env 
	# when invoking via CLI provided by __main__.py
	sys.path.insert(
		0, 
		'',
	)

	# import the Experiment
	module, experiment = args.experiment.rsplit('.', maxsplit=1)
	module = importlib.import_module(module)
	Experiment : ExperimentClass = getattr(module, experiment)

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
		experiment = Experiment(**unknown_kwargs)

	# base: assume all experiment attributes are defined in its class
	else: 
		experiment = Experiment()


	experiment.run_all(
		resume=args.resume, no_resume=args.no_resume, 
		num_proc=args.num_proc, debug=args.debug,
		clean=args.clean, rerun=args.rerun,
	)
