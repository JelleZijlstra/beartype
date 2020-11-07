#!/usr/bin/env python3
# --------------------( LICENSE                           )--------------------
# Copyright 2014-2020 by Cecil Curry.
# See "LICENSE" for further details.

'''
**Beartype unimportable data submodule.**

This submodule exercises dynamic importability by providing an unimportable
submodule defining an arbitrary attribute. External unit tests are expected to
dynamically import this attribute from this submodule.
'''

# ....................{ EXCEPTIONS                        }....................
class Fulfillment(Exception): pass
raise Fulfillment(
    'Can you imagine a fulfilled society? '
    'Whoa, what would everyone do?'
)
