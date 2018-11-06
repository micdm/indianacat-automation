#!/usr/bin/env python3

import sys

from lib import ic, mlp
from lib.common import run, create_references

if __name__ == '__main__':
    references = create_references()
    if sys.argv[1] == 'ic':
        stage_list_factory = ic.get_stages_to_test
    elif sys.argv[1] == 'mlp':
        stage_list_factory = mlp.get_stages_to_test
    else:
        raise RuntimeError('unknown game %s' % sys.argv[1])
    run(stage_list_factory(references))
