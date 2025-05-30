from __future__ import annotations
from itertools import product
from functools import reduce
from typing import Dict, List, Any, Iterator
from filelock import FileLock
from string import Formatter

import os, sys, shutil, pickle, traceback, code, copy
import subprocess, datetime, warnings, dataclasses as dc
import multiprocess, polars as pl

from .shared import PROGRESS_DIR

@dc.dataclass 
class Dimension: 
	''' 
	A dimension consists of a unidirectional series of points 
	i.e. a list, for now – it can also be a range.
	'''
	points : List[Any | Dimension]

	def __iter__(self) -> Iterator[Any]:
		''' iterate over this dimension, flattening sub-dimensions '''

		for point in self.points:
			if isinstance(point, Dimension): yield from iter(point)
			elif isinstance(point, _Surface): yield from iter(point)
			else: yield point

	def __len__(self) -> int:
		''' return size of all dimensions '''
		n_points = 0 
		for point in self.points: 
			if isinstance(point, Dimension): n_points += len(point)
			elif isinstance(point, _Surface): n_points += len(point)
			else: n_points += 1
		return n_points 

	def __str__(self) -> str: 
		''' self.__logs points as list, or recurse into subdims '''
		nonsurface = ', '.join(
			f'*{point}' if isinstance(point, Dimension) else str(point)
			for point in filter(lambda x: not isinstance(x, _Surface), self.points)) 
		surface = ','.join(str(point) for point in filter(lambda x: isinstance(x, _Surface), self.points))
		
		if len(nonsurface) > 0 and len(surface) > 0:
			return nonsurface + ', ' + surface 
		elif len(nonsurface) > 0: 
			return nonsurface 
		else: 
			return surface 

from typing import TypeVar
T = TypeVar('T')

def search(*points: T) -> dc.Field[T]: 
	''' to be used within a Surface definition '''
	return dc.field(default_factory=lambda: Dimension(points))

def field(point: T) -> dc.Field[T]: 
	''' 
	A field that is for all purposes, static and immutable.
	Shorthand for dataclasses.field(default_factory=lambda: point)
	''' 
	return dc.field(default_factory = lambda: point)


@dc.dataclass 
class _Surface: 
	''' 
	A surface consists of at least two dimensions 
	i.e. multiple lists, and optional static points 
	'''
	pass

# TODO: apparently a process pool cannot spawn more process pools; 
# though huggingface is definitely using all 128 cores w/o asking me sometimes...

# TODO: i leave myself two options:
# 1. Store the process id and the currently running Settings in a file, 
# allowing the user to start another session, e.g. if more cores became 
# available. 

# 2. Write a dynamic process-scheduler, and provide the user with a 
# controller to simply change the number of cores in use. And then,
# in the future we can do some auto-scheduling with enough profiling. 
# we can totally do this and optimise for slurm quote & other servers. 

