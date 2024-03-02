from __future__ import annotations
from itertools import product
from dataclasses import dataclass
from typing import List, Any, Generator

@dataclass
class Search:
    ''' TODO: prohibit importing of this '''
    params : List[Any]

    def __iter__(self):
        ''' iterates over this hyperparam's values '''
        return iter(self.params)
    
    def __len__(self):
        return len(self.params)
    
    def __str__(self): 
        return str(self.params)

def search(params: List[Any]) -> Any:
    return Search(params=params)

@dataclass 
class GridSearch:
    ''' extend this class with your hyperparameter dataclass,
        to allow for iterating over its parameters as a grid search'''
    # Example given below.

    def __post_init__(self):
        if len(self.__dimensions) == 0: return 

        to_print = '\n\t'.join(f'{k}: \t{v}' for k, v in self.__dimensions.items())
        print(f'''
        Search {len(self.__dimensions)} dimensions, total {len(self.__combinations)} combinations
        \033[90m{to_print}\033[0m
        ''')   

    def __iter__(self) -> Generator[GridSearch, None, None]:
        for combination in self.__combinations: 
            yield self.__class__(**{**self.__dict__, **combination})

    @property 
    def __dimensions(self) -> dict[str, Search]:
        ''' returns all search params, and their search space '''
        return {k: v for k, v in self.__dict__.items() \
                if isinstance(v, Search)}

    @property 
    def __combinations(self) -> List[dict[str, Any]]:
        ''' returns all combinations of search params'''
        search_params = self.__dimensions
        if len(search_params) == 0: return [self]

        combinations = list(product(*search_params.values()))
        return [{k: v[i] for i, k in enumerate(search_params.keys())}\
                 for v in combinations]

@dataclass
class Hyperparams(GridSearch):

    model_dir  : str = 'hugggingface/CodeBERTa-small-v1'
    config_dir : str = 'hugggingface/CodeBERTa-small-v1'

    num_telemetry_features : int    = 26
    feature_layers         : int    = search([1, 2, 3])
    add_cross_attn         : bool   = search([True, False])

    batch_size             : int    = 16
    num_train_epochs       : int    = 3
    learning_rate          : float  = 2e-5


## TODO: test
# - no params
# - single param
# - multiple params
# - search 1 param
# - search no params 
# - search multiple params
# - recursive structures!! 
