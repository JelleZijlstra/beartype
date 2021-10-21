#!/usr/bin/env python3
# --------------------( LICENSE                           )--------------------
# Copyright (c) 2014-2021 Beartype authors.
# See "LICENSE" for further details.

'''
**Beartype decorator PEP-compliant type-checking code generator.**

This private submodule dynamically generates pure-Python code type-checking
arbitrary **PEP-compliant type hints** (i.e., :mod:`beartype`-agnostic
annotations compliant with annotation-centric PEPs) of the decorated callable
with a breadth-first search over the abstract graph of nested objects reachable
from the subscripted arguments of these hints.

This private submodule is *not* intended for importation by downstream callers.
'''

# ....................{ TODO                              }....................
# All "FIXME:" comments for this submodule reside in this package's "__init__"
# submodule to improve maintainability and readability here.

# ....................{ IMPORTS                           }....................
from beartype.roar import (
    BeartypeDecorHintPepException,
    BeartypeDecorHintPepUnsupportedException,
    BeartypeDecorHintPep593Exception,
)
from beartype._cave._cavefast import TestableTypes
from beartype._decor._code.codesnip import (
    ARG_NAME_GETRANDBITS,
    VAR_NAME_PREFIX_PITH,
    VAR_NAME_PITH_ROOT as PITH_ROOT_VAR_NAME,
)
from beartype._decor._code._pep._pepmagic import (
    EXCEPTION_PREFIX_FUNC_WRAPPER_LOCAL,
    EXCEPTION_PREFIX_HINT_ROOT,
    HINT_META_INDEX_HINT,
    HINT_META_INDEX_PLACEHOLDER,
    HINT_META_INDEX_PITH_EXPR,
    HINT_META_INDEX_PITH_VAR_NAME,
    HINT_META_INDEX_INDENT,
)
from beartype._decor._code._pep._pepscope import (
    add_func_scope_type,
    add_func_scope_types,
    add_func_scope_type_or_types,
    express_func_scope_type_forwardref,
)
from beartype._decor._code._pep._pepsnip import (
    PEP_CODE_HINT_ROOT_PREFIX,
    PEP_CODE_HINT_ROOT_SUFFIX,
    PEP_CODE_HINT_ROOT_SUFFIX_RANDOM_INT,
    PEP_CODE_HINT_CHILD_PLACEHOLDER_PREFIX,
    PEP_CODE_HINT_CHILD_PLACEHOLDER_SUFFIX,
    PEP_CODE_PITH_ASSIGN_EXPR,
    PEP484585_CODE_HINT_GENERIC_CHILD,
    PEP484585_CODE_HINT_GENERIC_PREFIX,
    PEP484585_CODE_HINT_GENERIC_SUFFIX,
    PEP484585_CODE_HINT_SEQUENCE_ARGS_1,
    PEP484585_CODE_HINT_SEQUENCE_ARGS_1_PITH_CHILD_EXPR,
    PEP484585_CODE_HINT_SUBCLASS,
    PEP484585_CODE_HINT_TUPLE_FIXED_EMPTY,
    PEP484585_CODE_HINT_TUPLE_FIXED_LEN,
    PEP484585_CODE_HINT_TUPLE_FIXED_NONEMPTY_CHILD,
    PEP484585_CODE_HINT_TUPLE_FIXED_NONEMPTY_PITH_CHILD_EXPR,
    PEP484585_CODE_HINT_TUPLE_FIXED_PREFIX,
    PEP484585_CODE_HINT_TUPLE_FIXED_SUFFIX,
    PEP484_CODE_HINT_INSTANCE,
    PEP484_CODE_HINT_UNION_CHILD_PEP,
    PEP484_CODE_HINT_UNION_CHILD_NONPEP,
    PEP484_CODE_HINT_UNION_PREFIX,
    PEP484_CODE_HINT_UNION_SUFFIX,
    PEP586_CODE_HINT_LITERAL,
    PEP586_CODE_HINT_PREFIX,
    PEP586_CODE_HINT_SUFFIX,
    PEP593_CODE_HINT_VALIDATOR_CHILD,
    PEP593_CODE_HINT_VALIDATOR_PREFIX,
    PEP593_CODE_HINT_VALIDATOR_SUFFIX,
)
from beartype._util.cache.utilcachecall import callable_cached
from beartype._util.cache.pool.utilcachepoollistfixed import (
    SIZE_BIG,
    acquire_fixed_list,
    release_fixed_list,
)
from beartype._util.cache.pool.utilcachepoolobjecttyped import (
    acquire_object_typed,
    release_object_typed,
)
from beartype._data.hint.pep.sign.datapepsigns import (
    HintSignAnnotated,
    HintSignForwardRef,
    HintSignGeneric,
    HintSignLiteral,
    HintSignTuple,
    HintSignType,
)
from beartype._data.hint.pep.sign.datapepsignset import (
    HINT_SIGNS_SEQUENCE_ARGS_1,
    HINT_SIGNS_SUPPORTED_DEEP,
    HINT_SIGNS_ORIGIN_ISINSTANCEABLE,
    HINT_SIGNS_UNION,
)
from beartype._util.func.utilfuncscope import (
    CallableScope,
    add_func_scope_attr,
)
from beartype._util.hint.pep.proposal.pep484.utilpep484generic import (
    get_hint_pep484_generic_base_erased_from_unerased)
from beartype._util.hint.pep.proposal.pep484585.utilpep484585 import (
    is_hint_pep484585_tuple_empty)
from beartype._util.hint.pep.proposal.pep484585.utilpep484585arg import (
    get_hint_pep484585_args_1)
from beartype._util.hint.pep.proposal.pep484585.utilpep484585generic import (
    get_hint_pep484585_generic_bases_unerased,
    get_hint_pep484585_generic_type,
)
from beartype._util.hint.pep.proposal.pep484585.utilpep484585type import (
    get_hint_pep484585_subclass_superclass)
from beartype._util.hint.pep.proposal.utilpep585 import (
    is_hint_pep585_builtin)
from beartype._util.hint.pep.proposal.utilpep586 import (
    die_unless_hint_pep586,
    get_hint_pep586_literals,
)
from beartype._util.hint.pep.proposal.utilpep593 import (
    get_hint_pep593_metadata,
    get_hint_pep593_metahint,
)
from beartype._util.hint.pep.utilpepget import (
    get_hint_pep_args,
    get_hint_pep_sign,
    get_hint_pep_origin_type_isinstanceable,
)
from beartype._util.hint.pep.utilpeptest import (
    die_if_hint_pep_unsupported,
    die_if_hint_pep_sign_unsupported,
    is_hint_pep,
    is_hint_pep_args,
    is_hint_pep_typing,
    warn_if_hint_pep_deprecated,
)
from beartype._util.hint.utilhintconv import sanify_hint_child
from beartype._util.hint.utilhinttest import is_hint_ignorable
from beartype._util.kind.utilkinddict import update_mapping
from beartype._util.py.utilpyversion import (
    IS_PYTHON_AT_LEAST_3_8,
    IS_PYTHON_AT_LEAST_3_7,
)
from beartype._util.text.utiltextmagic import (
    CODE_INDENT_1,
    CODE_INDENT_2,
    LINE_RSTRIP_INDEX_AND,
    LINE_RSTRIP_INDEX_OR,
)
from beartype.vale._valevale import BeartypeValidator
from beartype._util.text.utiltextmunge import replace_str_substrs
from beartype._util.text.utiltextrepr import represent_object
from collections.abc import Callable
from random import getrandbits
from typing import Optional, Tuple

# See the "beartype.cave" submodule for further commentary.
__all__ = ['STAR_IMPORTS_CONSIDERED_HARMFUL']

# ....................{ CODERS                            }....................
#FIXME: Attempt to JIT this function with Numba at some point. This will almost
#certainly either immediately blow up or improve nothing, but we're curious to
#see what happens. Make it so, Ensign Numba!
# from numba import jit
# @jit

