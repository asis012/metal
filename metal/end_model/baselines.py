import torch.nn as nn

from metal.end_model import EndModel
from metal.end_model.em_defaults import em_default_config
from metal.utils import recursive_merge_dicts

class LogisticRegression(EndModel):
    """A logistic regression classifier for a binary single-task problem"""
    def __init__(self, input_dim, output_dim=2, **kwargs):
        layer_out_dims = [input_dim, output_dim]
        overrides = {
            'batchnorm': False,
            'dropout': 0.0,
        }
        kwargs = recursive_merge_dicts(kwargs, overrides, misses='insert',
            verbose=False)
        super().__init__(layer_out_dims, **kwargs)