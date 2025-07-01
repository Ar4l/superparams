## superparams
<!--
a Pythonic approach to Hyperparameter Search. Using built-in `dataclasses`, as they are flexible, typed, easily-serialisable, and are a `dict` in the places you need them. 

> I like to think of it as the repetitive back-logic for flexible, fast searching of any search space. 

#### Key Features 
--> 

A high-level experiment manager. 

- 📄 One Python file for your entire experiment, flexible and easily versionable.
- 💚 No boilerplate like parsing a text file with configuration variables, multiprocessing code, nor logging/saving results. 
- ♻️ Easily re-run failed experiment settings. 

#### Installation

```bash
pip install superparams
```

View on [PyPi](https://pypi.org/project/superparams/).


#### Usage 
Superparams incentivises use of Python's built-in `dataclass` to specify both the parameters and the experiment-specific logic in one place. It bundles this with a bunch of quality-of-life improvements for managing your experiments. 

```python 
# file: experiments/params.py

import dataclasses as dc
import superparams as sp 

@dc.dataclass
class Hyperparams(sp.Experiment):

    steps         :int = 100
    batch_size    :int = sp.search(16, 32)

    # and automatic string substitution!
    dataset_path  :str = 'data/raw/{dataset_name}'
    dataset_name  :str = sp.search('alphabet', 'numbers')

    def run(self) -> dict | pl.DataFrame:
        ''' 
        Runs this setting of parameters (override this method)
        Auto-stores the returned dict/pl.DataFrame in a parquet table.
        '''

        results = {
            'total samples':  self.batch_size * self.steps, 
            'path':           self.dataset_path
        }
        print(results)

        # automatically save results in a parquet file by returning them 
        return results

    def format_results(self, results: pl.DataFrame) -> None | pl.DataFrame:
        ''' 
        Useful for plotting and post-processing, 
        optionally can return formatted dataframe to be saved 
        '''
        results.plot.bar('path', 'total_samples').show()
```

This constructs an iterator to _grid-search_ the parameter settings, 
meaning you could add a snippet like the following to invoke your experiment 
from the terminal with `python -m experiments.params`.

```python
# file: experiments/params.py

if __name__ == '__main__':
    for h in Hyperparams():
        results = h.run()
        print(f'Setting ({h.steps}, {h.batch_size}): {results}')
        # Setting (100, 16): {'total_samples': 1600}
        # Setting (100, 32): {'total_samples': 3200}
```

But _we promised no boilerplate_! Instead, you can invoke from the terminal,
which handles result-caching for you, and enables easy multiprocessing. 

```bash
experiment params.Hyperparams --n_proc 2
```

This will:

1. print a nice overview of the running experiments
2. store results and log under `experiments/progress/params/Hyperparams`
3. prompt you to resume interrupted/failed experiment settings 
4. do the multiprocessing for you :)

> [!WARNING]
> Python-native `multiprocessing` shares the `Hyperparams` data with each process *by pickling it!*. This is woefully inefficient, and poses a massive bottleneck if sharing >10MB data. Consider refactoring such that each `run` method instantiates this data itself.
>
> In the future, I may do a refactor that shares the data more efficiently; but this is not trivial in Python and definitely not possible in all cases. See [Python docs](https://docs.python.org/3/library/multiprocessing.shared_memory.html#module-multiprocessing.shared_memory).


###### Flexibility
Dataclasses don't require Java-style repetitive constructors. To modify your hyperparameter combination, simply instantiate it as follows.

```python
Hyperparams(batch_size=search(2,4,8))
```

###### Multiprocessing 
You can run multiple settings on multiple processes. 

```python
params = Hyperparams()
params.run_all(n_proc = os.cpu_count() - 2)
```

Also note that `Experiment` objects have access to concurrency-related fields initialised by superparams. These are:

- `rank`: the process id of this experiment setting, i.e. `rank in {0,1,2,3}` if `n_proc = 4`. 
- `n_proc`: parameter passed to the `n_proc` field.

###### Mutable Dataclass Attributes
Python throws a tantrum if you try to assign a mutable value to a dataclass:

```python
@dataclass 
class Params(Experiment):
    iterable = [1,2,3]

# Error > you should use field(default_factory=lambda: [1,2,3])
```

This is ugly. Python does this to protect you in case you were to instantiate a second set of Params(), and modify the `iterable`. As it's a class attribute, you'd be modifying both instantiated `Params` objects. 

I think this is stupid and limits the potential of `dataclasses` (especially given that `frozen = True` is a setting that enforces this yet still raises the error). For now, using `iterable = search([1,2,3])` should work. In the future, I may rewrite the built-in dataclass to not follow this pattern to make it more explicit. 

Note a similar thing is much more likely to happen in functions, where it is not guarded by Python. E.g. in 

```python
def function(items = [1,2,3])
    print(items)
    items.append(4)

function() # [1,2,3]
function() # [1,2,3,4]
```

Further reference in [Python docs](https://docs.python.org/3/library/dataclasses.html#mutable-default-values).

#### Alternatives
Any decent package should list viable alternatives. Here are some that I considered, but ended up building this package instead. 

- [wandb sweeps](https://docs.wandb.ai/guides/sweeps/) is best used for Bayesian hyperparameter search to optimise a DL model; but requires specifying settings in JSON files.
- [ray tune](https://docs.ray.io/en/latest/tune/index.html) enables SOTA algorithms like PBT (similar to genetic optimisation) and HyperBand/ASHA (large population with early stopping), and allows for relatively unsupervised optimisation by specifying a search space *and objective* in Python. It is also compatible with [Keras Hyperopt](https://github.com/maxpumperla/hyperas) and [Pytorch Optuna](https://optuna.org/).
- [orion](https://orion.readthedocs.io/en/stable/index.html) is similar to ray tune, but more or less a wrapper around an argument parser you need to set up yourself (so you have to specify everything in plain-text cli commands).
- [hydra](https://hydra.cc/) is probably most-similar in features to `superparams`, but relies on `yaml` for specification and doesn't collate results nicely into a `polars` dataframe. 

I think of superparams as more open-ended than ray-tune: there may not be a direct objective to optimise as the right objective is often not yet established in the early stages of experimentation. And, by allowing everything to be specified in a single Python dataclass, you maintain flexibility by not assuming that the entire optimisation is a black-box. To me, it is valuable to be able to specify all parameters *and* logic in a single place, completely in lsp-understandable python.

