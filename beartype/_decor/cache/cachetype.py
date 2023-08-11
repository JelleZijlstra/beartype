#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright (c) 2014-2023 Beartype authors.
# See "LICENSE" for further details.

'''
**Beartypistry** (i.e., singleton dictionary mapping from the fully-qualified
classnames of all type hints annotating callables decorated by the
:func:`beartype.beartype` decorator to those types).

This private submodule is *not* intended for importation by downstream callers.
'''

# ....................{ TODO                               }....................
#FIXME: Consider obsoleting this submodule entirely in favour of the more
#general-purpose and significantly more powerful "cachescope" submodule, please.

# ....................{ IMPORTS                            }....................
from beartype.roar import (
    BeartypeCallHintForwardRefException,
    BeartypeDecorHintForwardRefException,
)
from beartype.roar._roarexc import _BeartypeDecorBeartypistryException
from beartype._check.checkmagic import ARG_NAME_TYPISTRY
from beartype._util.cache.utilcachecall import callable_cached
from beartype._util.cls.pep.utilpep3119 import die_unless_type_isinstanceable
from beartype._util.cls.utilclstest import is_type_builtin
from beartype._util.module.utilmodimport import import_module_attr
from beartype._util.module.utilmodtest import die_unless_module_attr_name
from beartype._util.utilobject import get_object_type_name

# ....................{ CONSTANTS                          }....................
TYPISTRY_HINT_NAME_TUPLE_PREFIX = '+'
'''
**Beartypistry tuple key prefix** (i.e., substring prefixing the keys of all
beartypistry key-value pairs whose values are tuples).

Since fully-qualified classnames are guaranteed *not* to be prefixed by this
prefix, this prefix suffices to uniquely distinguish key-value pairs whose
values are types from pairs whose values are tuples.
'''

# ....................{ REGISTRARS ~ forwardref            }....................
#FIXME: Unit test us up.
# Note this function intentionally does *NOT* accept an optional "hint_labal"
# parameter as doing so would conflict with memoization.
@callable_cached
def register_typistry_forwardref(hint_classname: str) -> str:
    '''
    Register the passed **fully-qualified forward reference** (i.e., string
    whose value is the fully-qualified name of a user-defined class that
    typically has yet to be defined) with the beartypistry singleton *and*
    return a Python expression evaluating to this class when accessed via the
    private ``__beartypistry`` parameter implicitly passed to all wrapper
    functions generated by the :func:`beartype.beartype` decorator.

    This function is memoized for both efficiency *and* safety, preventing
    accidental reregistration.

    Parameters
    ----------
    hint_classname : object
        Forward reference to be registered, defined as either:

        * A string whose value is the syntactically valid name of a class.
        * An instance of the :class:`typing.ForwardRef` class.

    Returns
    ----------
    str
        Python expression evaluating to the user-defined referred to by this
        forward reference when accessed via the private ``__beartypistry``
        parameter implicitly passed to all wrapper functions generated by the
        :func:`beartype.beartype` decorator.

    Raises
    ----------
    BeartypeDecorHintForwardRefException
        If this forward reference is *not* a syntactically valid
        fully-qualified classname.
    '''

    # If this object is *NOT* the syntactically valid fully-qualified name of a
    # module attribute which may *NOT* actually exist, raise an exception.
    die_unless_module_attr_name(
        module_attr_name=hint_classname,
        exception_cls=BeartypeDecorHintForwardRefException,
        exception_prefix='Forward reference ',
    )

    # Return a Python expression evaluating to this type *WITHOUT* explicitly
    # registering this forward reference with the beartypistry singleton. Why?
    # Because the Beartypistry.__missing__() dunder method implicitly handles
    # forward references by dynamically registering types on their first access
    # if *NOT* already registered. Ergo, our job is actually done here.
    return (
        f'{_CODE_TYPISTRY_HINT_NAME_TO_HINT_PREFIX}{repr(hint_classname)}'
        f'{_CODE_TYPISTRY_HINT_NAME_TO_HINT_SUFFIX}'
    )

