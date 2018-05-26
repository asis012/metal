from collections import defaultdict, Counter
from itertools import chain
import os

import numpy as np
import numpy.random as random
from scipy.sparse import csc_matrix
import torch

from metal.metrics import accuracy_score, coverage_score

def exact_choice(xs, n, p, shuffle=True):
    counts = np.ceil(p * n).astype(int)
    samples = np.concatenate([np.ones(count, dtype=int) * x for x, count in 
        zip(xs, counts)])
    if shuffle:
        np.random.shuffle(samples)
    return samples[:n]

################################################################################
# Single-Task 
################################################################################

def generate_single_task_unipolar(n, m, k=2, acc=[0.6, 0.9], rec=[0.1, 0.2], 
    class_balance=None, lf_balance=None, seed=None):
    """Generate a single task label matrix
    
    Args:
        n: number of examples
        m: number of LFs
        k: cardinality of the task
        acc: accuracy range
        beta: labeling propensity (same for all classes)
        class_balance: normalized list of k floats representing the portion
            of the dataset with each label
        lf_balance: normalized list of k floats representing the portion of
            lfs with the polarity of each label

    Semantics:
        acc (accuracy): of my non-abstaining votes, what fraction are correct?
        rec (recall): of items that match my polarity, what fraction do I label?

    True labels take on values in {1,...,k}.

    Example:
        For a given LF of polarity 1 (the 0.3 class):
        n = 2000
        class_balance = [0.3, 0.7]
        acc = 0.6
        rec = 0.2

        There are 600 items w/ class 1  (n * balance)
        I label 120 of them (correctly) (n * balance * rec)
        I label 80 from other classes   (n * balance * rec * (1 - acc)/acc)
    """
    if seed is not None:
        random.seed(seed)

    if isinstance(class_balance, list):
        class_balance = np.array(class_balance)
    elif not class_balance:
        class_balance = np.full(shape=k, fill_value=1/k)
    assert(sum(class_balance) == 1)

    if isinstance(lf_balance, list):
        lf_balance = np.array(lf_balance)
    elif not lf_balance:
        lf_balance = np.full(shape=k, fill_value=1/k)
    assert(sum(lf_balance) == 1)

    # Use exact_choice to get the exact right numbers but randomly shuffled 
    labels = list(range(1, k+1))
    Y = exact_choice(labels, n, class_balance)
    polarities = exact_choice(labels, m, lf_balance)

    accs = random.rand(m) * (max(acc) - min(acc)) + min(acc)
    recs = random.rand(m) * (max(rec) - min(rec)) + min(rec)
    
    rows = []
    cols = []
    data = []

    for j in range(m):
        p = polarities[j]
        correct_bar = recs[j]
        correct_pool = list(exact_choice(
            [1,0],
            int(n * class_balance[p - 1]), 
            np.array([correct_bar, 1-correct_bar])))
        incorrect_bar = (class_balance[p - 1] * recs[j] * (1/accs[j] - 1) / 
            (1 - class_balance[p - 1]))
        incorrect_pool = list(exact_choice(
            [1,0], 
            int(n * (1 - class_balance[p - 1])), 
            np.array([incorrect_bar, 1-incorrect_bar])))
        for i in range(n):
            if Y[i] == p:
                if correct_pool.pop():
                    rows.append(i)
                    cols.append(j)
                    data.append(p)
            else:
                if incorrect_pool.pop():
                    rows.append(i)
                    cols.append(j)
                    data.append(p)

    L = csc_matrix((data, (rows, cols)), shape=(n, m))
    metadata = {
        'n' : n,
        'm' : m,
        'k' : k,
        'accs' : accs,
        'recs' : recs,
        'polarities' : polarities,
        'class_balance' : class_balance,
        'lf_balance' : lf_balance,
    }

    Y = torch.tensor(Y, dtype=torch.short)
    return L, Y, metadata