@dc.dataclass 
class Experiment(_Surface): 
	''' 
	Grid-search a dataclass. Has the following attributes:

	- `exp.name = Class-k`		Where k is a setting's index
	- `exp.debug = False`		Whether --debug was passed 
	- `exp.n_proc = 1`			Number passed to --n_proc
	- `exp.proc_id = 0 `		Current process index [0, n_proc)

	## Usage 
	```python
	@dataclass
	class Params(Experiment):
		a :int = search(1,2,3)
		b :str = 'b'
	```

	Calling .run_all() on an instance, or invoking via CLI, 
	will run all settings of `a`.
	'''
	__name		 :str = 'Experiment'
	__nested	:bool = dc.field(default=False, kw_only=True) # TODO: do we still need this field?

	__start_time: str = dc.field(init=False, default=datetime.datetime.now().strftime("%-Y%m%d-%H%M%S"))
	__debug		:bool = dc.field(init=False, default=False, kw_only=True)
	__n_proc	 :int = dc.field(init=False, default=1, kw_only=True)

	@property 
	def name(self) -> str:
		''' 
		Override this method to give a descriptive name to your experiment.
		You can use properties and variables in the name to identify it. 
		'''
		return self.__name if not self.__debug else '_' + self.__name 

	@name.setter 
	def name(self, name: str) -> None: 
		self.__name = name 

	@property 
	def proc_id(self) -> int:
		''' 
		Return the processor id in case of multiprocessing (between 1 - n_proc)
		returns 0 if disabled (main thread execution)
		'''
		return 0 if len(multiprocess.current_process()._identity) == 0 \
			else multiprocess.current_process()._identity[0]

	@property 
	def n_proc(self) -> int:
		''' 
		Return the variable passed to n_proc flag, 1 by default (no multiprocessing) 
		'''
		return self.__n_proc 

	@property 
	def debug(self) -> bool: 
		''' 
		Return whether the --debug flag was passed, False by default 
		'''
		return self.__debug

	def as_dict(self) -> dict[str, Any]:
		''' 
		Return a dictionary representation of this Experiment object
		'''
		# TODO: do we also convert sub-Experiments to dictionaries? 
		return {k:v for k,v in self.__dict__.items() if not k.startswith('_Experiment__')}

	def run(self) -> dict:
		''' 
		Run this experiment using the values defined in its class.
		Return a dict of results for it to be stored with the experiment name 
		'''
		raise NotImplementedError('You should override this method!')

	def __prompt_resume(self, resume, no_resume, clean):
		''' 
		If existing progress files are found and the --no-resume flag is not set,
		prompt the user whether they want to resume from last time
		'''
		progress_files_dir = os.path.dirname(self.progress_file)
		os.makedirs(progress_files_dir, exist_ok=True)
		progress_files = sorted(
			filter(lambda filename: '.progress' in filename and '.lock' not in filename, 
			os.listdir(progress_files_dir))
		)

		if clean:
			self.__log(f'Cleaning {len(progress_files)} progress files...')
			for old_progress_file in os.listdir(progress_files_dir):
				path = os.path.join(progress_files_dir, old_progress_file)
				if os.path.isfile(path): os.remove(path)
				else: shutil.rmtree(path)
			return []

		# if the user has not put in the no_resume flag, we want to prompt them to be sure
		if (not resume and no_resume) and not len(progress_files) == 0: 
			prompt = input('Found existing progress, do you want to resume? [Y/n] ')
			resume = prompt.strip().lower() == 'y' or prompt.strip() == ''

		# if resume, the __start_time attribute is set to the last run's
		if resume: 
			# can happen if the user cancelled their first experiment 
			# but still passes the --resume flag
			if len(progress_files) == 0: 
				self.__log(f'\033[1;93mNothing to resume from, starting new experiment\033[0m')

			else: 
				last_progress_file = progress_files[-1]
				self.__start_time = os.path.basename(last_progress_file).split('.')[0]
				self.__log(f'\033[1;93mresuming from {last_progress_file}\033[0m')

		finished_runs = []
		if resume and not len(progress_files) == 0: 
			finished_runs = [setting for setting in self.__get_progress() if not 'in progress' in setting]
		else: 
			# touch a new progress file
			with open(self.progress_file, 'a'): pass 

			# NOTE: this does not work if the user has added new runs to the experiment, 
			# but there is also no lazy way of tracking this, by design.
			# self.__log(f'\033[1mResuming... {self.__start_time}, {len(self) - len(finished_runs)} remaining\033[0m')

		return finished_runs

	def __set_up_logging(self):
		''' 
		Set up logging. I'm using tee to ensure we capture system stuff too
		taken from https://stackoverflow.com/questions/616645/how-to-duplicate-sys-stdout-to-a-log-file
		'''
		try: 
			tee = subprocess.Popen(['tee', '-a', self.log_file], stdin=subprocess.PIPE)
			# Cause tee's stdin to get a copy of our stdin/stdout (as well as that
			# of any child processes we spawn)
			os.dup2(tee.stdin.fileno(), sys.stdout.fileno())
			os.dup2(tee.stdin.fileno(), sys.stderr.fileno())

			self.__log(f'\033[90mPROGRESS FILE: \t{self.progress_file}\033[0m', flush=True)
			self.__log(f'\033[90mLOG FILE	  : \t{self.log_file}\033[0m', flush=True)
		except: 
			warnings.warn(
				'user does not have `tee` installed, will not log ',
				f'to {self.log_file} '
			)

	def __store_result(self, setting_name: str, result: dict | pl.DataFrame):
		''' 
		Store results if they were returned, thread safe. 
		'''
		if isinstance(result, dict): 
			assert all(not isinstance(v, dict) for v in result.values()), \
				'unnest the returned dictionary yourself into a pl.DataFrame'
			result = pl.from_dicts([result])

		# add the setting name in case the user forgot
		if not any(
			col.dtype == pl.String and setting_name in col 
			for col in result.iter_columns()
		):
			result = result.with_columns(setting = pl.lit(setting_name))

		with FileLock(self.result_file + '.lock'): 
			try: 
				results = pl.concat([
					pl.read_parquet(self.result_file), 
					result, 
				], how = 'diagonal_relaxed')
			except: 
				results = result
			results.write_parquet(self.result_file)

		self.__log(results)
		return results

	def __store_progress(self, setting_name):
		''' 
		Store progress, thread safe. 
		'''

		progress_lock = FileLock(self.progress_file + '.lock')
		with progress_lock: 
			with open(self.progress_file, 'a') as progress_file:
				self.__log(setting_name, file=progress_file)

	def __get_progress(self) -> list:
		''' 
		Get progress so far, thread safe. 
		'''
		progress_lock = FileLock(self.progress_file + '.lock')
		with progress_lock: 
			with open(self.progress_file, 'r') as progress_file: 
				progress = [line.strip() for line in progress_file.readlines()]
		return progress

	def __store_exception(self, setting_name, exception, debug):
		'''
		Store exception in self.exc_file
		If --debug flag is passed, attempts to open a debugger shell at the 
		point of error. 
		'''

		# oh boy this is an interpreted language, let's use it.
		if debug: 
			extype, value, tb = sys.exc_info()
			try: 
				import pdb; pdb.post_mortem(tb)
			except: 
				self.__log('\033[1;31mcould also not activate `pdb` debugger\033[0m')

			try: 
				last_frame = lambda tb=tb: last_frame(tb.tb_next) if tb.tb_next else tb
				frame = last_frame().tb_frame
				ns = dict(frame.f_globals)
				ns.update(frame.f_locals)
				code.interact(local=ns)
				return
			except: 
				self.__log('\033[1;31mcould not activate `code` debugger, trying `pdb`\033[0m')
				pass

		exc_time = datetime.datetime.now()

		exception_lock = FileLock(self.exc_file + '.lock')
		with exception_lock: 

			with open(self.exc_file, 'a') as exc_file:
				self.__log(f'{setting_name} {exc_time.isoformat()}', file=exc_file, flush=True)

			with open(self.exc_file, 'r') as exc_file:
				exceptions = {setting: datetime.datetime.fromisoformat(time.strip()) for setting, time in \
							  map(lambda line: line.split(maxsplit=1), exc_file.readlines())}
				
		exception_log_lock = FileLock(self.exc_log_file + '.lock')
		with exception_log_lock:
			with open(self.exc_log_file, 'a') as exc_log_file:
				self.__log(f'\n\n{setting_name} {exc_time.isoformat()}', file=exc_log_file)
				self.__log(traceback.format_exc(), file=exc_log_file)


		# TODO: it would be really cool if we could fork the process, 
		# keep running the rest of the experiments, and set a pdb post-mortem 
		# See Accepted Answer on SO: https://stackoverflow.com/questions/242485/starting-python-debugger-automatically-on-error

		exception_times = list(exceptions.values())
		if len(exceptions) >= 3 and (exception_times[-1] - exception_times[(max(len(exception_times) - 4, 0))]).seconds < 3*60:
			self.__log(f'\033[1;31mThree exceptions in three minutes, quitting\033[0m')
			raise ChildProcessError('3 Exceptions in 3 minutes, quitting') from exception

	def __run_setting(self, index:int, setting:Experiment, finished_runs: list, debug=False, rerun=False):
		''' 
		Run setting on one process, with error handling and progress tracking
		'''
		# TODO: logging to multiple files to not clutter the one to bits 

		setting.__n_proc = self.__n_proc
		index += 1 # for natural language indexing
		# self.__log(f'{index:04d}: {multiprocess.current_process()._identity[0]}')

		try: 
			if not rerun and setting.name in finished_runs: 
				self.__log(f'Skipping {index}: \033[1m{setting.name}\033[0m')
				return

			# run setting. if it fails, just continue.
			self.__log(f'\nRunning setting {index}: \n{setting}')
			result = setting.resume() if hasattr(setting, 'resume') else setting.run()
			self.__log(f'\nDone with {index}: \033[1m{setting.name}\033[0m\n')

			if isinstance(result, dict) or isinstance(result, pl.DataFrame):
				self.__store_result(setting.name, result)
			self.__store_progress(setting.name)
			return

		except Exception as e: # let the user know we're skipping this setting
			# it can happen that the experiment fails during name initialisation
			# let's accomomdate to the user and still continue running the rest
			try: name = setting.name 
			except: name = f'experiment setting with index {index}'

			self.__log(f' \033[1;31m!!!\033[0m\t\033[1m{name}\033[31m failed \033[0m\n{traceback.format_exc()}')
			self.__store_exception(setting.name, e, debug) # can raise Exception: too many failures

		# cleanup memory
		del setting

	def run_all(self, resume=False, no_resume=False, n_proc=1, debug=False, clean=False, rerun=False):
		''' 
		Run all settings in this Experiment, saving progress to self.progress_file 
		and logging to self.log_file. 
		Optionally, specify whether to resume from last time.
		'''
		# TODO: Start a tmux session and log to different panes. 
		# Start pdb on a new pane if an exception is raised. 

		# TODO: Allow user to modify the Experiment while it is still running, 
		# and launch a separate instance of the same experiment. 
		# This requires tracking in-progress runs

		finished_runs = self.__prompt_resume(resume, no_resume, clean)

		all_names = [setting.name for setting in copy.deepcopy(self)]
		duplicates = set([name for name in all_names if all_names.count(name) > 1])
		assert len(duplicates) == 0, f'All settings must have unique names! Duplicates: \n{duplicates}'

		self.__set_up_logging()
		if not len(self) == 1: 
			self.__log((
				f'Running '
				'debug ' if debug else '' 
				'experiment with following settings'
				f' on {n_proc} procs:' if n_proc > 1 else ':'
				f'\n{self}'
			), flush=True)

		# todo: expose to user
		self.__debug = debug 
		self.__n_proc = n_proc
		self.__rerun = rerun

		if n_proc == 1:
			# run all settings in this experiment (i.e. perform grid search)
			for index, setting in enumerate(self):
				self.__run_setting(index, setting, finished_runs, debug, rerun)
		else: 
			with multiprocess.Pool(n_proc) as pool:
				iterator = map(lambda tup: (*tup, finished_runs, debug, rerun), enumerate(self))
				pool.starmap(self.__run_setting, iterator, chunksize=1)

		if hasattr(self, 'format_results'): # custom results display defined by user
			result_lock = FileLock(self.result_file + '.lock')
			with result_lock:
				try: results = pl.read_parquet(self.result_file)
				except: 
					self.__log(f'\033[1;31mWARNING: no results found!\033[0m') 
					return

			results: pl.DataFrame = self.format_results(results)
			if results is not None: 
				results.write_parquet(self.result_file.replace('.parquet', '_formatted.parquet'))

	def __post_init__(self): 
		''' 
		1. allows you to declare fields inline when instantiating an Experiment(), 
		   wrapping the mutables in a Field (field(default_factory=lambda: mutable))
		   TODO: not sure this works as intended.
		2. sets sub-Surfaces as nested; to indicate they should be searched as part
		   of the parent 
		   TODO: can't remember whether this was actually necessary.
		3. tries to format f-strings that appear in the setting's attributes, if 
		   they are formattable. Convenient for defining setting-dependent strings.
		'''

		# set name of the main experiment object to the class the user defined
		self.__name = self.__class__.__name__

		uninitialised_fields = {name: _field for \
			name, _field in self.__dict__.items() if isinstance(_field, dc.Field)
		}
		for name, _field in uninitialised_fields.items():
			setattr(self, name, _field.default_factory())

		# self.__log(f'\nPOST INIT for {self.__class__.__name__}')
		# self.__log('\n'.join(f'{k}: {type(v)}' for k,v, in self.__items))

		''' 2. set fields as nested, to not track progress in nested classes '''
		for k, v in self.__items:
			if isinstance(v, _Surface):
				v.__nested = True 

		''' 3. format attribute strings '''
		# per string field, collect the names necessary to format the string
		string_fields = {name: (string, [name for _, name, _, _ in Formatter().parse(string) if name is not None]) \
						 for name, string in self.__dict__.items() if isinstance(string, str)}

		for name, (string, names) in string_fields.items():
			try:
				kwargs = {}
				for v_name in names: 
					if not isinstance(getattr(self, v_name), Dimension): 
						kwargs[v_name] = getattr(self, v_name)
				setattr(self, name, string.format(**kwargs))
			except: pass

		# create experiment dir on init 
		os.makedirs(self.experiment_dir, exist_ok=True)

	def __log(self, message, flush=True, file=None) -> None:
		''' 
		because I can't be bothered to write if elses everywhere 
		'''
		if os.environ.get('LOCAL_RANK', 0) == 0: 
			print(message, flush=flush, file=file)

	def __str__(self) -> str: 
		'''
		Return a string representation of this experiment/setting,
		with variables highlighted in purple in case of an Experiment.
		'''
		string = f'\n\033[1;93m{len(self):3} {self.name}\033[0m'

		max_k_len = max(map(len, self.__dict__.keys()))
		for k,v in self.__items: 
			# in case of a multiline value (from a Surface), we pad the block
			v_string = '\n	  '.join(str(v).splitlines()) 

			# dimensions in purple to make it clear to the user 
			if isinstance(v, Dimension) or isinstance(v, _Surface):
				string += '\n \033[1;95m{:2} {:{}s}: [\033[0m {} \033[95;1m]\033[0m'.format(
					len(v), k, max_k_len, v_string
				)
			else:
				string += '\n {:2} \033[1m{:{}s}\033[0m: {}'.format(
					1, k, max_k_len, v_string
				)

		return string + '\n'

	def __len__(self) -> int:
		'''
		Return number of settings in this experiment.
		'''
		return reduce(
				lambda a,b: a*b, 
				map(
					len,
					(d for d in self.__dimensions.values()) 
			), 1
		) 

	def __iter__(self) -> Iterator[_Surface]:
		'''
		Iterate over settings in this experiment.
		'''
		keys = self.__dimensions.keys()
		for i, instance in enumerate(product(*[v for v in self.__dimensions.values()])):
			point = self.__class__(**self.__static_points, **dict(zip(keys, instance)))
			
			point.__name = point.clean_class_name + f'-{i}'
			yield point


	@property 
	def __items(self):
		''' 
		Returns all items in this class, except dunders 
		'''
		return {k:v for k,v in self.__dict__.items() if not k.startswith('_Experiment__')}.items()

	@property 
	def __static_points(self) -> Dict[str, Any] :
		''' 
		Dictionary of { var_one: Any, var_two: Any, ... } 
		'''
		return {k:v for k,v in self.__items if not isinstance(v, Dimension) and not isinstance(v,_Surface)}

	@property 
	def __dimensions(self) -> Dict[str, Dimension]:
		''' 
		Dictionary of { var_one: Dimension, var_two: Dimension, ... } 
		'''
		return {k:v for k,v in self.__items if isinstance(v,Dimension) or isinstance(v,_Surface)}

	@property 
	def clean_class_name(self) -> str:
		''' 
		Clean class name (without experiment index) 
		'''
		classname = self.__class__.__name__
		return classname.split('-')[0] if '-' in classname else classname

	@property 
	def experiment_dir(self) -> str: 
		'''
		Output directory in experiments/progress/filename/Classname/
		'''
		return os.path.join(
			PROGRESS_DIR, 
			self.__module__.split('.')[-1],
			self.clean_class_name,
		)

	@property 
	def __experiment_file(self) -> str: 
		''' 
		Used for storing the below files.
		'''
		return os.path.join(self.experiment_dir, f'{self.__start_time}')

	@property
	def progress_file(self) -> str:
		''' 
		Progress is stored by saving experiment index to
		experiments/progress/filename/Classname/YYYYMMDD-HHMMSS.progress
		'''
		return self.__experiment_file + '.progress'

	@property 
	def result_file(self) -> str : 
		''' 
		Results are stored in a dataframe at the path:
		experiments/progress/filename/Classname/YYYYMMDD-HHMMSS.parquet
		'''
		return self.__experiment_file + '.parquet'

	@property 
	def log_file(self) -> str:
		''' 
		Log everything! A copy of terminal output is stored at
		experiments/progress/filename/Classname/YYYYMMDD-HHMMSS.log
		'''
		return self.__experiment_file + '.log'

	@property 
	def exc_file(self) -> str: 
		''' 
		Experiment indices that had an Exception are stored at 
		experiments/progress/filename/Classname/YYYYMMDD-HHMMSS.exceptions
		'''
		return self.__experiment_file + '.exceptions'

	@property 
	def exc_log_file(self) -> str: 
		''' 
		Exception stack traces are stored at 
		experiments/progress/filename/Classname/YYYYMMDD-HHMMSS.exceptions.log
		'''
		return self.__experiment_file + '.exceptions.log'

