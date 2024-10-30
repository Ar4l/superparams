
import pytest 

from dataclasses import dataclass
from superparams import Experiment, search

def test_empty(): 
	@dataclass 
	class Params(Experiment): 
		pass 
	assert len(Params()) == 1 

def test_single():
	@dataclass
	class Params(Experiment):
		value: int = 3
		other: int = search(1)

	assert len(Params()) == 1

def test_multiple():
	@dataclass 
	class Params(Experiment):
		a :int = search(1,2)
		b :int = search(3,4)

	params : list[Params] = [p for p in Params()]
	assert len(params) == 4

	for param in params:
		assert len(param.as_dict()) == 2 
		assert param.a == 1 or param.a == 2
		assert param.b == 3 or param.b == 4

def test_recursive():

	@dataclass 
	class SubParams(Experiment):
		a :int = search(1,2)
		b :int = 3

	@dataclass 
	class Params(Experiment):
		c	:int		= search(4,5)
		sub :SubParams	= search(SubParams(), SubParams())

	for param in Params():
		assert param.sub.a == 1 or param.sub.a == 2 
		assert param.sub.b == 3 
		assert param.c == 4 or param.c == 5
		assert len(param.as_dict())

def test_readme():
	''' ensure code samples on the readme pass ''' 

	from dataclasses import dataclass
	from superparams import Experiment, search

	@dataclass
	class Hyperparams(Experiment):

		steps         :int = 100
		batch_size    :int = search([16, 32])

		def run(self) -> dict:
			''' Runs this setting of parameters (override this method)
				Auto-stores the returned dict in a parquet.
			'''

			results = {
				'total samples': self.batch_size * self.steps
			}
			print(results)

			# automatically save results in a parquet file by returning them 
			return results

	for h in Hyperparams():
		print(h)

# def test_
## TODO: test
# - no params
# - single param
# - multiple params
# - search 1 param
# - search no params 
# - search multiple params
# - recursive structures!! 

# class Hyperparams(Search):
#     learning_rate: float = 3
#     batch_size: int      = 32
#     epochs: int          = 3

