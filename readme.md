## superparams
a Pythonic approach to Hyperparameter Search. Using built-in `dataclasses`, as they are flexible, typed, easily-serialisable, and are a `dict` in the places you need them. 

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

#### Installation
A single file for now. Just copy it over. 


