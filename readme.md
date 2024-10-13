## superparams
a Pythonic approach to Hyperparameter Search. Using built-in `dataclasses`, as they are flexible, typed, easily-serialisable, and are a `dict` in the places you need them. 

> I like to think of it as the repetitive back-logic for flexible, fast searching of any search space. 

#### Usage 
```python 
from dataclasses import dataclass
from hyperparameters import GridSearch, search

@dataclass
class Hyperparams(GridSearch):

    epochs        :int   = 3 
    batch_size    :int   = search([16, 32])
    learning_rate :float = search([1e-5, 2e-5])

def run(self):
    ''' Run this setting of parameters '''

    results = dict(batch=self.batch_size, lr=self.learning_rate)
    print(results)

    # automatically save results in a parquet file by returning them 
    return results
```

This inherits a bunch of useful attributes, and constructs an iterator. 

```python
for h in Hyperparams():
    print(h)

# Outputs: 
# Hyperparams(epochs=3, batch_size=16, learning_rate=1e-05)
# Hyperparams(epochs=3, batch_size=16, learning_rate=2e-05)
# Hyperparams(epochs=3, batch_size=32, learning_rate=1e-05)
# Hyperparams(epochs=3, batch_size=32, learning_rate=2e-05)
```

###### Flexibility
Dataclasses don't require Java-style repetitive constructors. To modify your hyperparameter combination, simply instantiate it as follows.

```python
Hyperparams(epochs=search([1,2,3]))

#    Search 3 dimensions, total 12 combinations
#    epochs:            [1, 2, 3]
#    batch_size:        [16, 32]
#    learning_rate:     [1e-05, 2e-05]
```

###### Multiprocessing 
You can run multiple settings on multiple processes. 

```python
params = Hyperparams()
params.run_all(num_proc = os.cpu_count() - 2)
```

> [!WARNING]
> Python-native `multiprocessing` shares the `Hyperparams` data with each process *by pickling it!*. This is woefully inefficient, and poses a massive bottleneck if sharing >50MB data. Consider refactoring such that each `run` method instantiates this data itself.
>
> In the future, I may do a refactor that shares the data more efficiently; but this is not trivial in Python.

Also note that `Experiment` objects have access to concurrency-related fields initialised by superparams. These are:

- `rank`: the process id of this experiment setting, i.e. `rank in {0,1,2,3}` if `n_proc = 4`. 
- `n_proc`: parameter passed to the `n_proc` field.

#### Installation
A single file for now. Just copy it over. 


#### TODO

- [ ] cli fn to run `experiment exp.RQ1`. 
- [ ] Encapsulate current `__main__` into a class, so the user can just add 
      ```python
      # some/path/to/custom/experiments/__main__.py
      from superparams import entrypoint
      entrypoint()
      ```
- [ ] smarter experiment lookup: users may want to have a single file for all their experiments, or spread it into different folders. 
  - `experiment RQ1` runs all experiments in the file `RQ1.py`
  - `experiment index.RQ1` runs the experiment `RQ1` in the file `index.py`, 
    or the file `RQ1.py` in the folder `experiments/index`. 

- `dataclasses` improvements 
- get rid of this annoying `@dataclass` annotation
- provide a `value` method to replace `field` pattern; do we assume immutability? 
- check compatitibility with `python=3.10, python=3.11`. 

- `testing`
- [ ] actual functional correctness tests 

