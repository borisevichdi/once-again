# Reproducible

## Quick start
```python
import time
from once_again import reproducible_call

@reproducible_call
def plus(a, b):
    time.sleep(5)
    print("Boo-ya!")
    return a + b

>>> a = plus(3, 2)  # takes 5 seconds
Boo-ya!
>>> print(a)  # result is calculated
5
>>> b = plus(3, 2)  # function is not executed:
                    # call takes 0 seconds,
                    # nothing is printed
>>> print(b)  # result is taken from the cache
5
```

### Intended benefits
1. You can save time while re-running the same code on the same data.
2. You will be able to re-run the code two years later, when the reviewer of your paper will ask for corrections, and you will still get the very same results (even if an online server you used does not exist anymore).

Now, how cool is that? =)

## Table of Contents
1. [Detailed description](#detailed-description)
    * [Overview](#overview)
    * [When to use it](#when-should-I-use-the-decorator)
    * [When it can be used](#what-can-the-decorator-be-applied-to)
    * [When it can not be used](#what-can-the-decorator-not-be-applied-to)
2. [Arguments](#arguments)
3. [Caveats](#caveats)
    * [Classes](#classes)
    * [Functions](#function-identity)
4. [FAQ](#faq)

## Detailed description

### Overview
To make your function call reproducible, add @reproducible_call as decorator.
This will create [@functools.lru_cache](https://docs.python.org/dev/library/functools.html#functools.lru_cache)-like cache, that will automatically check arguments, passed to the function.
If the function will be called with the same arguments, this case will be recognized, and the code won't be executed, the cached result will be returned immediately instead.

The **main improvement** over \@functools.lru_cache, is that this package creates cache on _disk_, and thus it will persist _between runtimes_. This mean, that you can re-run your code comletely, and time will be saved.

Keep in mind, that the cached function won't be executed, thus _any side-effects_ of the function won't be made as well (see `time.sleep` and `print` in the [quick start](#quick-start) as example).

### When should I use the decorator
Prioritize to apply this decorator to functions, which:
1. Perform _loooong_ calculations (self, or calling 3rd-party tool), or
2. Do requests over the internet.

Keep in mind, that cache is disk-based, and therefore faster than internet or big calculations, but is still quite slow. 
So, it is NOT recommended to be applied to short calculations, unless you want reproducibilty _for the cost_ of time.

### What can the decorator be applied to
Stand-alone functions, objects/classes/static methods:
```python
@reproducible_call
def plus(a, b):
    return a + b

class A(object):
    v = 0
    def __repr__(self):
        return f"A({self.v})"
    
    @reproducible_call
    def method(self):
        return self.v
    
    @classmethod
    @reproducible_call
    def cls_method(cls):
        return cls.__name__
    
    @staticmethod
    @reproducible_call
    def static_method():
        return [1, 2, 3]
```

### What can the decorator NOT be applied to

lambdas and nested functions.

## Arguments

By default, application of @reproducible_call decorator will store files in subfolder with a name "cache", and cache will be considered valid infinitely.

To change the behaviour, you can provide following arguments to the decorator:

```python
def reproducible_call(
    _cache_path: Optional[str] = "cache", 
    _invalidation_period: Optional[float] = None,
    _verbose: Optional[bool] = False
):
```
For example,
```python
@reproducible_call(_cache_path="better_dir",
                   _invalidation_period=60 * 60 * 24 * 30,
                   _verbose=True)
def plus(a, b):
    return a + b
```

* _cache_path: Absolute or relative path to a folder, where cache will be stored.
  * "cache" by default, will be created if does not exist.
* _invalidation_period: Time in seconds, for how long the existing cache is considered valid, before the function will be retried. This is particularly useful for requests over the internet, for which you'd like to save the time, but also update the cache from time to time.
  * Note, that this is checked during the runtime, and not stored in a cache file.
  * If not provided, then available cache with any timestamp is considered valid. 
* _verbose: Whether to print noisy debug information.
  * False by default.

## Caveats

### Classes

Be aware, that by default in CPython, custom objects have __repr__  method, which returns a string like `<__main__.A at 0x6f6ce70>`, where the "0x6f6ce70" is the memory address.
The current implementation of the package will not be able to recognize that this object is the same.

To solve the problem, provide a proper __repr__ method to your class, that will be the same for identical objects, and different for different.
For example, this will work just fine:
```python
class A(object):
    v = 0
    stuff = "text"
    
    def __repr__(self):
        # to comply with @reproducible_call, __repr__
        # provides both the unique name of the class 
        # and all the variables attached
        return f"A(v={self.v}, stuff={self.stuff})"
```

### Function identity

The code intentionally only check function name, and does _not_ check, what is the code of the decorated function.
Thus, it will use the same cache file for two functions with the same name with the same arguments, but different code.

This means, among other things, that:
* Two identically named functions in different modules will check the same cache.
* Any changes made in the decorated function code won't be checked, and old cache will be used.

This is because I've found the decorator mostly useful during initial protyping phase of development, when one might need to re-run code quite often.
In that phase, it is very common to make refactoring, that will change code appearance, but won't change its functionality.
Since proving algorithmic identity of functions is way out of the scope of this project, I've decided to ignore code changes.

**Shortly: This means that if you changed the code of decorated function "fname", you MUST invalidate cache manually, by removing all "cache/fname.\*" files**

## FAQ

* My decorated code does not save any time and ignore existing cache!
  * You are probably using _custom classes_, which do not have proper \_\_repr\_\_. Read more [here](#classes).
  * Other possibility is that you pass _a collection_, like dict or set or list, as an argument, and _order of the elements_ is not controlled between runs. Use `sorted()` to guarantee order (if your function does not rely on element order, of course), or consider applying decorator to the downstream or upstream function.

* I changed my code, but the decorator keeps using cache!
  * Yes, this is [intentional](#function-identity). Remove "cache/{fname}.\*" files manually, if you really want to delete old cache.

* I want to apply the decorator to function `cool_function()`, that comes from a 3rd-party package, how do I do it?
  * Write an almost 1-liner proxy:
  ```python
  @reproducible_call
  def proxy_cool_function(*args, **kwargs):
      return cool_function(*args, **kwargs)
  ```

* The code should have created a file / printed text / made a request / run a bash command, but it didn't!
  * Yes, because all these actions are _side-effects_, and the whole idea of the package is to skip (time-wasting) side-effects.
  * On this note, you should write more [pure functions](https://en.wikipedia.org/wiki/Pure_function) if you really want to decorate them, instead of doing everything in one sole function - this is _always a great idea_, even if you are not going to use this package.

* I want to decorate a nested function or lambda, but it fails, complaining about filename.
  * Unfortunately, this will happen. Feel free to make a PR to fix it.
