'''
Whether we can 
1. return a dictionary
2. return a pl.DataFrame

pytest throws a tantrum with these tests, I've got no clue why
just run this file as a module
'''

import dataclasses as dc
import superparams as sp, polars as pl, pytest 

formatted_results: bool = False

@dc.dataclass 
class Params(sp.Experiment):
	a :int = sp.search(1,2)
	b :int = sp.search(3,4)

	def run(self):
		return pl.DataFrame(self.as_dict())
	def format_results(self, results: pl.DataFrame): 
		print(results)

		global formatted_results
		formatted_results = True


def return_dataframe(): 

	params = Params()
	params.run_all()
	results = pl.read_parquet(params.result_file)

	expected = pl.from_repr('''
		shape: (4, 3)
		┌─────┬─────┬──────────┐
		│ a   ┆ b   ┆ setting  │
		│ --- ┆ --- ┆ ---      │
		│ i64 ┆ i64 ┆ str      │
		╞═════╪═════╪══════════╡
		│ 1   ┆ 3   ┆ Params-0 │
		│ 1   ┆ 4   ┆ Params-1 │
		│ 2   ┆ 3   ┆ Params-2 │
		│ 2   ┆ 4   ┆ Params-3 │
		└─────┴─────┴──────────┘
	''')
    
	assert all(col.all() for col in (results == expected)), \
		f'{results} != {expected}: \n{results == expected}'

	assert formatted_results, \
		'format_results() was not called in run_all()'

def return_dict():

	@dc.dataclass
	class DictParams(Params): 

		constant: str = 'constant'
		nullable: str = sp.search(None, 'a')

		name: str = '{a}-{b}-{nullable}'

		def run(self):
			return self.as_dict()

	params = DictParams()
	params.run_all()
	results = pl.read_parquet(params.result_file)

	expected = pl.from_repr('''
		shape: (8, 5)
		┌─────┬─────┬──────────┬──────────┬──────────┐
		│ a   ┆ b   ┆ constant ┆ nullable ┆ name     │
		│ --- ┆ --- ┆ ---      ┆ ---      ┆ ---      │
		│ i64 ┆ i64 ┆ str      ┆ str      ┆ str      │
		╞═════╪═════╪══════════╪══════════╪══════════╡
		│ 1   ┆ 3   ┆ constant ┆ null     ┆ 1-3-None │
		│ 1   ┆ 3   ┆ constant ┆ a        ┆ 1-3-a    │
		│ 1   ┆ 4   ┆ constant ┆ null     ┆ 1-4-None │
		│ 1   ┆ 4   ┆ constant ┆ a        ┆ 1-4-a    │
		│ 2   ┆ 3   ┆ constant ┆ null     ┆ 2-3-None │
		│ 2   ┆ 3   ┆ constant ┆ a        ┆ 2-3-a    │
		│ 2   ┆ 4   ┆ constant ┆ null     ┆ 2-4-None │
		│ 2   ┆ 4   ┆ constant ┆ a        ┆ 2-4-a    │
		└─────┴─────┴──────────┴──────────┴──────────┘
	''')

	assert all(col.all() for col in (results == expected)), \
		f'{results} != {expected}: \n{results == expected}'

if __name__ == '__main__':
	return_dataframe()
	return_dict()
