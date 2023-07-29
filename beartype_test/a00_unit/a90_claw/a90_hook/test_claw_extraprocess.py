#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright (c) 2014-2023 Beartype authors.
# See "LICENSE" for further details.

'''
Beartype **extraprocess import hook unit tests** (i.e., unit tests exercising
:mod:`beartype.claw` import hooks within a Python subprocess forked from the
active Python process).
'''

# ....................{ IMPORTS                            }....................
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# WARNING: To raise human-readable test errors, avoid importing from
# package-specific submodules at module scope.
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
from pytest import MonkeyPatch

# ....................{ TESTS                              }....................
def test_claw_extraprocess_executable_submodule(
    monkeypatch: MonkeyPatch) -> None:
    '''
    Test an arbitrary :mod:`beartype.claw` import hook against a data submodule
    in this test suite run as a script within a Python subprocess forked from
    the active Python process via the standard command-line option ``-m``.

    Parameters
    ----------
    monkeypatch : MonkeyPatch
        :mod:`pytest` fixture enabling various state associated with the active
        Python process to be temporarily changed for the duration of this test.
    '''

    # ....................{ IMPORTS                        }....................
    # Defer test-specific imports.
    from beartype._util.py.utilpyinterpreter import (
        get_interpreter_command_words)
    from beartype_test._util.command.pytcmdrun import run_command_forward_output
    from beartype_test._util.path.pytpathtest import (
        get_test_unit_data_claw_extraprocess_dir)

    # ....................{ ASSERTS                        }....................
    # Temporarily change the current working directory (CWD) to the
    # test-specific root directory containing the data package tested below.
    monkeypatch.chdir(get_test_unit_data_claw_extraprocess_dir())

    # Tuple of all shell words with which to run a data submodule in this test
    # suite as a script within a Python subprocess forked from the active Python
    # process via the standard command-line option "-m".
    PYTHON_ARGS = get_interpreter_command_words() + (
        # Fully-qualified name of this data submodule with respect to the root
        # directory containing the package containing this submodule.
        '-m', 'executable_submodule.main_submodule',
    )

    # Run this module as a script, raising an exception on subprocess failure
    # while forwarding all standard output and error output by this subprocess
    # to the standard output and error file handles of this active process.
    run_command_forward_output(command_words=PYTHON_ARGS)


def test_claw_extraprocess_executable_package(monkeypatch: MonkeyPatch) -> None:
    '''
    Test an arbitrary :mod:`beartype.claw` import hook against a data package
    in this test suite run as a script within a Python subprocess forked from
    the active Python process via the standard command-line option ``-m``.

    Parameters
    ----------
    monkeypatch : MonkeyPatch
        :mod:`pytest` fixture enabling various state associated with the active
        Python process to be temporarily changed for the duration of this test.
    '''

    # ....................{ IMPORTS                        }....................
    # Defer test-specific imports.
    from beartype._util.py.utilpyinterpreter import (
        get_interpreter_command_words)
    from beartype_test._util.command.pytcmdrun import run_command_forward_output
    from beartype_test._util.path.pytpathtest import (
        get_test_unit_data_claw_extraprocess_dir)

    # ....................{ ASSERTS                        }....................
    # Temporarily change the current working directory (CWD) to the
    # test-specific root directory containing the data package tested below.
    monkeypatch.chdir(get_test_unit_data_claw_extraprocess_dir())

    # Tuple of all shell words with which to run a data submodule in this test
    # suite as a script within a Python subprocess forked from the active Python
    # process via the standard command-line option "-m".
    PYTHON_ARGS = get_interpreter_command_words() + (
        # Fully-qualified name of this data package with respect to the root
        # directory containing the package.
        '-m', 'executable_package',
    )

    # Run this package as a script, raising an exception on subprocess failure
    # while forwarding all standard output and error output by this subprocess
    # to the standard output and error file handles of this active process.
    run_command_forward_output(command_words=PYTHON_ARGS)
