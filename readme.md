## param-search
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

#### Installation
A single file for now. Just copy it over. 