@callable_cached
def pep_code_check_hint(
    # ..................{ PARAMS ~ mandatory                }..................
    hint: object,

    # ..................{ PARAMS ~ optional                 }..................
    # Globals defined above, declared as optional parameters for efficient
    # lookup as local attributes. Yes, this is an absurd microoptimization.
    # *fight me, github developer community*

    # "beartype._decor._code.codesnip" globals.
    _ARG_NAME_GETRANDBITS=ARG_NAME_GETRANDBITS,
    _CODE_INDENT_1=CODE_INDENT_1,
    _CODE_INDENT_2=CODE_INDENT_2,

    # "beartype._decor._code._pep._pepmagic" globals.
    _EXCEPTION_PREFIX_FUNC_WRAPPER_LOCAL=EXCEPTION_PREFIX_FUNC_WRAPPER_LOCAL,
    _EXCEPTION_PREFIX_HINT_ROOT=EXCEPTION_PREFIX_HINT_ROOT,
    _HINT_META_INDEX_HINT=HINT_META_INDEX_HINT,
    _HINT_META_INDEX_PLACEHOLDER=HINT_META_INDEX_PLACEHOLDER,
    _HINT_META_INDEX_PITH_EXPR=HINT_META_INDEX_PITH_EXPR,
    _HINT_META_INDEX_PITH_VAR_NAME=HINT_META_INDEX_PITH_VAR_NAME,
    _HINT_META_INDEX_INDENT=HINT_META_INDEX_INDENT,
    _LINE_RSTRIP_INDEX_AND=LINE_RSTRIP_INDEX_AND,
    _LINE_RSTRIP_INDEX_OR=LINE_RSTRIP_INDEX_OR,

    # "beartype._decor._code._pep._pepsnip" string globals required only for
    # their bound "str.format" methods.
    PEP_CODE_HINT_ROOT_SUFFIX_format: Callable = (
        PEP_CODE_HINT_ROOT_SUFFIX.format),
    PEP_CODE_PITH_ASSIGN_EXPR_format: Callable = (
        PEP_CODE_PITH_ASSIGN_EXPR.format),
    PEP484_CODE_HINT_INSTANCE_format: Callable = (
        PEP484_CODE_HINT_INSTANCE.format),
    PEP484585_CODE_HINT_GENERIC_CHILD_format: Callable = (
        PEP484585_CODE_HINT_GENERIC_CHILD.format),
    PEP484585_CODE_HINT_SEQUENCE_ARGS_1_format: Callable = (
        PEP484585_CODE_HINT_SEQUENCE_ARGS_1.format),
    PEP484585_CODE_HINT_SEQUENCE_ARGS_1_PITH_CHILD_EXPR_format: Callable = (
        PEP484585_CODE_HINT_SEQUENCE_ARGS_1_PITH_CHILD_EXPR.format),
    PEP484585_CODE_HINT_SUBCLASS_format: Callable = (
        PEP484585_CODE_HINT_SUBCLASS.format),
    PEP484585_CODE_HINT_TUPLE_FIXED_EMPTY_format: Callable = (
        PEP484585_CODE_HINT_TUPLE_FIXED_EMPTY.format),
    PEP484585_CODE_HINT_TUPLE_FIXED_LEN_format: Callable = (
        PEP484585_CODE_HINT_TUPLE_FIXED_LEN.format),
    PEP484585_CODE_HINT_TUPLE_FIXED_NONEMPTY_CHILD_format: Callable = (
        PEP484585_CODE_HINT_TUPLE_FIXED_NONEMPTY_CHILD.format),
    PEP484585_CODE_HINT_TUPLE_FIXED_NONEMPTY_PITH_CHILD_EXPR_format: Callable = (
        PEP484585_CODE_HINT_TUPLE_FIXED_NONEMPTY_PITH_CHILD_EXPR.format),
    PEP484_CODE_HINT_UNION_CHILD_PEP_format: Callable = (
        PEP484_CODE_HINT_UNION_CHILD_PEP.format),
    PEP484_CODE_HINT_UNION_CHILD_NONPEP_format: Callable = (
        PEP484_CODE_HINT_UNION_CHILD_NONPEP.format),
    PEP586_CODE_HINT_LITERAL_format: Callable = (
        PEP586_CODE_HINT_LITERAL.format),
    PEP586_CODE_HINT_PREFIX_format: Callable = (
        PEP586_CODE_HINT_PREFIX.format),
    PEP593_CODE_HINT_VALIDATOR_PREFIX_format: Callable = (
        PEP593_CODE_HINT_VALIDATOR_PREFIX.format),
    PEP593_CODE_HINT_VALIDATOR_SUFFIX_format: Callable = (
        PEP593_CODE_HINT_VALIDATOR_SUFFIX.format),
    PEP593_CODE_HINT_VALIDATOR_CHILD_format: Callable = (
        PEP593_CODE_HINT_VALIDATOR_CHILD.format),
) -> Tuple[str, CallableScope, Tuple[str, ...]]:
    '''
    Python code snippet type-checking the previously localized parameter or
    return value annotated by the passed PEP-compliant type hint against that
    hint of the decorated callable.

    This code generator is memoized for efficiency.

    Caveats
    ----------
    **This function intentionally accepts no** ``exception_prefix`` **parameter.**
    Why? Since that parameter is typically specific to the caller, accepting
    that parameter would effectively prevent this code generator from memoizing
    the passed hint with the returned code, which would rather defeat the
    point. Instead, this function only:

    * Returns generic non-working code containing the placeholder
      :attr:`beartype._decor._code._pep.pepcode.PITH_ROOT_NAME_PLACEHOLDER_STR`
      substring that the caller is required to globally replace by the name of
      the current parameter *or* ``return`` for return values (e.g., by calling
      the builtin :meth:`str.replace` method) to generate the desired
      non-generic working code type-checking that parameter or return value.
    * Raises generic non-human-readable exceptions containing the placeholder
      :attr:`beartype._util.cache.utilcacheerror.EXCEPTION_CACHED_PLACEHOLDER`
      substring that the caller is required to explicitly catch and raise
      non-generic human-readable exceptions from by calling the
      :func:`beartype._util.cache.utilcacheerror.reraise_exception_cached`
      function.

    Parameters
    ----------
    hint : object
        PEP-compliant type hint to be type-checked.

    Returns
    ----------
    Tuple[str, CallableScope, Tuple[str, ...]]
        3-tuple ``(func_wrapper_code, func_wrapper_locals,
        hint_forwardrefs_class_basename)``, where:

        * ``func_wrapper_code`` is a Python code snippet type-checking the
          previously localized parameter or return value against this hint.
        * ``func_wrapper_locals`` is the **local scope** (i.e., dictionary
          mapping from the name to value of each attribute referenced in the
          signature) of this wrapper function needed for this type-checking.
        * ``hint_forwardrefs_class_basename`` is a tuple of the unqualified
          classnames of :pep:`484`-compliant relative forward references
          visitable from this root hint (e.g., ``('MuhClass', 'YoClass')``
          given the root hint ``Union['MuhClass', List['YoClass']]``).

    Raises
    ----------
    BeartypeDecorHintPepException
        If this object is *not* a PEP-compliant type hint.
    BeartypeDecorHintPepUnsupportedException
        If this object is a PEP-compliant type hint currently unsupported by
        the :func:`beartype.beartype` decorator.
    BeartypeDecorHintPep484Exception
        If one or more PEP-compliant type hints visitable from this object are
        nested :attr:`typing.NoReturn` child hints, since
        :attr:`typing.NoReturn` is valid *only* as a non-nested return hint.
    BeartypeDecorHintPep593Exception
        If one or more PEP-compliant type hints visitable from this object
        subscript the :pep:`593`-compliant :class:`typing.Annotated` class such
        that:

        * The second argument subscripting that class is an instance of the
          :class:`beartype.vale.Is` class.
        * One or more further arguments subscripting that class are *not*
          instances of the :class:`beartype.vale.Is` class.

    Warns
    ----------
    BeartypeDecorHintPep585DeprecationWarning
        If one or more :pep:`484`-compliant type hints visitable from this
        object have been deprecated by :pep:`585`.
    '''

    # ..................{ HINT ~ root                       }..................
    # Top-level hint relocalized for disambiguity.
    hint_root = hint

    # Delete the passed parameter whose name is ambiguous within the context of
    # this function for similar disambiguity.
    del hint

    # ..................{ HINT ~ current                    }..................
    # Currently visited hint.
    hint_curr = None

    # Current unsubscripted typing attribute associated with this hint (e.g.,
    # "Union" if "hint_curr == Union[int, str]").
    hint_curr_sign = None

    # Python expression evaluating to an isinstanceable type (e.g., origin
    # type) associated with the currently visited type hint if any.
    hint_curr_expr = None

    #FIXME: Excise us up.
    # Origin type (i.e., non-"typing" superclass suitable for shallowly
    # type-checking the current pith against the currently visited hint by
    # passing both to the isinstance() builtin) of this hint if this hint
    # originates from such a superclass.
    # hint_curr_type_origin = None

    # Placeholder string to be globally replaced in the Python code snippet to
    # be returned (i.e., "func_wrapper_code") by a Python code snippet
    # type-checking the current pith expression (i.e.,
    # "pith_curr_var_name") against the currently visited hint (i.e.,
    # "hint_curr").
    hint_curr_placeholder = None

    # Full Python expression evaluating to the value of the current pith (i.e.,
    # possibly nested object of the passed parameter or return value to be
    # type-checked against the currently visited hint).
    #
    # Note that this is *NOT* a Python >= 3.8-specific assignment expression
    # but rather the original inefficient expression provided by the parent
    # PEP-compliant type hint of the currently visited hint.
    pith_curr_expr = None

    # Name of the current pith variable (i.e., local Python variable in the
    # body of the wrapper function whose value is that of the current pith).
    # This name is either:
    # * Initially, the name of the currently type-checked parameter or return.
    # * On subsequently type-checking nested items of the parameter or return
    #   under Python >= 3.8, the name of the local variable uniquely assigned
    #   to by the assignment expression defined by "pith_curr_assign_expr"
    #   (i.e., the left-hand side (LHS) of that assignment expression).
    pith_curr_var_name = PITH_ROOT_VAR_NAME

    # Python code snippet expanding to the current level of indentation
    # appropriate for the currently visited hint.
    indent_curr = _CODE_INDENT_2

    # ..................{ HINT ~ child                      }..................
    # Currently iterated PEP-compliant child hint subscripting the currently
    # visited hint, initialized to the root hint to enable the subsequently
    # called _enqueue_hint_child() function to enqueue the root hint.
    hint_child = hint_root

    #FIXME: Excise us up.
    # Current unsubscripted typing attribute associated with this hint (e.g.,
    # "Union" if "hint_child == Union[int, str]").
    # hint_child_sign = None

    #FIXME: Excise us up.
    # Python expression evaluating to the value of the currently iterated child
    # hint of the currently visited parent hint.
    # hint_child_expr = None

    #FIXME: Excise us up.
    # Origin type (i.e., non-"typing" superclass suitable for shallowly
    # type-checking the current pith against the currently visited hint by
    # passing both to the isinstance() builtin) of the currently iterated child
    # hint of the currently visited parent hint.
    # hint_child_type_origin = None

    #FIXME: Excise us up.
    # Python code snippet evaluating to the current (possibly nested) object of
    # the passed parameter or return value to be type-checked against the
    # currently iterated child hint.
    #pith_child_expr = None

    # Python code snippet expanding to the current level of indentation
    # appropriate for the currently iterated child hint, initialized to the
    # root hint indentation to enable the subsequently called
    # _enqueue_hint_child() function to enqueue the root hint.
    indent_child = indent_curr

    # ..................{ HINT ~ childs                     }..................
    # Current tuple of all PEP-compliant child hints subscripting the currently
    # visited hint (e.g., "(int, str)" if "hint_curr == Union[int, str]").
    hint_childs: tuple = None  # type: ignore[assignment]

    # Number of PEP-compliant child hints subscripting the currently visited
    # hint.
    hint_childs_len: int = None  # type: ignore[assignment]

    # Set of all PEP-noncompliant child hints subscripting the currently
    # visited hint.
    hint_childs_nonpep: set = None  # type: ignore[assignment]

    # Set of all PEP-compliant child hints subscripting the currently visited
    # hint.
    hint_childs_pep: set = None  # type: ignore[assignment]

    # ..................{ HINT ~ pep 484 : forwardref       }..................
    # Set of the unqualified classnames referred to by all relative forward
    # references visitable from this root hint if any *OR* "None" otherwise
    # (i.e., if no such forward references are visitable).
    hint_forwardrefs_class_basename: Optional[set] = None

    # ..................{ HINT ~ pep 572                    }..................
    # The following local variables isolated to this subsection are only
    # relevant when these conditions hold:
    # * The active Python interpreter targets at least Python 3.8, the first
    #   major Python version to introduce support for "PEP 572 -- Assignment
    #   Expressions."
    # * The currently visited hint is *NOT* the root hint (i.e., "hint_root").
    #   If the currently visited hint is the root hint, the current pith has
    #   already been localized to a local variable whose name is the value of
    #   the "VAR_NAME_PITH_ROOT" string global and thus need *NOT* be
    #   relocalized to another local variable using an assignment expression.
    #
    # This is a necessary and sufficient condition for deciding whether a
    # Python >= 3.8-specific assignment expression localizing the current pith
    # should be embedded in the code generated to type-check this pith against
    # this hint. This is a non-trivial runtime optimization eliminating
    # repeated computations to obtain this pith from PEP-compliant child hints.
    # For example, if this hint constrains this pith to be a standard sequence,
    # the child pith of this parent pith is a random item selected from this
    # sequence; since obtaining this child pith is non-trivial, the computation
    # required to do so is performed only once by assigning this child pith to
    # a unique local variable during runtime type-checking and then repeatedly
    # type-checking that variable rather than the computation required to
    # continually reacquire this child pith: e.g.,
    #
    #     # Type-checking conditional for "List[List[str]]" under Python < 3.8.
    #     if not (
    #         isinstance(__beartype_pith_0, list) and
    #         (
    #             isinstance(__beartype_pith_0[__beartype_random_int % len(__beartype_pith_0)], list) and
    #             isinstance(__beartype_pith_0[__beartype_random_int % len(__beartype_pith_0)][__beartype_random_int % len(__beartype_pith_0[__beartype_random_int % len(__beartype_pith_0)])], str) if __beartype_pith_0[__beartype_random_int % len(__beartype_pith_0)] else True
    #         ) if __beartype_pith_0 else True
    #     ):
    #
    #     # The same conditional under Python >= 3.8.
    #     if not (
    #         isinstance(__beartype_pith_0, list) and
    #         (
    #             isinstance(__beartype_pith_1 := __beartype_pith_0[__beartype_random_int % len(__beartype_pith_0)], list) and
    #             isinstance(__beartype_pith_1[__beartype_random_int % len(__beartype_pith_1)], str) if __beartype_pith_1 else True
    #         ) if __beartype_pith_0 else True
    #     ):
    #
    # Note that:
    # * The random item selected from the root pith (i.e., "__beartype_pith_1
    #   := __beartype_pith_0[__beartype_random_int % len(__beartype_pith_0)")
    #   only occurs once under Python >= 3.8 but repeatedly under Python < 3.8.
    #   In both cases, the same semantic type-checking is performed regardless
    #   of optimization.
    # * This optimization implicitly "bottoms out" when the currently visited
    #   hint is *NOT* subscripted by unignorable PEP-compliant child hint
    #   arguments. If all child hints of the currently visited hint are either
    #   ignorable (e.g., "object", "Any") *OR* are unignorable isinstanceable
    #   types (e.g., "int", "str"), the currently visited hint has *NO*
    #   meaningful PEP-compliant child hints and is thus effectively a leaf
    #   node with respect to performing this optimization.
    #is_pith_curr_assign_expr = None

    # Integer suffixing the name of each local variable assigned the value of
    # the current pith in a Python >= 3.8-specific assignment expression, thus
    # uniquifying this variable in the body of the current wrapper function.
    #
    # Note that this integer is intentionally incremented as an efficient
    # low-level scalar rather than as an inefficient high-level
    # "itertools.Counter" object. Since both are equally thread-safe in the
    # internal context of this function body, the former is preferable.
    pith_curr_assign_expr_name_counter = 0

    # Python >= 3.8-specific assignment expression assigning this full Python
    # expression to the local variable assigned the value of this expression.
    pith_curr_assign_expr: str = None  # type: ignore[assignment]

    # ..................{ HINT ~ label                      }..................
    # Human-readable label prefixing the machine-readable representation of the
    # currently visited type hint if this hint is nested (i.e., any hint
    # *except* the root type hint) in exception and warning messages.
    #
    # Note that "hint_curr_exception_prefix" should almost *ALWAYS* be used instead.
    _EXCEPTION_PREFIX_HINT_CHILD = (
        f'{_EXCEPTION_PREFIX_HINT_ROOT}{repr(hint_root)} nested ')

    # Human-readable label prefixing the machine-readable representation of the
    # currently visited type hint in exception and warning messages,
    # initialized to the label describing the root type hint.
    #
    # Note that this label intentionally only describes the root and currently
    # iterated child hints rather than the root hint, the currently iterated
    # child hint, and all interim child hints leading from the former to the
    # latter. The latter approach would be non-human-readable and insane.
    hint_curr_exception_prefix = _EXCEPTION_PREFIX_HINT_ROOT

    # ..................{ METADATA                          }..................
    # Tuple of metadata describing the currently visited hint, appended by
    # the previously visited parent hint to the "hints_meta" stack.
    hint_curr_meta: tuple = None  # type: ignore[assignment]

    # Fixed list of all metadata describing all visitable hints currently
    # discovered by the breadth-first search (BFS) below. This list acts as a
    # standard First In First Out (FILO) queue, enabling this BFS to be
    # implemented as an efficient imperative algorithm rather than an
    # inefficient (and dangerous, due to both unavoidable stack exhaustion and
    # avoidable infinite recursion) recursive algorithm.
    #
    # Note that this list is guaranteed by the previously called
    # _die_if_hint_repr_exceeds_child_limit() function to be larger than the
    # number of hints transitively visitable from this root hint. Ergo, *ALL*
    # indexation into this list performed by this BFS is guaranteed to be safe.
    # Ergo, avoid explicitly testing below that the "hints_meta_index_last"
    # integer maintained by this BFS is strictly less than "SIZE_BIG", as this
    # constraint is already guaranteed to be the case.
    hints_meta = acquire_fixed_list(SIZE_BIG)

    # 0-based index of metadata describing the currently visited hint in the
    # "hints_meta" list.
    hints_meta_index_curr = 0

    # 0-based index of metadata describing the last visitable hint in the
    # "hints_meta" list, initialized to "-1" to ensure that the initial
    # incrementation of this index by the _enqueue_hint_child() directly called
    # below initializes index 0 of the "hints_meta" fixed list.
    #
    # For efficiency, this integer also uniquely identifies the currently
    # iterated child PEP-compliant type hint of the currently visited parent
    # PEP-compliant type hint.
    hints_meta_index_last = -1

    # ..................{ FUNC ~ code                       }..................
    # Python code snippet type-checking the current pith against the currently
    # visited hint (to be appended to the "func_wrapper_code" string).
    func_curr_code: str = None  # type: ignore[assignment]

    # ..................{ FUNC ~ code : locals              }..................
    # Local scope (i.e., dictionary mapping from the name to value of each
    # attribute referenced in the signature) of this wrapper function required
    # by this Python code snippet.
    func_wrapper_locals: CallableScope = {}

    # True only if one or more PEP-compliant type hints visitable from this
    # root hint require a pseudo-random integer. If true, the higher-level
    # beartype._decor._code.codemain.generate_code() function prefixes the body
    # of this wrapper function with code generating such an integer.
    is_var_random_int_needed = False

    # ..................{ CLOSURES                          }..................
    # Closures centralizing frequently repeated logic, addressing Don't Repeat
    # Yourself (DRY) concerns during the breadth-first search (BFS) below.

    def _enqueue_hint_child(pith_child_expr: str) -> str:
        '''
        **Enqueue** (i.e., append) a new tuple of metadata describing the
        currently iterated child hint to the end of the ``hints_meta`` queue,
        enabling this hint to be visited by the ongoing breadth-first search
        (BFS) traversing over this queue.

        Parameters
        ----------
        pith_child_expr : str
            Python code snippet evaluating to the child pith to be
            type-checked against the currently iterated child hint.

        This closure also implicitly expects the following local variables of
        the outer scope to be set to relevant values:

        hint_child : object
            Currently iterated PEP-compliant child hint subscripting the
            currently visited hint.

        Returns
        ----------
        str
            Placeholder string to be subsequently replaced by code
            type-checking this child pith against this child hint.
        '''

        # Allow these local variables of the outer scope to be modified below.
        nonlocal hints_meta_index_last

        # Increment both the 0-based index of metadata describing the last
        # visitable hint in the "hints_meta" list and the unique identifier of
        # the currently iterated child hint *BEFORE* overwriting the existing
        # metadata at this index.
        #
        # Note this index is guaranteed to *NOT* exceed the fixed length of
        # this list, by prior validation.
        hints_meta_index_last += 1

        # Placeholder string to be globally replaced by code type-checking the
        # child pith against this child hint, intentionally prefixed and
        # suffixed by characters that:
        #
        # * Are intentionally invalid as Python code, guaranteeing that the
        #   top-level call to the exec() builtin performed by the @beartype
        #   decorator will raise a "SyntaxError" exception if the caller fails
        #   to replace all placeholder substrings generated by this method.
        # * Protect the identifier embedded in this substring against ambiguous
        #   global replacements of larger identifiers containing this
        #   identifier. If this identifier were *NOT* protected in this manner,
        #   then the first substring "0" generated by this method would
        #   ambiguously overlap with the subsequent substring "10" generated by
        #   this method, which would then produce catastrophically erroneous
        #   and non-trivial to debug Python code.
        hint_child_placeholder = (
            f'{PEP_CODE_HINT_CHILD_PLACEHOLDER_PREFIX}'
            f'{str(hints_meta_index_last)}'
            f'{PEP_CODE_HINT_CHILD_PLACEHOLDER_SUFFIX}'
        )

        # Create and insert a new tuple of metadata describing this child hint
        # at this index of this list.
        #
        # Note that this assignment is guaranteed to be safe, as "SIZE_BIG" is
        # guaranteed to be substantially larger than "hints_meta_index_last".
        hints_meta[hints_meta_index_last] = (
            hint_child,
            hint_child_placeholder,
            pith_child_expr,
            pith_curr_var_name,
            indent_child,
        )

        # Return this placeholder string.
        return hint_child_placeholder

    # ..................{ CLOSURES ~ locals                 }..................
    # Local variables calling one or more closures declared above and thus
    # deferred until after declaring those closures.

    # Placeholder string to be globally replaced in the Python code snippet to
    # be returned (i.e., "func_wrapper_code") by a Python code snippet
    # type-checking the child pith expression (i.e., "pith_child_expr") against
    # the currently iterated child hint (i.e., "hint_child"), initialized to a
    # placeholder describing the root hint.
    hint_child_placeholder = _enqueue_hint_child(PITH_ROOT_VAR_NAME)

    # Python code snippet type-checking the root pith against the root hint,
    # localized separately from the "func_wrapper_code" snippet to enable this
    # function to validate this code to be valid *BEFORE* returning this code.
    func_root_code = (
        f'{PEP_CODE_HINT_ROOT_PREFIX}{hint_child_placeholder}')

    # Python code snippet to be returned, seeded with a placeholder to be
    # replaced on the first iteration of the breadth-first search performed
    # below with a snippet type-checking the root pith against the root hint.
    func_wrapper_code = func_root_code

    # ..................{ SEARCH                            }..................
    # While the 0-based index of metadata describing the next visited hint in
    # the "hints_meta" list does *NOT* exceed that describing the last
    # visitable hint in this list, there remains at least one hint to be
    # visited in the breadth-first search performed by this iteration.
    while hints_meta_index_curr <= hints_meta_index_last:
        # Metadata describing the currently visited hint.
        hint_curr_meta = hints_meta[hints_meta_index_curr]

        # Assert this metadata is a tuple as expected. This enables us to
        # distinguish between proper access of used items and improper access
        # of unused items of the parent fixed list containing this tuple, since
        # an unused item of this list is initialized to "None" by default.
        assert hint_curr_meta.__class__ is tuple, (
            f'Current hint metadata {repr(hint_curr_meta)} at '
            f'index {hints_meta_index_curr} not tuple.')

        # Localize metadatum for both efficiency and f-string purposes.
        hint_curr             = hint_curr_meta[_HINT_META_INDEX_HINT]
        hint_curr_placeholder = hint_curr_meta[_HINT_META_INDEX_PLACEHOLDER]
        pith_curr_expr        = hint_curr_meta[_HINT_META_INDEX_PITH_EXPR]
        pith_curr_var_name    = hint_curr_meta[_HINT_META_INDEX_PITH_VAR_NAME]
        indent_curr           = hint_curr_meta[_HINT_META_INDEX_INDENT]

        # If this is a child hint rather than the root hint, sanify (i.e.,
        # sanitize) this hint if this hint is reducible *OR* preserve this hint
        # otherwise (i.e., if this hint is irreducible).
        #
        # Note that the root hint has already been permanently sanified by the
        # calling "beartype._decor._code.codemain" submodule and thus need
        # *NOT* be inefficiently resanified here.
        if hints_meta_index_curr:
            hint_curr = sanify_hint_child(
                hint=hint_curr, exception_prefix=hint_curr_exception_prefix)

        #FIXME: Comment this sanity check out after we're sufficiently
        #convinced this algorithm behaves as expected. While useful, this check
        #requires a linear search over the entire code and is thus costly.
        # assert hint_curr_placeholder in func_wrapper_code, (
        #     '{} {!r} placeholder {} not found in wrapper body:\n{}'.format(
        #         hint_curr_exception_prefix, hint, hint_curr_placeholder, func_wrapper_code))

        # ................{ PEP                               }................
        # If this hint is PEP-compliant...
        if is_hint_pep(hint_curr):
            #FIXME: Refactor to call warn_if_hint_pep_unsupported() instead.
            #Actually...wait. This is probably still a valid test here. We'll
            #need to instead augment the is_hint_ignorable() function to
            #additionally test whether the passed hint is unsupported, in which
            #case that function should return false as well as emit a non-fatal
            #warning ala the new warn_if_hint_pep_unsupported() function --
            #which should probably simply be removed now. *sigh*
            #FIXME: Actually, in that case, we can simply reduce the following
            #two calls to simply:
            #    die_if_hint_pep_ignorable(
            #        hint=hint_curr, exception_prefix=hint_curr_exception_prefix)
            #Of course, this implies we want to refactor the
            #die_if_hint_pep_unsupported() function into
            #die_if_hint_pep_ignorable()... probably.

            # If this hint is currently unsupported, raise an exception.
            #
            # Note the human-readable label prefixing the representations of
            # child PEP-compliant type hints is unconditionally passed. Since
            # the root hint has already been validated to be supported by
            # the above call to the same function, this call is guaranteed to
            # *NEVER* raise an exception for that hint.
            die_if_hint_pep_unsupported(
                hint=hint_curr, exception_prefix=hint_curr_exception_prefix)
            # Else, this hint is supported.

            # Assert that this hint is unignorable. Iteration below generating
            # code for child hints of the current parent hint is *REQUIRED* to
            # explicitly ignore ignorable child hints. Since the caller has
            # explicitly ignored ignorable root hints, these two guarantees
            # together ensure that all hints visited by this breadth-first
            # search *SHOULD* be unignorable. Naturally, we validate that here.
            assert not is_hint_ignorable(hint_curr), (
                f'{hint_curr_exception_prefix}ignorable type hint {repr(hint_curr)} '
                f'not ignored.')

            # Sign uniquely identifying this hint.
            hint_curr_sign = get_hint_pep_sign(hint_curr)
            # print(f'Type-checking PEP type hint {repr(hint_curr)} sign {repr(hint_curr_sign)}...')

            # If this sign is currently unsupported, raise an exception.
            #
            # Note the human-readable label prefixing the representations of
            # child PEP-compliant type hints is unconditionally passed. Since
            # the root hint has already been validated to be supported by the
            # above call to the die_if_hint_pep_unsupported() function, this
            # call is guaranteed to *NEVER* raise exceptions for the root hint.
            die_if_hint_pep_sign_unsupported(
                hint_sign=hint_curr_sign, exception_prefix=hint_curr_exception_prefix)
            # Else, this attribute is supported.

            # If this hint is deprecated, emit a non-fatal warning.
            # print(f'Testing {hint_curr_exception_prefix} hint {repr(hint_curr)} for deprecation...')
            warn_if_hint_pep_deprecated(
                hint=hint_curr, warning_prefix=hint_curr_exception_prefix)

            # Tuple of all arguments subscripting this hint if any *OR* the
            # empty tuple otherwise (e.g., if this hint is its own unsubscripted
            # "typing" attribute).
            #
            # Note that the "__args__" dunder attribute is *NOT* guaranteed to
            # exist for arbitrary PEP-compliant type hints. Ergo, we obtain
            # this attribute via a higher-level utility getter instead.
            hint_childs = get_hint_pep_args(hint_curr)
            hint_childs_len = len(hint_childs)

            #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            # NOTE: Whenever adding support for (i.e., when generating code
            # type-checking) a new "typing" attribute below, similar support
            # for that attribute *MUST* also be added to the parallel:
            # * "beartype._util.hint.pep.errormain" submodule, which
            #   raises exceptions on the current pith failing this check.
            # * "beartype._data.hint.pep.sign.datapepsignset.HINT_SIGNS_SUPPORTED_DEEP"
            #   frozen set of all signs for which this function generates
            #   deeply type-checking code.
            #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

            #FIXME: Python 3.10 provides proper syntactic support for "case"
            #statements, which should allow us to dramatically optimize this
            #"if" logic into equivalent "case" logic *AFTER* we drop support
            #for Python 3.9. Of course, that will be basically never, so we'll
            #have to preserve this for basically forever. What you gonna do?

            # Switch on (as in, pretend Python provides a "case" statement)
            # the sign identifying this hint to decide which type of code to
            # generate to type-check the current pith against the current hint.
            #
            # This decision is intentionally implemented as a linear series of
            # tests ordered in descending likelihood for efficiency. While
            # alternative implementations (that are more readily readable and
            # maintainable) do exist, these alternatives all appear to be
            # substantially less efficient.
            #
            # Consider the standard alternative of sequestering the body of
            # each test implemented below into either:
            #
            # * A discrete private function called by this function. This
            #   approach requires maintaining a global private dictionary
            #   mapping from each support unsubscripted typing attribute to
            #   the function generating code for that attribute: e.g.,
            #      def pep_code_check_union(...): ...
            #      _HINT_TYPING_ATTR_ARGLESS_TO_CODER = {
            #          typing.Union: pep_code_check_union,
            #      }
            #   Each iteration of this loop then looks up the function
            #   generating code for the current attribute from this dictionary
            #   and calls that function to do so. Function calls come with
            #   substantial overhead in Python, impacting performance more
            #   than the comparable linear series of tests implemented below.
            #   Additionally, these functions *MUST* mutate local variables of
            #   this function by some arcane means -- either:
            #   * Passing these locals to each such function, returning these
            #     locals from each such function, and assigning these return
            #     values to these locals in this function after each such call.
            #   * Passing a single composite fixed list of these locals to each
            #     such function, which then mutates these locals in-place,
            #     which then necessitates this function permanently store these
            #     locals in such a list rather than as local variables.
            # * A discrete closure of this function, which adequately resolves
            #   the aforementioned locality issue via the "nonlocal" keyword at
            #   a substantial up-front performance cost of redeclaring these
            #   closures on each invocation of this function.
            #
            # ..............{ SHALLOW                           }..............
            # Perform shallow type-checking logic (i.e., logic that does *NOT*
            # recurse and thus "bottoms out" at this hint) *BEFORE* deep
            # type-checking logic. The latter needs additional setup (e.g.,
            # generation of assignment expressions) *NOT* needed by the former,
            # whose requirements are more understandably minimalist.
            #
            # ..............{ ORIGIN                            }..............
            # If this hint both...
            if (
                # Originates from an origin type and may thus be shallowly
                # type-checked against that type *AND is either...
                hint_curr_sign in HINT_SIGNS_ORIGIN_ISINSTANCEABLE and (
                    #FIXME: Ideally, this line should just resemble:
                    #    not is_hint_pep_args(hint_curr)
                    #Unfortunately, unsubscripted type hints under Python 3.6
                    #like "typing.List" are technically subscripted due to
                    #subclassing subscripted superclasses, which is insane. Due
                    #to this insanity, we currently ignore type variables for
                    #purposes of detecting subscription. Since this is awful,
                    #drop this as soon as we drop Python 3.6 support.
                    # Unsubscripted *OR*...
                    not (
                        is_hint_pep_args(hint_curr)
                        if IS_PYTHON_AT_LEAST_3_7 else
                        hint_childs_len
                    ) or
                    #FIXME: Remove this branch *AFTER* deeply supporting all
                    #hints.
                    # Currently unsupported with deep type-checking...
                    hint_curr_sign not in HINT_SIGNS_SUPPORTED_DEEP
                )
            ):
            # Then generate trivial code shallowly type-checking the current
            # pith as an instance of the origin type originating this sign
            # (e.g., "list" for the hint "typing.List[int]").
                # Code type-checking the current pith against this origin type.
                func_curr_code = PEP484_CODE_HINT_INSTANCE_format(
                    pith_curr_expr=pith_curr_expr,
                    # Python expression evaluating to this origin type.
                    hint_curr_expr=add_func_scope_type(
                        # Origin type of this hint if any *OR* raise an
                        # exception -- which should *NEVER* happen, as this
                        # hint was validated above to be supported.
                        cls=get_hint_pep_origin_type_isinstanceable(hint_curr),
                        func_scope=func_wrapper_locals,
                        exception_prefix=_EXCEPTION_PREFIX_FUNC_WRAPPER_LOCAL,
                    ),
                )
            # Else, this hint is either subscripted, not shallowly
            # type-checkable, *OR* deeply type-checkable.
            #
            # ..............{ FORWARDREF                        }..............
            # If this hint is a forward reference...
            elif hint_curr_sign is HintSignForwardRef:
                # Render this forward reference accessible to the body of this
                # wrapper function by populating:
                # * Python expression evaluating to the class referred to by
                #   this forward reference when accessed via the private
                #   "__beartypistry" parameter.
                # * Set of the unqualified classnames referred to by all
                #   relative forward references, including this reference if
                #   relative. If this set was previously uninstantiated (i.e.,
                #   "None"), this assignment initializes this local to the new
                #   set instantiated by this call; else, this assignment
                #   preserves this local set as is.
                hint_curr_expr, hint_forwardrefs_class_basename = (
                    express_func_scope_type_forwardref(
                        forwardref=hint_curr,
                        forwardrefs_class_basename=(
                            hint_forwardrefs_class_basename),
                        func_scope=func_wrapper_locals,
                        exception_prefix=hint_curr_exception_prefix,
                    ))

                # Code type-checking the current pith against this class.
                func_curr_code = PEP484_CODE_HINT_INSTANCE_format(
                    pith_curr_expr=pith_curr_expr,
                    hint_curr_expr=hint_curr_expr,
                )
            # Else, this hint is *NOT* a forward reference.
            #
            # Since this hint is *NOT* shallowly type-checkable, this hint
            # *MUST* be deeply type-checkable. So, we do so now.
            #
            # ..............{ DEEP                              }..............
            # Perform deep type-checking logic (i.e., logic that recurses and
            # thus does *NOT* "bottom out" at this hint).
            else:
                # Python code snippet expanding to the current level of
                # indentation appropriate for the current child hint.
                #
                # Note that this is almost always but technically *NOT* always
                # required below by logic generating code type-checking the
                # currently visited parent hint. Naturally, unconditionally
                # setting this string here trivially optimizes the common case.
                indent_child = f'{indent_curr}{_CODE_INDENT_1}'

                # ............{ DEEP ~ expression                 }............
                #FIXME: Unit test that this is behaving as expected. Doing so will
                #require further generalizations, including:
                #* In the "beartype._decor.main" submodule:
                #  * Detect when running under tests.
                #  * When running under tests, define a new
                #    "func_wrapper.__beartype_wrapper_code" attribute added to
                #    decorated callables to be the "func_wrapper_code" string
                #    rather than True. Note that this obviously isn't the right way
                #    to do source code association. Ideally, we'd at least
                #    interface with the stdlib "linecache" module (e.g., by calling
                #    the linecache.lazycache() function intended to be used to
                #    cache the source code for non-file-based modules) and possibly
                #    even go so far as to define a PEP 302-compatible beartype
                #    module loader. That's out of scope, so this suffices for now.
                #* In the "beartype_test.a00_unit.data._data_hint_pep" submodule:
                #  * Add a new "_PepHintMetadata.code_str_match_regexes" field,
                #    defined as an iterable of regular expressions matching
                #    substrings of the "func_wrapper.__beartype_wrapper_code"
                #    attribute that are expected to exist.
                #  * For most "HINTS_PEP_META" entries, default this field to
                #    merely the empty tuple.
                #  * For deeply nested "HINTS_PEP_META" entries, define this
                #    field as follows:
                #        code_str_match_regexes=(r'\s+:=\s+',)
                #* In the "beartype_test.a00_unit.pep.p484.test_p484" submodule:
                #  * Match the "pep_hinted.__beartype_wrapper_code" string against
                #    all regular expressions in the "code_str_match_regexes"
                #    iterable for the currently iterated "pep_hint_meta".
                #
                #This is fairly important, as we have no other reusable means of
                #ascertaining whether this is actually being applied in general.
                #FIXME: That's all great, except for the
                #"func_wrapper.__beartype_wrapper_code" part. Don't do that,
                #please. We really do just want to do this right the first time. As
                #expected, the key to doing so is the linecache.lazycache()
                #function, whose implementation under Python 3.7 reads:
                #
                #    def lazycache(filename, module_globals):
                #        """Seed the cache for filename with module_globals.
                #
                #        The module loader will be asked for the source only when getlines is
                #        called, not immediately.
                #
                #        If there is an entry in the cache already, it is not altered.
                #
                #        :return: True if a lazy load is registered in the cache,
                #            otherwise False. To register such a load a module loader with a
                #            get_source method must be found, the filename must be a cachable
                #            filename, and the filename must not be already cached.
                #        """
                #        if filename in cache:
                #            if len(cache[filename]) == 1:
                #                return True
                #            else:
                #                return False
                #        if not filename or (filename.startswith('<') and filename.endswith('>')):
                #            return False
                #        # Try for a __loader__, if available
                #        if module_globals and '__loader__' in module_globals:
                #            name = module_globals.get('__name__')
                #            loader = module_globals['__loader__']
                #            get_source = getattr(loader, 'get_source', None)
                #
                #            if name and get_source:
                #                get_lines = functools.partial(get_source, name)
                #                cache[filename] = (get_lines,)
                #                return True
                #        return False
                #
                #Given that, what we need to do is:
                #* Define a new "beartype._decor._pep302" submodule implementing a
                #  PEP 302-compatible loader for @beartype-generated wrapper
                #  functions, enabling external callers (including the stdlib
                #  "linecache" module) to obtain the source for these functions.
                #  For space efficiency, this submodule should internally store
                #  code in a compressed format -- which probably means "gzip" for
                #  maximal portability. This submodule should at least define these
                #  attributes:
                #  * "_FUNC_WRAPPER_MODULE_NAME_TO_CODE", a dictionary mapping from
                #    the unique fake module names assigned to @beartype-generated
                #    wrapper functions by the @beartype decorator to the compressed
                #    source strings for those fake modules.
                #  * get_source(), a function accepting one unique fake module name
                #    assigned to an arbitrary @beartype-generated wrapper function
                #    by the @beartype decorator and returning the uncompressed
                #    source string for that fake module. Clearly, this function
                #    should internally access the
                #    "_FUNC_WRAPPER_MODULE_NAME_TO_CODE" dictionary and either:
                #    * If the passed module name has *NOT* already been registered
                #      to that dictionary, raise an exception.
                #    * Else, uncompress the compressed source string previously
                #      registered under that module name with that dictionary and
                #      return that uncompressed string. Don't worry about caching
                #      uncompressed strings here; that's exactly what the stdlib
                #      "linecache" module already does on our behalf.
                #    Ergo, this function should have signature resembling:
                #        def get_source(func_wrapper_module_name: str) -> str:
                #  * set_source(), a function accepting one unique fake module name
                #    assigned to an arbitrary @beartype-generated wrapper function
                #    by the @beartype decorator as well as as the uncompressed
                #    source string for that fake module. Clearly, this function
                #    should internally
                #    "_FUNC_WRAPPER_MODULE_NAME_TO_CODE" dictionary and either:
                #    * If the passed module name has already been registered to
                #      that dictionary, raise an exception.
                #    * Else, compress the passed uncompressed source string and
                #      register that compressed string under that module name with
                #      that dictionary.
                #* In the "beartype._decor.main" submodule:
                #  * Do... something? Oh, boy. Why didn't we finish this comment?

                # If the active Python interpreter targets Python >= 3.8 and
                # thus supports assignment expressions...
                if IS_PYTHON_AT_LEAST_3_8:
                    # If...
                    if (
                        # The current pith is not the root pith *AND*...
                        #
                        # Note that we explicitly test against piths rather
                        # than seemingly equivalent metadata to account for
                        # edge cases. Notably, child hints of unions (and
                        # possibly other "typing" objects) do *NOT* narrow the
                        # current pith and are *NOT* the root hint. Ergo, a
                        # seemingly equivalent test like "hints_meta_index_curr
                        # != 0" would generate false positives and thus
                        # unnecessarily inefficient code.
                        pith_curr_expr is not PITH_ROOT_VAR_NAME and

                        #FIXME: Overly ambiguous, unfortunately. This suffices
                        #for now but absolutely *WILL* fail with inscrutable
                        #errors under some future release. The issue is that
                        #this trivial test reports false negatives for
                        #sufficiently complex "pith_curr_expr" strings.
                        #
                        #For example, if "pith_curr_expr ==
                        #'(yam := yum[0])[1]'", the detection below would
                        #incorrectly detect that as being an assignment
                        #expression. It isn't. It *CONTAINS* an embedded
                        #assignment expression, but it itself is *NOT* an
                        #assignment expression. Ergo, that "pith_curr_expr"
                        #should be assigned via an assignment expression here.
                        #
                        #To handle embedded assignment expressions like that,
                        #we'll probably need to generalize this yet again:
                        #* Define a new "HINT_META_INDEX_IS_PITH_EXPR_ASSIGN"
                        #  global.
                        #* Define a new "is_pith_curr_expr_assign" local,
                        #  "True" only if "pith_curr_expr" itself is an
                        #  assignment expression, defaulting to "False":
                        #      is_pith_curr_expr_assign = False
                        #* Assign above:
                        #      is_pith_curr_expr_assign = hint_curr_meta[
                        #          HINT_META_INDEX_IS_PITH_EXPR_ASSIGN]
                        #* Assign below in the body of this "if" conditional:
                        #      is_pith_curr_expr_assign = True
                        #* Assign below in the body of this "else" branch:
                        #      is_pith_curr_expr_assign = False
                        #* Pass "is_pith_curr_expr_assign" in the
                        #  _enqueue_hint_child() closure above.
                        #* Replace this "':=' not in pith_curr_expr" test here
                        #  with "not is_pith_curr_expr_assign" instead.
                        #
                        #Voila! What could be simpler? O_o

                        # The current pith expression does *NOT* already
                        # perform an assignment expression...
                        #
                        # If the current pith expression already performs an
                        # assignment expression, there's no benefit to
                        # assigning that to another local variable via another
                        # assignment expression, which would just be an alias
                        # of the existing local variable assigned via the
                        # existing assignment expression. Moreover, whereas
                        # chained assignments are syntactically valid, chained
                        # assignment expressions are syntactically invalid
                        # unless protected with parens:
                        #     >>> a = b =    'Mother*Teacher*Destroyer'  # <-- fine
                        #     >>> (a :=      "Mother's Abomination")     # <-- fine
                        #     >>> (a := (b := "Mother's Illumination"))  # <-- fine
                        #     >>> (a := b := "Mother's Illumination")    # <-- not fine
                        #     SyntaxError: invalid syntax
                        ':=' not in pith_curr_expr
                    ):
                    # Then all conditions needed to assign the current pith to
                    # a unique local variable via a Python >= 3.8-specific
                    # assignment expression are satisfied. In this case...
                        # Increment the integer suffixing the name of this
                        # variable *BEFORE* defining this local variable.
                        pith_curr_assign_expr_name_counter += 1

                        # Reduce the current pith expression to the name of
                        # this local variable.
                        pith_curr_var_name = (
                            f'{VAR_NAME_PREFIX_PITH}'
                            f'{pith_curr_assign_expr_name_counter}'
                        )

                        # Python >= 3.8-specific assignment expression
                        # assigning this full expression to this variable.
                        pith_curr_assign_expr = (
                            PEP_CODE_PITH_ASSIGN_EXPR_format(
                                pith_curr_var_name=pith_curr_var_name,
                                pith_curr_expr=pith_curr_expr,
                            ))
                    # Else, one or more of the above conditions have *NOT* been
                    # satisfied. In this case, preserve the Python code snippet
                    # evaluating to the current pith as is.
                    else:
                        pith_curr_assign_expr = pith_curr_expr
                # Else, the active Python interpreter targets Python < 3.8 and
                # thus does *NOT* support assignment expressions. In this case,
                # assign the variables assigned above to sane expressions.
                else:
                    pith_curr_assign_expr = pith_curr_var_name = pith_curr_expr

                # ............{ UNION                             }............
                # If this hint is a union (e.g., "typing.Union[bool, str]",
                # typing.Optional[float]")...
                #
                # Note that unions are non-physical abstractions of physical
                # types and thus *NOT* themselves subject to type-checking;
                # only the subscripted arguments of unions are type-checked.
                # This differs from "typing" pseudo-containers like
                # "List[int]", in which both the parent "List" and child "int"
                # types represent physical types to be type-checked. Ergo,
                # unions themselves impose no narrowing of the current pith
                # expression and thus *CANNOT* by definition benefit from
                # Python >= 3.8-specific assignment expressions. This differs
                # from "typing" pseudo-containers, which narrow the current
                # pith expression and thus do benefit from these expressions.
                if hint_curr_sign in HINT_SIGNS_UNION:
                    # Assert this union to be subscripted by one or more child
                    # hints. Note this should *ALWAYS* be the case, as:
                    # * The unsubscripted "typing.Union" object is explicitly
                    #   listed in the "HINTS_REPR_IGNORABLE_SHALLOW" set and
                    #   should thus have already been ignored when present.
                    # * The "typing" module explicitly prohibits empty union
                    #   subscription: e.g.,
                    #       >>> typing.Union[]
                    #       SyntaxError: invalid syntax
                    #       >>> typing.Union[()]
                    #       TypeError: Cannot take a Union of no types.
                    assert hint_childs, (
                        f'{hint_curr_exception_prefix}union type hint {repr(hint_curr)} '
                        f'unsubscripted.')
                    # Else, this union is subscripted by two or more arguments.
                    # Why two rather than one? Because the "typing" module
                    # reduces unions of one argument to that argument: e.g.,
                    #     >>> import typing
                    #     >>> typing.Union[int]
                    #     int

                    # Acquire a pair of sets for use in prefiltering child
                    # hints into the subset of all PEP-noncompliant and
                    # -compliant child hints subscripting this union. For
                    # efficiency, reuse previously created sets if available.
                    #
                    # Since these child hints require fundamentally different
                    # forms of type-checking, prefiltering child hints into
                    # these sets *BEFORE* generating code type-checking these
                    # child hints improves both efficiency and maintainability.
                    hint_childs_nonpep = acquire_object_typed(set)
                    hint_childs_pep = acquire_object_typed(set)

                    # Clear these sets prior to use below.
                    hint_childs_nonpep.clear()
                    hint_childs_pep.clear()

                    # For each subscripted argument of this union...
                    for hint_child in hint_childs:
                        #FIXME: Uncomment as desired for debugging. This test is
                        #currently a bit too costly to warrant uncommenting.
                        # Assert that this child hint is *NOT* shallowly ignorable.
                        # Why? Because any union containing one or more shallowly
                        # ignorable child hints is deeply ignorable and should thus
                        # have already been ignored after a call to the
                        # is_hint_ignorable() tester passed this union on handling
                        # the parent hint of this union.
                        # assert (
                        #     repr(hint_curr) not in HINTS_REPR_IGNORABLE_SHALLOW), (
                        #     f'{hint_curr_exception_prefix} {repr(hint_curr)} child '
                        #     f'{repr(hint_child)} ignorable but not ignored.')

                        # If this child hint is PEP-compliant...
                        if is_hint_pep(hint_child):
                            # Filter this child hint into the set of
                            # PEP-compliant child hints.
                            #
                            # Note that this PEP-compliant child hint *CANNOT*
                            # also be filtered into the set of PEP-noncompliant
                            # child hints, even if this child hint originates
                            # from a non-"typing" type (e.g., "List[int]" from
                            # "list"). Why? Because that would then induce
                            # false positives when the current pith shallowly
                            # satisfies this non-"typing" type but does *NOT*
                            # deeply satisfy this child hint.
                            hint_childs_pep.add(hint_child)
                        # Else, this child hint is PEP-noncompliant. In this
                        # case, filter this child hint into the list of
                        # PEP-noncompliant arguments.
                        else:
                            hint_childs_nonpep.add(hint_child)

                    # Initialize the code type-checking the current pith
                    # against these arguments to the substring prefixing all
                    # such code.
                    func_curr_code = PEP484_CODE_HINT_UNION_PREFIX

                    # If this union is subscripted by one or more
                    # PEP-noncompliant child hints, generate and append
                    # efficient code type-checking these child hints *BEFORE*
                    # less efficient code type-checking any PEP-compliant child
                    # hints subscripting this union.
                    if hint_childs_nonpep:
                        func_curr_code += (
                            PEP484_CODE_HINT_UNION_CHILD_NONPEP_format(
                                # Python expression yielding the value of the
                                # current pith. Specifically...
                                pith_curr_expr=(
                                    # If this union is subscripted by one or
                                    # more PEP-compliant child hints, prefer
                                    # the expression assigning this value to a
                                    # local variable efficiently reused by
                                    # subsequent code generated for
                                    # PEP-compliant child hints.
                                    pith_curr_assign_expr if hint_childs_pep else
                                    # Else, this union is *NOT* subscripted by
                                    # one or more PEP-compliant child hints.
                                    # Since this is the first and only test
                                    # generated for this union, prefer the
                                    # expression yielding the value of the
                                    # current pith *WITHOUT* assigning this
                                    # value to a local variable, which would
                                    # otherwise pointlessly go unused.
                                    pith_curr_expr
                                ),
                                # Python expression evaluating to a tuple of
                                # these arguments.
                                #
                                # Note that we would ideally avoid coercing
                                # this set into a tuple when this set only
                                # contains one type by passing that type
                                # directly to the
                                # _add_func_wrapper_local_type() function.
                                # Sadly, the "set" class defines no convenient
                                # or efficient means of retrieving the only
                                # item of a 1-set. Indeed, the most efficient
                                # means of doing so is to iterate over that set
                                # and break:
                                #     for first_item in muh_set: break
                                # While we *COULD* technically leverage that
                                # approach here, doing so would also mandate
                                # adding multiple intermediate tests,
                                # mitigating any performance gains. Ultimately,
                                # we avoid doing so by falling back to the
                                # usual approach. See also this relevant
                                # self-StackOverflow post:
                                #       https://stackoverflow.com/a/40054478/2809027
                                hint_curr_expr=add_func_scope_types(
                                    types=hint_childs_nonpep,
                                    func_scope=func_wrapper_locals,
                                    exception_prefix=(
                                        _EXCEPTION_PREFIX_FUNC_WRAPPER_LOCAL),
                                ),
                            ))

                    # For each PEP-compliant child hint of this union, generate
                    # and append code type-checking this child hint.
                    for hint_child_index, hint_child in enumerate(
                        hint_childs_pep):
                        func_curr_code += (
                            PEP484_CODE_HINT_UNION_CHILD_PEP_format(
                                # Python expression yielding the value of the
                                # current pith.
                                hint_child_placeholder=_enqueue_hint_child(
                                    # If this union is subscripted by either...
                                    #
                                    # Then prefer the expression efficiently
                                    # reusing the value previously assigned to
                                    # a local variable by either the above
                                    # conditional or prior iteration of the
                                    # current conditional.
                                    pith_curr_var_name
                                    if (
                                        # One or more PEP-noncompliant child
                                        # hints *OR*...
                                        hint_childs_nonpep or
                                        # This is any PEP-compliant child hint
                                        # *EXCEPT* the first...
                                        hint_child_index
                                    ) else
                                    # Else, this union is both subscripted by
                                    # no PEP-noncompliant child hints *AND*
                                    # this is the first PEP-compliant child
                                    # hint, prefer the expression assigning
                                    # this value to a local variable
                                    # efficiently reused by code generated by
                                    # subsequent iteration.
                                    #
                                    # Note this child hint is guaranteed to be
                                    # followed by at least one more child hint.
                                    # Why? Because the "typing" module forces
                                    # unions to be subscripted by two or more
                                    # child hints. By deduction, those child
                                    # hints *MUST* be PEP-compliant. Ergo, we
                                    # needn't explicitly validate that
                                    # constraint here.
                                    pith_curr_assign_expr
                                )))

                    # If this code is *NOT* its initial value, this union is
                    # subscripted by one or more unignorable child hints and
                    # the above logic generated code type-checking these child
                    # hints. In this case...
                    if func_curr_code is not (
                        PEP484_CODE_HINT_UNION_PREFIX):
                        # Munge this code to...
                        func_curr_code = (
                            # Strip the erroneous " or" suffix appended by the
                            # last child hint from this code.
                            f'{func_curr_code[:_LINE_RSTRIP_INDEX_OR]}'
                            # Suffix this code by the substring suffixing all
                            # such code.
                            f'{PEP484_CODE_HINT_UNION_SUFFIX}'
                        # Format the "indent_curr" prefix into this code
                            # deferred above for efficiency.
                        ).format(indent_curr=indent_curr)
                    # Else, this snippet is its initial value and thus
                    # ignorable.

                    # Release this pair of sets back to their respective pools.
                    release_object_typed(hint_childs_nonpep)
                    release_object_typed(hint_childs_pep)
                # Else, this hint is *NOT* a union.
                #
                # ..........{ SEQUENCES ~ variadic                }............
                # If this hint is either...
                elif (
                    # A standard sequence (e.g., "typing.List[int]") *OR*...
                    hint_curr_sign in HINT_SIGNS_SEQUENCE_ARGS_1 or (
                        # A tuple *AND*...
                        hint_curr_sign is HintSignTuple and
                        # This tuple is subscripted by exactly two child hints
                        # *AND*...
                        hint_childs_len == 2 and
                        # The second child hint is just an unquoted ellipsis...
                        hint_childs[1] is Ellipsis
                    )
                    # Then this hint is of the form "Tuple[{typename}, ...]",
                    # typing a tuple accepting a variadic number of items all
                    # satisfying the "{typename}" child hint. Since this case
                    # is semantically equivalent to that of standard sequences,
                    # we transparently handle both here for maintainability.
                    #
                    # See below for logic handling fixed-length tuples.
                ):
                # Then this hint is either a single-argument sequence *OR* a
                # similar hint semantically resembling a single-argument
                # sequence subscripted by one argument and one or more
                # ignorable arguments.

                    # Python expression evaluating to this origin type.
                    hint_curr_expr = add_func_scope_type(
                        # Origin type of this sequence.
                        cls=get_hint_pep_origin_type_isinstanceable(hint_curr),
                        func_scope=func_wrapper_locals,
                        exception_prefix=_EXCEPTION_PREFIX_FUNC_WRAPPER_LOCAL,
                    )
                    # print(f'Sequence type hint {hint_curr} origin type scoped: {hint_curr_expr}')

                    # If this hint is a fixed-length tuple, the parent "if"
                    # statement above has already validated the contents of
                    # this tuple. In this case, efficiently get the lone child
                    # hint of this parent hint *WITHOUT* validation.
                    if hint_curr_sign is HintSignTuple:
                        hint_child = hint_childs[0]
                    # Else, this hint is a single-argument sequence, in which
                    # case the contents of this sequence have yet to be
                    # validated. In this case, inefficiently get the lone child
                    # hint of this parent hint *WITH* validation.
                    else:
                        hint_child = get_hint_pep484585_args_1(
                            hint=hint_curr, exception_prefix=hint_curr_exception_prefix)

                    # If this child hint is *NOT* ignorable, deeply type-check
                    # both the type of the current pith *AND* a randomly
                    # indexed item of this pith. Specifically...
                    if not is_hint_ignorable(hint_child):
                        # Record that a pseudo-random integer is now required.
                        is_var_random_int_needed = True

                        # Code type-checking this pith against this type.
                        func_curr_code = (
                            PEP484585_CODE_HINT_SEQUENCE_ARGS_1_format(
                                indent_curr=indent_curr,
                                pith_curr_assign_expr=pith_curr_assign_expr,
                                pith_curr_var_name=(
                                    pith_curr_var_name),
                                hint_curr_expr=hint_curr_expr,
                                hint_child_placeholder=_enqueue_hint_child(
                                    # Python expression yielding the value of a
                                    # randomly indexed item of the current pith
                                    # (i.e., standard sequence) to be
                                    # type-checked against this child hint.
                                    PEP484585_CODE_HINT_SEQUENCE_ARGS_1_PITH_CHILD_EXPR_format(
                                        pith_curr_var_name=(
                                            pith_curr_var_name))),
                            ))
                    # Else, this child hint is ignorable. In this case,
                    # fallback to generating trivial code shallowly
                    # type-checking the current pith as an instance of this
                    # origin type.
                    else:
                        func_curr_code = (
                            PEP484_CODE_HINT_INSTANCE_format(
                                pith_curr_expr=pith_curr_expr,
                                hint_curr_expr=hint_curr_expr,
                            ))
                # Else, this hint is neither a standard sequence *NOR* variadic
                # tuple.
                #
                # ............{ SEQUENCES ~ tuple : fixed         }............
                # If this hint is a tuple, this tuple is *NOT* of the variadic
                # form and *MUST* thus be of the fixed-length form.
                #
                # Note that if this hint is a:
                # * PEP 484-compliant "typing.Tuple"-based hint, this hint is
                #   guaranteed to contain one or more child hints. Moreover, if
                #   this hint contains exactly one child hint that is the empty
                #   tuple, this hint is the empty fixed-length form
                #   "typing.Tuple[()]".
                # * PEP 585-compliant "tuple"-based hint, this hint is *NOT*
                #   guaranteed to contain one or more child hints. If this hint
                #   contains *NO* child hints, this hint is equivalent to the
                #   empty fixed-length PEP 484-compliant form
                #   "typing.Tuple[()]". Yes, PEP 585 even managed to violate
                #   PEP 484-compliance. UUUURGH!
                #
                # While tuples are sequences, the "typing.Tuple" singleton that
                # types tuples violates the syntactic norms established for
                # other standard sequences by concurrently supporting two
                # different syntaxes with equally different semantics:
                # * "typing.Tuple[{typename}, ...]", typing a tuple whose items
                #   all satisfy the "{typename}" child hint. Note that the
                #   "..." substring here is a literal ellipses.
                # * "typing.Tuple[{typename1}, {typename2}, ..., {typenameN}]",
                #   typing a tuple whose:
                #   * First item satisfies the "{typename1}" child hint.
                #   * Second item satisfies the "{typename2}" child hint.
                #   * Last item satisfies the "{typenameN}" child hint.
                #   Note that the "..." substring here is *NOT* a literal
                #   ellipses.
                #
                # This is what happens when non-human-readable APIs are
                # promoted.
                elif hint_curr_sign is HintSignTuple:
                    # Assert this tuple is *NOT* of the syntactic form
                    # "typing.Tuple[{typename}, ...]" handled by prior logic.
                    assert (
                        hint_childs_len <= 1 or
                        hint_childs[1] is not Ellipsis
                    ), (f'{hint_curr_exception_prefix}variadic tuple type hint '
                        f'{repr(hint_curr)} unhandled.')

                    # Initialize the code type-checking the current pith
                    # against this tuple to the substring prefixing all such
                    # code.
                    func_curr_code = PEP484585_CODE_HINT_TUPLE_FIXED_PREFIX

                    # If this hint is the empty fixed-length tuple, generate
                    # and append code type-checking the current pith to be the
                    # empty tuple. This edge case constitutes a code smell.
                    if is_hint_pep484585_tuple_empty(hint_curr):
                        func_curr_code += (
                            PEP484585_CODE_HINT_TUPLE_FIXED_EMPTY_format(
                                pith_curr_var_name=(
                                    pith_curr_var_name),
                            ))
                    # Else, that ridiculous edge case does *NOT* apply. In this
                    # case...
                    else:
                        # Append code type-checking the length of this pith.
                        func_curr_code += (
                            PEP484585_CODE_HINT_TUPLE_FIXED_LEN_format(
                                pith_curr_var_name=(
                                    pith_curr_var_name),
                                hint_childs_len=hint_childs_len,
                            ))

                        # For each child hint of this tuple...
                        for hint_child_index, hint_child in enumerate(
                            hint_childs):
                            # If this child hint is ignorable, skip to the
                            # next.
                            if is_hint_ignorable(hint_child):
                                continue
                            # Else, this child hint is unignorable.

                            # Append code type-checking this child pith.
                            func_curr_code += PEP484585_CODE_HINT_TUPLE_FIXED_NONEMPTY_CHILD_format(
                                hint_child_placeholder=_enqueue_hint_child(
                                    # Python expression yielding the value of
                                    # the currently indexed item of this tuple
                                    # to be type-checked against this child
                                    # hint.
                                    PEP484585_CODE_HINT_TUPLE_FIXED_NONEMPTY_PITH_CHILD_EXPR_format(
                                        pith_curr_var_name=(
                                            pith_curr_var_name),
                                        pith_child_index=hint_child_index,
                                    )
                                ),
                            )

                    # Munge this code to...
                    func_curr_code = (
                        # Strip the erroneous " and" suffix appended by the
                        # last child hint from this code.
                        f'{func_curr_code[:_LINE_RSTRIP_INDEX_AND]}'
                        # Suffix this code by the substring suffixing all such
                        # code.
                        f'{PEP484585_CODE_HINT_TUPLE_FIXED_SUFFIX}'
                    # Format...
                    ).format(
                        # Indentation deferred above for efficiency.
                        indent_curr=indent_curr,
                        pith_curr_assign_expr=pith_curr_assign_expr,
                    )
                # Else, this hint is *NOT* a tuple.
                #
                # ............{ ANNOTATED                         }............
                # If this hint is a PEP 593-compliant type metahint, this
                # metahint is guaranteed by the reduction performed above to be
                # beartype-specific (i.e., metahint whose second argument is a
                # beartype validator produced by subscripting a beartype
                # validator factory). In this case...
                elif hint_curr_sign is HintSignAnnotated:
                    # PEP-compliant type hint annotated by this metahint,
                    # localized to the "hint_child" local variable to satisfy
                    # the public API of the _enqueue_hint_child() closure
                    # called below.
                    hint_child = get_hint_pep593_metahint(hint_curr)

                    # Initialize the code type-checking this pith against this
                    # metahint to the substring prefixing all such code.
                    #
                    # Note that we intentionally do *NOT* defer formatting
                    # these variables into this string as we do for most other
                    # kinds of type hints. Why? Safety. Since caller-defined
                    # code could theoretically embed substrings accidentally
                    # matching these variable names, we safely (but
                    # inefficiently) format these variables into the exact
                    # strings known to embed them.
                    func_curr_code = (
                        PEP593_CODE_HINT_VALIDATOR_PREFIX_format(
                            indent_curr=indent_curr,
                            hint_child_placeholder=_enqueue_hint_child(
                                # Python expression yielding the value of the
                                # current pith assigned to a local variable
                                # efficiently reused by code generated by the
                                # following iteration.
                                #
                                # Note this child hint is guaranteed to be
                                # followed by at least one more test expression
                                # referencing this local variable. Why? Because
                                # the "typing" module forces metahints to be
                                # subscripted by one child hint and one or more
                                # arbitrary objects. Ergo, we needn't
                                # explicitly validate that here.
                                pith_curr_assign_expr),
                        ))

                    # For each beartype validator annotating this metahint...
                    for hint_child in get_hint_pep593_metadata(hint_curr):
                        # print(f'Type-checking PEP 593 type hint {repr(hint_curr)} argument {repr(hint_child)}...')
                        # If this is *NOT* a beartype validator, raise an
                        # exception.
                        #
                        # Note that the previously called sanify_hint_child()
                        # function validated only the first such to be a
                        # beartype validator. All remaining arguments have yet
                        # to be validated, so we do so now for consistency and
                        # safety.
                        if not isinstance(hint_child, BeartypeValidator):
                            raise BeartypeDecorHintPep593Exception(
                                f'{hint_curr_exception_prefix}'
                                f'PEP 593 type hint '
                                f'{repr(hint_curr)} subscripted by both '
                                f'@beartype-specific and -agnostic metadata '
                                f'(i.e., {represent_object(hint_child)} not '
                                f'beartype validator).'
                            )
                        # Else, this argument is beartype-specific.

                        # Generate and append efficient code type-checking this
                        # validator by embedding this code as is.
                        func_curr_code += (
                            PEP593_CODE_HINT_VALIDATOR_CHILD_format(
                                indent_curr=indent_curr,
                                # Python expression formatting the current pith
                                # into the "{obj}" variable already embedded by
                                # that class into this code.
                                hint_child_expr=(
                                    hint_child._is_valid_code.format(
                                        indent=indent_child,
                                        obj=pith_curr_var_name,
                                    )),
                            ))

                        # Generate locals safely merging the locals required by
                        # both this validator code *AND* the current code
                        # type-checking this entire root hint.
                        update_mapping(
                            mapping_trg=func_wrapper_locals,
                            mapping_src=hint_child._is_valid_code_locals,
                        )

                    # Munge this code to...
                    func_curr_code = (
                        # Strip the erroneous " and" suffix appended by the
                        # last child hint from this code.
                        f'{func_curr_code[:_LINE_RSTRIP_INDEX_AND]}'
                        # Suffix this code by the substring suffixing all such
                        # code.
                        f'{PEP593_CODE_HINT_VALIDATOR_SUFFIX_format(indent_curr=indent_curr)}'
                    )
                # Else, this hint is *NOT* a metahint.
                #
                # ............{ SUBCLASS                          }............
                # If this hint is either a PEP 484- or 585-compliant subclass
                # type hint...
                elif hint_curr_sign is HintSignType:
                    #FIXME: Optimization: if the superclass is an ignorable
                    #class (e.g., "object", "Protocol"), this type hint is
                    #ignorable (e.g., "Type[object]", "type[Protocol]"). We'll
                    #thus want to:
                    #* Add that detection logic to one or more
                    #  is_hint_*_ignorable() testers elsewhere.
                    #* Call is_hint_ignorable() below.
                    #* Unit test such type hints to indeed be ignorable.

                    # Superclass this pith is required to be a subclass of.
                    hint_child = get_hint_pep484585_subclass_superclass(
                        hint=hint_curr, exception_prefix=hint_curr_exception_prefix)

                    #FIXME: Unit test us up, please.

                    # If this superclass is either a class *OR* tuple of
                    # classes...
                    if isinstance(hint_child, TestableTypes):
                        # Python expression evaluating to this superclass.
                        hint_curr_expr = add_func_scope_type_or_types(
                            type_or_types=hint_child,  # type: ignore[arg-type]
                            func_scope=func_wrapper_locals,
                            exception_prefix=(
                                _EXCEPTION_PREFIX_FUNC_WRAPPER_LOCAL),
                        )

                    #FIXME: *UNIT TEST THIS PLEASE.*

                    # Else, this superclass is *NOT* actually a class. By
                    # process of elimination and the validation already
                    # performed above by the
                    # get_hint_pep484585_subclass_superclass() getter, this
                    # superclass *MUST* be a forward reference to a class.
                    else:
                        # Render this forward reference accessible to the body
                        # of this wrapper function. See above for commentary.
                        hint_curr_expr, hint_forwardrefs_class_basename = (
                            express_func_scope_type_forwardref(
                                forwardref=hint_child,
                                forwardrefs_class_basename=(
                                    hint_forwardrefs_class_basename),
                                func_scope=func_wrapper_locals,
                            ))

                    # Code type-checking this pith against this superclass.
                    func_curr_code = PEP484585_CODE_HINT_SUBCLASS_format(
                        pith_curr_assign_expr=pith_curr_assign_expr,
                        pith_curr_var_name=pith_curr_var_name,
                        hint_curr_expr=hint_curr_expr,
                        indent_curr=indent_curr,
                    )
                # Else, this hint is neither a PEP 484- nor 585-compliant
                # subclass type hint.
                #
                # ............{ GENERIC or PROTOCOL               }............
                # If this hint is either a:
                # * PEP 484-compliant generic (i.e., user-defined class
                #   subclassing a combination of one or more of the
                #   "typing.Generic" superclass and other "typing" non-class
                #   pseudo-superclasses) *OR*...
                # * PEP 544-compliant protocol (i.e., class subclassing a
                #   combination of one or more of the "typing.Protocol"
                #   superclass and other "typing" non-class
                #   pseudo-superclasses) *OR*...
                # * PEP 585-compliant generic (i.e., user-defined class
                #   subclassing at least one non-class PEP 585-compliant
                #   pseudo-superclasses) *OR*...
                # Then this hint is a PEP-compliant generic. In this case...
                elif hint_curr_sign is HintSignGeneric:
                    #FIXME: *THIS IS NON-IDEAL.* Ideally, we should propagate
                    #*ALL* child type hints subscripting a generic up to *ALL*
                    #pseudo-superclasses of that generic (e.g., the "int" child
                    #hint subscripting a parent hint "MuhGeneric[int]" of type
                    #"class MuhGeneric(list[T]): pass" up to its "list[T]"
                    #pseudo-superclass).
                    #
                    #For now, we just strip *ALL* child type hints subscripting
                    #a generic with the following call. This suffices, because
                    #we just need this to work. So it goes, uneasy code
                    #bedfellows.

                    # If this hint is *NOT* a class, this hint is *NOT* an
                    # unsubscripted generic but could still be a generic
                    # subscripted by one or more PEP-compliant child hints.
                    #
                    # To decide, reduce this hint to the object originating
                    # this hint if any, enabling the subsequent assertion to
                    # assert whether this origin object is an unsubscripted
                    # generic, which would then imply this hint to be a
                    # subscripted generic. If this strikes you as insane,
                    # you're not alone.
                    hint_curr = get_hint_pep484585_generic_type(
                        hint=hint_curr,
                        exception_prefix=hint_curr_exception_prefix,
                    )

                    # Tuple of the one or more unerased pseudo-superclasses
                    # originally listed as superclasses prior to their type
                    # erasure by this generic.
                    hint_childs = get_hint_pep484585_generic_bases_unerased(
                        hint=hint_curr, exception_prefix=hint_curr_exception_prefix)

                    # Initialize the code type-checking this pith against this
                    # generic to the substring prefixing all such code.
                    func_curr_code = PEP484585_CODE_HINT_GENERIC_PREFIX

                    # For each pseudo-superclass subclassed by this generic...
                    for hint_child in hint_childs:
                        # print(f'hint_child: {repr(hint_child)} {is_hint_pep_type_typing(hint_child)}')

                        # If this pseudo-superclass is an actual class, this
                        # class is effectively ignorable. Why? Because the
                        # "PEP484585_CODE_HINT_GENERIC_PREFIX" snippet
                        # leveraged above already type-checks this pith against
                        # the generic subclassing this superclass and thus this
                        # superclass as well with a trivial isinstance() call.
                        # In this case, skip to the next pseudo-superclass.
                        if isinstance(hint_child, type):
                            continue
                        # Else, this pseudo-superclass is *NOT* a class.
                        #
                        # If this pseudo-superclass is neither a PEP
                        # 585-compliant type hint *NOR* a PEP-compliant type
                        # hint defined by the "typing" module, this
                        # pseudo-superclass *MUST* be a user-defined
                        # pseudo-superclass *NOT* compliant with PEP
                        # 585. In this case, reduce this pseudo-superclass to
                        # the corresponding actual superclass originating
                        # this pseudo-superclass. Note that:
                        # * This horrible, irrational, and unintuitive edge
                        #   case arises *ONLY* for user-defined PEP
                        #   484-compliant generics and PEP 544-compliant
                        #   protocols subclassing another user-defined generic
                        #   or protocol superclass subscripted by one or more
                        #   type variables: e.g.,
                        #     >>> import typing as t
                        #     >>> class UserProtocol(t.Protocol[t.AnyStr]): pass
                        #     >>> class UserSubprotocol(UserProtocol[str], t.Protocol): pass
                        #     >>> UserSubprotocol.__orig_bases__
                        #     (UserProtocol[bytes], typing.Protocol)
                        #     >>> UserProtocolUnerased = UserSubprotocol.__orig_bases__[0]
                        #     >>> UserProtocolUnerased is UserProtocol
                        #     False
                        #     >>> isinstance(UserProtocolUnerased, type)
                        #     False
                        # * PEP 585-compliant generics suffer no such issues:
                        #     >>> from beartype._util.hint.pep.proposal.utilpep585 import is_hint_pep585_builtin
                        #     >>> class UserGeneric(list[int]): pass
                        #     >>> class UserSubgeneric(UserGeneric[int]): pass
                        #     >>> UserSubgeneric.__orig_bases__
                        #     (UserGeneric[int],)
                        #     >>> UserGenericUnerased = UserSubgeneric.__orig_bases__[0]
                        #     >>> isinstance(UserGenericUnerased, type)
                        #     True
                        #     >>> UserGenericUnerased.__mro__
                        #     (UserGeneric, list, object)
                        #     >>> is_hint_pep585_builtin(UserGenericUnerased)
                        #     True
                        #
                        # Walking up the unerased inheritance hierarchy for
                        # this generic or protocol iteratively visits the
                        # user-defined generic or protocol pseudo-superclass
                        # subscripted by one or more type variable. Due to
                        # poorly defined obscurities in the "typing"
                        # implementation, this pseudo-superclass is *NOT*
                        # actually a class but rather an instance of a private
                        # "typing" class (e.g., "typing._SpecialForm").
                        #
                        # Ergo, this pseudo-superclass will be subsequently
                        # detected as neither a generic nor "typing" object and
                        # thus raise exceptions. Our only recourse is to
                        # silently reduce this hint into the erased superclass
                        # to which the "typing" module previously transformed
                        # this hint (e.g., "UserProtocol" above). This is
                        # slightly non-ideal, as this erased superclass is an
                        # actual class that should ideally be ignored rather
                        # than redundantly tested against the current pith
                        # again. Nonetheless, there exists no other means of
                        # recursing into the possibly relevant superclasses of
                        # this erased superclass.
                        #
                        # Note that, in theory, we could deeply refactor this
                        # whole algorithm to support the notion of child hints
                        # that should be ignored for purposes of type-checking
                        # but nonetheless recursed into. In practice, the
                        # current approach only introduces mild runtime
                        # inefficiencies while preserving sanity throughout
                        # this algorithm.
                        #
                        # Specifically, perform this awful reduction *ONLY* if
                        # this pseudo-superclass is a PEP 484- or 544-compliant
                        # user-defined pseudo-superclass that is neither...
                        elif not (
                            # A PEP 585-compliant pseudo-superclass *NOR*...
                            is_hint_pep585_builtin(hint_child) and
                            # A PEP 484- or 544-compliant pseudo-superclass
                            # defined by the "typing" module.
                            is_hint_pep_typing(hint_child)
                        ):
                            hint_child = get_hint_pep484_generic_base_erased_from_unerased(
                                hint_child)
                        # Else, this pseudo-superclass is defined by the "typing"
                        # module.

                        # If this superclass is ignorable, do so.
                        if is_hint_ignorable(hint_child):
                            continue
                        # Else, this superclass is unignorable.

                        # Generate and append code type-checking this pith
                        # against this superclass.
                        func_curr_code += (
                            PEP484585_CODE_HINT_GENERIC_CHILD_format(
                                hint_child_placeholder=_enqueue_hint_child(
                                    # Python expression efficiently reusing the
                                    # value of this pith previously assigned to
                                    # a local variable by the prior prefix.
                                    pith_curr_var_name),
                            ))

                    # Munge this code to...
                    func_curr_code = (
                        # Strip the erroneous " and" suffix appended by the
                        # last child hint from this code.
                        f'{func_curr_code[:_LINE_RSTRIP_INDEX_AND]}'
                        # Suffix this code by the substring suffixing all such
                        # code.
                        f'{PEP484585_CODE_HINT_GENERIC_SUFFIX}'
                    # Format...
                    ).format(
                        # Indentation deferred above for efficiency.
                        indent_curr=indent_curr,
                        pith_curr_assign_expr=pith_curr_assign_expr,
                        # Python expression evaluating to this generic type.
                        hint_curr_expr=add_func_scope_type(
                            cls=hint_curr,
                            func_scope=func_wrapper_locals,
                            exception_prefix=(
                                _EXCEPTION_PREFIX_FUNC_WRAPPER_LOCAL),
                        ),
                    )
                    # print(f'{hint_curr_exception_prefix} PEP generic {repr(hint)} handled.')
                # Else, this hint is *NOT* a generic.
                #
                # ............{ LITERAL                           }............
                # If this hint is a PEP 586-compliant type hint (i.e., the
                # "typing.Literal" singleton subscripted by one or more literal
                # objects), this hint is largely useless and thus intentionally
                # detected last. Why? Because "typing.Literal" is subscriptable
                # by objects that are instances of only *SIX* possible types,
                # which is sufficiently limiting as to render this singleton
                # patently absurd and a farce that we weep to even implement.
                # In this case...
                elif hint_curr_sign is HintSignLiteral:
                    # If this hint does *NOT* comply with PEP 586 despite being
                    # a "typing.Literal" subscription, raise an exception.
                    die_unless_hint_pep586(
                        hint=hint_curr,
                        exception_prefix=hint_curr_exception_prefix,
                    )
                    # Else, this hint complies with PEP 586 and is thus
                    # subscripted by one or more compliant literal objects.

                    # Tuple of zero or more literal objects subscripting this
                    # hint, intentionally replacing the current such tuple due
                    # to the non-standard implementation of the third-party
                    # "typing_extensions.Literal" type hint factory.
                    hint_childs = get_hint_pep586_literals(
                        hint=hint_curr,
                        exception_prefix=hint_curr_exception_prefix,
                    )

                    # Initialize the code type-checking this pith against this
                    # hint to the substring prefixing all such code.
                    func_curr_code = PEP586_CODE_HINT_PREFIX_format(
                        pith_curr_assign_expr=pith_curr_assign_expr,

                        #FIXME: If "typing.Literal" is ever extended to support
                        #substantially more types (and thus actually become
                        #useful), optimize the construction of the "types" set
                        #below to instead leverage a similar
                        #"acquire_object_typed(set)" caching solution as that
                        #currently employed for unions. For now, we only shrug.

                        # Python expression evaluating to a tuple of the unique
                        # types of all literal objects subscripting this hint.
                        hint_child_types_expr=add_func_scope_types(
                            types=set(
                                type(hint_child)
                                for hint_child in hint_childs
                            ),
                            func_scope=func_wrapper_locals,
                            exception_prefix=(
                                _EXCEPTION_PREFIX_FUNC_WRAPPER_LOCAL),
                        ),
                    )

                    # For each literal object subscripting this hint...
                    for hint_child in hint_childs:
                        # Generate and append efficient code type-checking
                        # this data validator by embedding this code as is.
                        func_curr_code += (
                            PEP586_CODE_HINT_LITERAL_format(
                                pith_curr_var_name=(
                                    pith_curr_var_name),
                                # Python expression evaluating to this literal
                                # object.
                                hint_child_expr=add_func_scope_attr(
                                    attr=hint_child,
                                    func_scope=func_wrapper_locals,
                                    exception_prefix=(
                                        _EXCEPTION_PREFIX_FUNC_WRAPPER_LOCAL),
                                ),
                            ))

                    # Munge this code to...
                    func_curr_code = (
                        # Strip the erroneous " or" suffix appended by the last
                        # child hint from this code.
                        f'{func_curr_code[:_LINE_RSTRIP_INDEX_OR]}'
                        # Suffix this code by the appropriate substring.
                        f'{PEP586_CODE_HINT_SUFFIX}'
                    ).format(indent_curr=indent_curr)
                # Else, this hint is *NOT* a PEP 586-compliant type hint.

                # ............{ UNSUPPORTED                       }............
                # Else, this hint is neither shallowly nor deeply supported and
                # is thus unsupported. Since an exception should have already
                # been raised above in this case, this conditional branch
                # *NEVER* be triggered. Nonetheless, raise an exception.
                else:
                    raise BeartypeDecorHintPepUnsupportedException(
                        f'{hint_curr_exception_prefix}{repr(hint_curr)} unsupported but '
                        f'erroneously detected as supported.'
                    )

        # ................{ NON-PEP                           }................
        # Else, this hint is *NOT* PEP-compliant.
        #
        # ................{ INSTANCES                         }................
        # If this hint is a non-"typing" class...
        #
        # Note that:
        # * This test is intentionally performed *AFTER* that testing whether
        #   this hint is PEP-compliant, thus guaranteeing this hint to be a
        #   PEP-noncompliant non-"typing" class rather than a PEP-compliant
        #   type hint originating from such a class. Since many hints are both
        #   PEP-compliant *AND* originate from such a class (e.g., the "List"
        #   in "List[int]", PEP-compliant but originating from the
        #   PEP-noncompliant builtin class "list"), testing these hints first
        #   for PEP-compliance ensures we generate non-trivial code deeply
        #   type-checking these hints instead of trivial code only shallowly
        #   type-checking the non-"typing" classes from which they originate.
        # * This class is guaranteed to be a subscripted argument of a
        #   PEP-compliant type hint (e.g., the "int" in "Union[Dict[str, str],
        #   int]") rather than the root type hint. Why? Because if this class
        #   were the root type hint, it would have already been passed into a
        #   faster submodule generating PEP-noncompliant code instead.
        elif isinstance(hint_curr, type):
            # Code type-checking the current pith against this type.
            func_curr_code = PEP484_CODE_HINT_INSTANCE_format(
                pith_curr_expr=pith_curr_expr,
                # Python expression evaluating to this type.
                hint_curr_expr=add_func_scope_type(
                    cls=hint_curr,
                    func_scope=func_wrapper_locals,
                    exception_prefix=_EXCEPTION_PREFIX_FUNC_WRAPPER_LOCAL,
                ),
            )

        # Else, this hint is neither PEP-compliant *NOR* a class. In this case,
        # raise an exception. Note that:
        # * This should *NEVER* happen, as the "typing" module goes to great
        #   lengths to validate the integrity of PEP-compliant types at
        #   declaration time.
        # * The higher-level die_unless_hint_nonpep() validator is
        #   intentionally *NOT* called here, as doing so would permit both:
        #   * PEP-noncompliant forward references, which could admittedly be
        #     disabled by passing "is_str_valid=False" to that call.
        #   * PEP-noncompliant tuple unions, which currently *CANNOT* be
        #     disabled by passing such an option to that call.
        else:
            raise BeartypeDecorHintPepException(
                f'{hint_curr_exception_prefix}type hint {repr(hint_curr)} '
                f'not PEP-compliant.'
            )

        # ................{ CLEANUP                           }................
        # Inject this code into the body of this wrapper.
        func_wrapper_code = replace_str_substrs(
            text=func_wrapper_code,
            old=hint_curr_placeholder,
            new=func_curr_code,
        )

        # Nullify the metadata describing the previously visited hint in this
        # list for safety.
        hints_meta[hints_meta_index_curr] = None

        # Set the following *BEFORE* visiting the next visited hint but *AFTER*
        # performing all other logic for the currently visited hint, implying
        # these should be the last statements of this iteration:
        # * Increment the 0-based index of metadata describing the next visited
        #   hint in the "hints_meta" list.
        # * Label prefixing the representation of the next visited hint.
        hints_meta_index_curr += 1
        hint_curr_exception_prefix = _EXCEPTION_PREFIX_HINT_CHILD

    # ..................{ CLEANUP                           }..................
    # Release the fixed list of all such metadata.
    release_fixed_list(hints_meta)

    # If the Python code snippet to be returned remains unchanged from its
    # initial value, the breadth-first search above failed to generate code. In
    # this case, raise an exception.
    #
    # Note that this test is inexpensive, as the third character of the
    # "func_root_code" code snippet is guaranteed to differ from that of
    # "func_wrapper_code" code snippet if this function behaved as expected,
    # which it should have... but may not have, which is why we're testing.
    if func_wrapper_code == func_root_code:
        raise BeartypeDecorHintPepException(
            f'{_EXCEPTION_PREFIX_HINT_ROOT}{repr(hint_root)} '
            f'not type-checked.'
        )
    # Else, the breadth-first search above successfully generated code.

    # ..................{ CODE ~ locals                     }..................
    # PEP-compliant code snippet passing the value of the random integer
    # previously generated for the current call to the exception-handling
    # function call embedded in the "PEP_CODE_HINT_ROOT_SUFFIX" snippet,
    # defaulting to passing *NO* such integer.
    func_wrapper_code_random_int_if_any = ''

    # If type-checking the root pith requires a pseudo-random integer...
    if is_var_random_int_needed:
        # Pass this integer to the function raising exceptions.
        func_wrapper_code_random_int_if_any = (
            PEP_CODE_HINT_ROOT_SUFFIX_RANDOM_INT)

        # Pass the random.getrandbits() function required to generate this
        # integer to this wrapper function as an optional hidden parameter.
        func_wrapper_locals[_ARG_NAME_GETRANDBITS] = getrandbits

    # ..................{ CODE ~ suffix                     }..................
    # Suffix this code by a Python code snippet raising a human-readable
    # exception when the root pith violates the root type hint.
    func_wrapper_code += PEP_CODE_HINT_ROOT_SUFFIX_format(
        random_int_if_any=func_wrapper_code_random_int_if_any)

    # Return all metadata required by higher-level callers.
    return (
        func_wrapper_code,
        func_wrapper_locals,
        # Tuple of the unqualified classnames referred to by all relative
        # forward references visitable from this hint converted from that set
        # to reduce space consumption after memoization by @callable_cached,
        # defined as either...
        (
            # If *NO* relative forward references are visitable from this root
            # hint, the empty tuple;
            ()
            if hint_forwardrefs_class_basename is None else
            # Else, that set converted into a tuple.
            tuple(hint_forwardrefs_class_basename)
        ),
    )