# ....................{ SUBCLASSES                         }....................
class Beartypistry(dict):
    '''
    **Beartypistry** (i.e., singleton dictionary mapping from strings uniquely
    identifying PEP-noncompliant type hints annotating callables decorated
    by the :func:`beartype.beartype` decorator to those hints).

    This dictionary implements a global registry for **PEP-noncompliant type
    hints** (i.e., :mod:`beartype`-specific annotation *not* compliant with
    annotation-centric PEPs), including:

    * Non-:mod:`typing` types (i.e., classes *not* defined by the :mod:`typing`
      module, which are PEP-compliant type hints that fail to comply with
      standard type semantics and are thus beyond the limited scope of this
      PEP-noncompliant-specific dictionary).
    * Tuples of non-:mod:`typing` types, commonly referred to as **tuple
      unions** in :mod:`beartype` jargon.

    This dictionary efficiently shares these hints across all type-checking
    wrapper functions generated by this decorator, enabling these functions to:

    * Obtain type and tuple objects at wrapper runtime given only the strings
      uniquely identifying those objects hard-coded into the bodies of those
      wrappers at decoration time.
    * Resolve **forward references** (i.e., type hints whose values are strings
      uniquely identifying type and tuple objects) at wrapper runtime, which
      this dictionary supports by defining a :meth:`__missing__` dunder method
      dynamically adding a new mapping from each such reference to the
      corresponding object on the first attempt to access that reference.
    '''

    # ..................{ DUNDERS                            }..................
    def __setitem__(self, hint_name: str, hint: object) -> None:
        '''
        Dunder method explicitly called by the superclass on setting the passed
        key-value pair with ``[``- and ``]``-delimited syntax, mapping the
        passed string uniquely identifying the passed PEP-noncompliant type
        hint to that hint.

        Parameters
        ----------
        hint_name: str
            String uniquely identifying this hint in a manner dependent on the
            type of this hint. Specifically, if this hint is:

            * A non-:mod:`typing` type, this is the fully-qualified classname of
              the module attribute defining this type.
            * A tuple of non-:mod:`typing` types, this is a string:

              * Prefixed by the :data:`TYPISTRY_HINT_NAME_TUPLE_PREFIX`
                substring distinguishing this string from fully-qualified
                classnames.
              * Hash of these types (ignoring duplicate types and type order in
                this tuple).
        hint : object
            PEP-noncompliant type hint to be mapped from this string.

        Raises
        ----------
        TypeError
            If this hint is **unhashable** (i.e., *not* hashable by the builtin
            :func:`hash` function and thus unusable in hash-based containers
            like dictionaries and sets). Since *all* supported PEP-noncompliant
            type hints are hashable, this exception should *never* be raised.
        _BeartypeDecorBeartypistryException
            If either:

            * This name either:

              * *Not* a string.
              * Is an existing string key of this dictionary, implying this
                name has already been registered, implying a key collision
                between the type or tuple already registered under this key and
                this passed type or tuple to be reregistered under this key.
                Since the high-level :func:`register_typistry_type` and
                :func:`register_typistry_tuple` functions implicitly calling
                this low-level dunder method are memoized *and* since the
                latter function explicitly avoids key collisions by detecting
                and uniquifying colliding keys, every call to this method
                should be passed a unique key.

            * This hint is either:

              * A type but either:

                * This name is *not* the fully-qualified classname of this
                  type.
                * This type is **PEP-compliant** (most of which violate
                  standard type semantics and thus require PEP-specific
                  handling), including either:

                  * A class defined by the :mod:`typing` module.
                  * A subclass of such a class.
                  * A generic alias.

              * A tuple but either:

                * This name is *not* prefixed by the magic substring
                  :data:`TYPISTRY_HINT_NAME_TUPLE_PREFIX`.
                * This tuple contains one or more items that are either:

                  * *Not* types.
                  * PEP-compliant types.
        '''

        # If this name is *NOT* a string, raise an exception.
        if not isinstance(hint_name, str):
            raise _BeartypeDecorBeartypistryException(
                f'Beartypistry key {repr(hint_name)} not string.')
        # Else, this name is a string.
        #
        # If this name is an existing key of this dictionary, this name has
        # already been registered, implying a key collision between the type or
        # tuple already registered under this key and the passed type or
        # tuple to be reregistered under this key. In this case, raise an
        # exception.
        elif hint_name in self:
            raise _BeartypeDecorBeartypistryException(
                f'Beartypistry key "{hint_name}" already registered '
                f'(i.e., key collision between '
                f'prior registered value {repr(self[hint_name])} and '
                f'newly registered value {repr(hint)}).'
            )
        # Else, this name is *NOT* an existing key of this dictionary.
        #
        # If this hint is a class...
        #
        # Note that although *MOST* classes are PEP-noncompliant (e.g., the
        # builtin "str" type), some classes are PEP-compliant (e.g., the
        # stdlib "typing.SupportsInt" protocol). Since both PEP-noncompliant
        # and -compliant classes are shallowly type-checkable via the
        # isinnstance() builtin, there exists no demonstrable benefit to
        # distinguishing between either here.
        elif isinstance(hint, type):
            # Fully-qualified classname of this type as declared by this type.
            hint_clsname = get_object_type_name(hint)

            # If...
            if (
                # The passed name is not this classname *AND*...
                hint_name != hint_clsname and
                # This type is *NOT* builtin (and thus requires importation
                # into the body of the current wrapper function)...
                #
                # Note that builtin types are registered under their
                # unqualified basenames (e.g., "list" rather than
                # "builtins.list") for runtime efficiency, a core optimization
                # requiring manual whitelisting here.
                not is_type_builtin(hint)
            # Then raise an exception.
            ):
                raise _BeartypeDecorBeartypistryException(
                    f'Beartypistry key "{hint_name}" not '
                    f'fully-qualified classname "{hint_clsname}" of '
                    f'type {hint}.'
                )
        # Else, this hint is *NOT* a class.
        #
        # If this hint is a tuple...
        elif isinstance(hint, tuple):
            # If this tuple's name is *NOT* prefixed by a magic substring
            # uniquely identifying this hint as a tuple, raise an exception.
            #
            # Ideally, this block would strictly validate this name to be the
            # concatenation of this prefix followed by this tuple's hash.
            # Sadly, Python fails to cache tuple hashes (for largely spurious
            # reasons, like usual):
            #     https://bugs.python.org/issue9685
            #
            # Potentially introducing a performance bottleneck for mostly
            # redundant validation is a bad premise, given that we mostly
            # trust callers to call the higher-level
            # :func:`register_typistry_tuple` function instead, which already
            # guarantees this constraint to be the case.
            if not hint_name.startswith(TYPISTRY_HINT_NAME_TUPLE_PREFIX):
                raise _BeartypeDecorBeartypistryException(
                    f'Beartypistry key "{hint_name}" not '
                    f'prefixed by "{TYPISTRY_HINT_NAME_TUPLE_PREFIX}" for '
                    f'tuple {repr(hint)}.'
                )
        # Else, this hint is neither a class nor a tuple. In this case,
        # something has gone terribly awry. Pour out an exception.
        else:
            raise _BeartypeDecorBeartypistryException(
                f'Beartypistry key "{hint_name}" value {repr(hint)} invalid '
                f'(i.e., neither type nor tuple).'
            )

        # Cache this object under this name.
        super().__setitem__(hint_name, hint)


    def __missing__(self, hint_classname: str) -> type:
        '''
        Dunder method explicitly called by the superclass
        :meth:`dict.__getitem__` method implicitly called on caller attempts to
        access the passed missing key with ``[``- and ``]``-delimited syntax.

        This method treats this attempt to get this missing key as the
        intentional resolution of a forward reference whose fully-qualified
        classname is this key.

        Parameters
        ----------
        hint_classname : str
            **Name** (i.e., fully-qualified name of the user-defined class) of
            this hint to be resolved as a forward reference.

        Returns
        ----------
        type
            User-defined class whose fully-qualified name is this missing key.

        Raises
        ----------
        BeartypeCallHintForwardRefException
            If either:

            * This name is *not* a syntactically valid fully-qualified
              classname.
            * *No* module prefixed this name exists.
            * An importable module prefixed by this name exists *but* this
              module declares no attribute by this name.
            * The module attribute to which this name refers is *not* an
              isinstanceable class.
        '''

        # Module attribute whose fully-qualified name is this forward
        # reference, dynamically imported at callable call time.
        hint_class: type = import_module_attr(
            module_attr_name=hint_classname,
            exception_cls=BeartypeCallHintForwardRefException,
            exception_prefix='Forward reference ',
        )

        # If this attribute is *NOT* an isinstanceable class, raise an
        # exception.
        die_unless_type_isinstanceable(
            cls=hint_class,
            exception_cls=BeartypeCallHintForwardRefException,
            exception_prefix=f'Forward reference "{hint_classname}" referent ',
        )
        # Else, this hint is an isinstanceable class.

        # Return this class. The superclass dict.__getitem__() dunder method
        # then implicitly maps the passed missing key to this class by
        # effectively assigning this name to this class: e.g.,
        #     self[hint_classname] = hint_class
        return hint_class  # type: ignore[return-value]

# ....................{ SINGLETONS                         }....................
bear_typistry = Beartypistry()
'''
**Beartypistry** (i.e., singleton dictionary mapping from the fully-qualified
classnames of all type hints annotating callables decorated by the
:func:`beartype.beartype` decorator to those types).**

See Also
----------
:class:`Beartypistry`
    Further details.
'''

# ....................{ PRIVATE ~ constants                }....................
_CODE_TYPISTRY_HINT_NAME_TO_HINT_PREFIX = f'{ARG_NAME_TYPISTRY}['
'''
Substring prefixing a Python expression mapping from the subsequent string to
an arbitrary object cached by the beartypistry singleton via the private
beartypistry parameter.
'''


_CODE_TYPISTRY_HINT_NAME_TO_HINT_SUFFIX = ']'
'''
Substring prefixing a Python expression mapping from the subsequent string to
an arbitrary object cached by the beartypistry singleton via the private
beartypistry parameter.
'''