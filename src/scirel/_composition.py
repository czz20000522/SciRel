"""Ordinary function composition with explicit, module-owned dependencies."""
from collections.abc import Mapping


def compose(calculation, inputs, keywords, dependencies):
    if inputs is None:
        values = {}
    elif isinstance(inputs, Mapping):
        values = dict(inputs)
    else:
        raise TypeError("inputs must be a mapping when supplied positionally")
    values.update(keywords)

    def resolver(functions):
        def resolve(reference, attribute=None):
            function = functions[reference]
            if attribute is not None and attribute not in {
                function.__name__, "scientific_operator", "latin_hypercube_samples"
            }:
                raise KeyError(f"undeclared callable attribute: {attribute}")
            return function
        return resolve

    return calculation(values, **{name: resolver(functions) for name, functions in dependencies.items()})
