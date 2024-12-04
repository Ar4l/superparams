
from superparams import Experiment, search
from dataclasses import dataclass

@dataclass 
class Debug(Experiment):
	''' verify debug flag is passed '''

	a :int = 1

	def run(self):
		return {
			'debug': self.debug
		}



