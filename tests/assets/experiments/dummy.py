
from superparams import Experiment, search
from dataclasses import dataclass

@dataclass 
class SubClass(Experiment):
	c: int = -1

@dataclass 
class Other(Experiment):
	string: str = search('a', 'b')

@dataclass 
class Dummy(Experiment):

	a :int = 1
	b :int = search(2,3)
	c :SubClass = search(*[SubClass(c=i) for i in range(3)])
	d :Other = search(Other())

	def run(self):
		return {
			'ab': self.a * self.b,
			'cd': self.d.string * self.c.c 
		}

	# todo: assert error thrown in duplicate names


