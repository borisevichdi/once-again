"""This package provides simple way to call any function reproducibly.

It only works with pure functions, cache only function's output, and
will NOT reproduce all the side-effects, occurring in the function.

Copyright 2018 Dmitrii Borisevich

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

import functools
import os
import pickle
import sys
import time
import types
from typing import *
from hashlib import sha1

# Here we define what are functions and what are methods.
# We do this, because methods (and classmethods) pass "invisible" parameter to function, "self" (and "cls")
# If we just control for function arguments - then in the following code:
# a = A()
# b = A()
# a.f(*args)
# b.f(*args)
# calls a.f and b.f would be indistinguishable.
# Thus, we will check if callable is a free function or bound method, and analyze the bound object in the latter case
function_types = (
    types.FunctionType,  # fits 1. def f(): ..., 2. f = lambda x: ..., 3. @staticmethod, bound and unbound
                         # 4. method non-bound to object (class A(): def b(): pass; A.b (but not A().b !))
    types.BuiltinFunctionType,  # fits builtins such as open
)
method_types = (
    types.MethodType,  # fits 1. methods bound to object (A().b); (a = A(); a.b), 2. @classmethod, bound and unbound
    types.BuiltinMethodType,  # fits builtins methods such as a = [2,3,4], a.index(3)
)


def cache_hash(args):
    """Hashing function, that returns hash for cache given function arguments (including self instance for bound calls).

    Overhead is really good considering use case of slow requests.

    Args:
        args: List of objects to be hashed (for example - args of function or CLI args of script).
            Each object (and sub-objects) should properly implement repr() as _unique_ and _univocal_ representation,
            to guarantee that memory addresses won't be used in repr(), and so caching would work between scripts runs.
            Btw, these are the requirements for the repr() anyways according to python documentation.

    Returns:
        Hash as str of fixed length.
    """
    return sha1(','.join(map(repr, args)).encode("ascii")).hexdigest()[-16:]


def cache_checking_call(f: Callable,
                        args: Union[Tuple, List], kwargs: Dict,
                        invalidation_period: Optional[float], cache_path: str, verbose: bool):
    """This functions tries to a. save execution time, b. make runs reproducible, by caching output of any function.
    It is most useful, if the function calls to the 3rd-party API somewhere on internet or just takes a lot of time.

    This is achieved by storing for each function it's output for defined input parameters to a file, which name is
    defined by the input parameters.
    This function heavily relies on repr(x) returning identical representation of x between code executions,
    for each x in args list. Thus, for example, if one of args is a function or a standard object, then in
    '<function r at 0x006F78A0>' memory address 0x006F78A0 will be different every time, and hashing won't work.
    It's up to you to either provide only objects that follow this rule, or
    to wrap your objects in a proxy class, that will have a proper __repr__.

    Args:
        f: Callable to be called.
        args: List/tuple of positional arguments passed to f, should have __repr__ that stays the same
            for the same content between different runs of code (see docstring above for more info).
        kwargs: Dict of keyword arguments passed to f, should have __repr__ that stays the same
            for the same content between different runs of code (see docstring above for more info).
        invalidation_period: Number of seconds after which cache becomes invalid.
        cache_path: Relative or absolute path to cache dir.
        verbose: Whether to print how caching is going / used.

    Returns:
        f(*args, **kwargs)
    """
    CACHE_VER = "v01"
    # Generate hash-based filename
    h = cache_hash((args, kwargs))
    cache_fname = os.path.join(cache_path, f"{f.__qualname__}.{h}.cache")
    # Cache exists
    if os.path.exists(cache_fname):
        # Cache is valid
        if (invalidation_period is None) or (time.time() - os.path.getmtime(cache_fname) <= invalidation_period):
            if verbose:
                print("  Cache exists for {}, loading it from {}".format(f.__name__, cache_fname), file=sys.stderr)
            with open(cache_fname, 'rb') as cache_f:
                state = pickle.load(cache_f)
            version, args_saved, kwargs_saved, retval = state
            if version == CACHE_VER:
                if repr(args_saved) == repr(args):
                    if repr(kwargs_saved) == repr(kwargs):
                        return retval
            if verbose:
                print("  Cache turned out to be invalid for {}, re-running code".format(f.__name__),
                      file=sys.stderr)
            retval = f(*args, **kwargs)
        # Cache is timed-out
        else:
            if verbose:
                print("  Cache exists for {}, but it became invalid, re-running code".format(f.__name__),
                      file=sys.stderr)
            retval = f(*args, **kwargs)
    # Cache does not exist
    else:
        if verbose:
            print("  No cache exists for {}, running".format(f.__name__), file=sys.stderr)
        retval = f(*args, **kwargs)
    # Storing cache
    with open(cache_fname, 'wb') as cache_f:
        pickle.dump((CACHE_VER, args, kwargs, retval),
                    cache_f)
    return retval


def reproducible_call(cache_path: Optional[str] = "cache", invalidation_period: Optional[float] = None,
                      verbose: Optional[bool] = False):
    # unfortunately, I do not know, what to change in black magic used here,
    # to become compatible with PyCharm inspections, so:
    # noinspection PyUnresolvedReferences
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Some params - can be passed as well
            if not os.path.isdir(cache_path):
                if os.path.exists(cache_path):
                    raise RuntimeError("Cache dir does not exist, but the file with the same name exists instead")
                else:
                    os.mkdir(cache_path)
            # Basic case
            if isinstance(func, function_types):
                value = cache_checking_call(
                    f=func,
                    args=args,
                    invalidation_period=invalidation_period,
                    cache_path=cache_path,
                    verbose=verbose,
                    kwargs=kwargs,
                )
                if verbose:
                    print(f"{func.__qualname__} ({args}, {kwargs})")
            elif isinstance(func, method_types):
                # @classmethod OR instance bound method OR builtin
                # if it was not for built-ins, simpler version could have been used via __func__
                unbound_f = getattr(func.__self__.__class__,
                                    func.__name__)
                unbound_args = [func.__self__, ] + list(args)
                if verbose:
                    print(f"unbounded: {unbound_f.__name__} ({unbound_args}, {kwargs})")
                value = cache_checking_call(
                    f=unbound_f,
                    args=unbound_args,
                    invalidation_period=invalidation_period,
                    cache_path=cache_path,
                    verbose=verbose,
                    kwargs=kwargs,
                )
            else:
                raise AssertionError(
                    "reproducible_call operates only on function or bound methods, {} passed instead".format(
                        type(func)
                    ))

            return value

        return wrapper

    return decorator
