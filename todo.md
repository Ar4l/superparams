
#### TODO

- [ ] just running `experiment` lists the available experiments.
- [ ] improve progress reporting to work better across multiple processes.
- [ ] caching experiments based on the hyperparameters, 
- [ ] allowing operations based on the hyperparameters in `format_results` e.g. `max(dimension)`.
- [ ] try merging `.progress.lock` lockfile with the `.progress` file, to avoid this litter, requires multiprocessing tests :). 
- [ ] allow running multiple experiments defined in one file. I.e. `experiment dataset` runs all classes found in dataset. We should be able to do this by checking if the final component is a filename, or a directory name. 
- [ ] allow relative imports in libraries imported by experiment.
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
- get rid of this annoying `@dataclass` annotation, replace with `@experiment`; force immutability for provided mutable class attributes, rather than `dataclasses` default approach.
- check compatitibility with `python=3.10, python=3.11`. 


#### Publishing

0. **Test.** Ensure tests pass with `uv run --all-extras pytest`
1. **Update.** Bump version in `pyproject.toml`: big bump means package *in*compatibility for users :)
2. **Publish.** Clear existing builds in `dist`, run `uv build`, followed by `uv publish -vt <token>`
3. **Save.** Git commit `pyproject.toml` and `uv.lock`, tag with `git tag -a vX.X.X -m 'version X.X.X: description`. 
4. **Push.** `git push` and `git push origin vX.X.X` ~~will trigger an automatic publish hook on GitHub. #todo: set up git hook to automatically publish, and then we can get rid of step 2~~.

