import os
import shutil
import time
import unittest
from .reproducible_call import reproducible_call

CACHE_DIR = "test"
VERBOSE = False


@reproducible_call(cache_path=CACHE_DIR, verbose=VERBOSE)
def f(a, b, *, c, d=0):
    return a * b + c * d


def g(a, b, *, c, d=0):
    return a * b + c * d


@reproducible_call(cache_path=CACHE_DIR, verbose=VERBOSE)
def magic(*args, **kwargs):
    return g(*args, **kwargs)


@reproducible_call(cache_path=CACHE_DIR, verbose=VERBOSE)
def h(a, f):
    return a + f


class A(object):
    value = 0

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"A({self.value})"

    def f(self):
        return self.value


class Dataset(object):
    value = None

    def __init__(self, v: list):
        self.value = v

    def __repr__(self):
        return f"Dataset({self.value})"

    @reproducible_call(cache_path=CACHE_DIR, verbose=VERBOSE)
    def sumsq(self):
        return sum(x ** 2 for x in self.value)

    @classmethod
    @reproducible_call(cache_path=CACHE_DIR, verbose=VERBOSE)
    def whoami(cls):
        return cls.__name__

    @staticmethod
    @reproducible_call(cache_path=CACHE_DIR, verbose=VERBOSE)
    def increment(arr):
        return [x+1 for x in arr]


class OtherDataset(object):
    value = None

    def __init__(self, v: list):
        self.value = v

    def __repr__(self):
        return f"OtherDataset({self.value})"

    @reproducible_call(cache_path=CACHE_DIR, verbose=VERBOSE)
    def sumsq(self):
        return sum(x ** 2 for x in self.value)

    @classmethod
    @reproducible_call(cache_path=CACHE_DIR, verbose=VERBOSE)
    def whoami(cls):
        return cls.__name__

    @staticmethod
    @reproducible_call(cache_path=CACHE_DIR, verbose=VERBOSE)
    def increment(arr):
        return [x+1 for x in arr]


ds = Dataset([1, 2, 3])
dsx = Dataset([1, 2, 3, 4])
ds2 = OtherDataset([1, 2, 3])


class Tests(unittest.TestCase):
    files_countrer = 0
    cache_dir = CACHE_DIR

    @classmethod
    def setUpClass(cls):
        if os.path.isdir(cls.cache_dir):
            shutil.rmtree(cls.cache_dir)
        cls.files_countrer = 0

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.cache_dir)
        cls.files_countrer = 0

    def check_that_new_file_created(self, _filename, _expected_output, _func, *args, **kwargs):
        if self.__class__.files_countrer == 0:
            self.assertFalse(os.path.isdir(self.cache_dir))
        else:
            self.assertEqual(len(os.listdir(self.cache_dir)), self.__class__.files_countrer)
        self.assertFalse(os.path.isfile(os.path.join(self.cache_dir, _filename)))

        self.assertEqual(_func(*args, **kwargs), _expected_output)

        self.__class__.files_countrer += 1
        self.assertEqual(len(os.listdir(self.cache_dir)), self.__class__.files_countrer)
        self.assertTrue(os.path.isfile(os.path.join(self.cache_dir, _filename)))

    def check_that_cache_exists_and_used(self, _filename, _expected_output, _func, *args, **kwargs):
        self.assertEqual(len(os.listdir(self.cache_dir)), self.__class__.files_countrer)
        self.assertTrue(os.path.isfile(os.path.join(self.cache_dir, _filename)))
        timestamp = os.path.getmtime(os.path.join(self.cache_dir, _filename))
        time.sleep(0.1)

        self.assertEqual(_func(*args, **kwargs), _expected_output)

        self.assertEqual(len(os.listdir(self.cache_dir)), self.__class__.files_countrer)
        self.assertEqual(timestamp, os.path.getmtime(os.path.join(self.cache_dir, _filename)))

    def test_00_f_and_dir_creation(self):
        self.check_that_new_file_created(
            "f.5270d670cd06f7c9.cache", 320,
            f, 10, 20, c=30, d=4
        )
        self.check_that_cache_exists_and_used(
            "f.5270d670cd06f7c9.cache", 320,
            f, 10, 20, c=30, d=4
        )

    def test_01_apply_in_place_is_identical_for_same_function_but_different_for_bound_method_with_same_name(self):
        self.check_that_cache_exists_and_used(
            "f.5270d670cd06f7c9.cache", 320,
            reproducible_call(cache_path=self.cache_dir, verbose=VERBOSE)(f), 10, 20, c=30, d=4
        )
        # this is the only use-case for the "elif isinstance(func, method_types)" branch of reproducible_call
        self.check_that_new_file_created(
            "A.f.4fd7f59c656bdfa6.cache", 10,
            reproducible_call(cache_path=self.cache_dir, verbose=VERBOSE)(A(10).f)
        )

    def test_02_obj_method(self):
        self.check_that_new_file_created(
            "Dataset.sumsq.fcf435f879c1a7fc.cache", 14,
            ds.sumsq
        )
        self.check_that_cache_exists_and_used(
            "Dataset.sumsq.fcf435f879c1a7fc.cache", 14,
            ds.sumsq
        )

    def test_03_method_of_other_class(self):
        self.check_that_new_file_created(
            "OtherDataset.sumsq.8086bc0bfcd89cf5.cache", 14,
            ds2.sumsq
        )
        self.check_that_cache_exists_and_used(
            "OtherDataset.sumsq.8086bc0bfcd89cf5.cache", 14,
            ds2.sumsq
        )

    def test_04_method_of_other_obj_same_class(self):
        self.check_that_new_file_created(
            "Dataset.sumsq.4aa22ffd185fd537.cache", 30,
            dsx.sumsq
        )
        self.check_that_cache_exists_and_used(
            "Dataset.sumsq.4aa22ffd185fd537.cache", 30,
            dsx.sumsq
        )

    def test_05_class_method(self):
        self.check_that_new_file_created(
            "Dataset.whoami.986ed718b5c6828f.cache", "Dataset",
            ds.whoami
        )
        self.check_that_cache_exists_and_used(
            "Dataset.whoami.986ed718b5c6828f.cache", "Dataset",
            ds.whoami
        )

    def test_06_other_class_method(self):
        self.check_that_new_file_created(
            "OtherDataset.whoami.b3466e35ef31906a.cache", "OtherDataset",
            ds2.whoami
        )
        self.check_that_cache_exists_and_used(
            "OtherDataset.whoami.b3466e35ef31906a.cache", "OtherDataset",
            ds2.whoami
        )

    def test_07_static_method(self):
        self.check_that_new_file_created(
            "Dataset.increment.56a4daefe1dca449.cache", [2, 3, 4],
            ds.increment, [1, 2, 3]
        )
        self.check_that_cache_exists_and_used(
            "Dataset.increment.56a4daefe1dca449.cache", [2, 3, 4],
            ds.increment, [1, 2, 3]
        )
        # ds is object of Dataset class
        self.check_that_cache_exists_and_used(
            "Dataset.increment.56a4daefe1dca449.cache", [2, 3, 4],
            Dataset.increment, [1, 2, 3]
        )
        # ds2 is object of OtherDataset class
        self.check_that_new_file_created(
            "OtherDataset.increment.56a4daefe1dca449.cache", [2, 3, 4],
            ds2.increment, [1, 2, 3]
        )
        self.check_that_cache_exists_and_used(
            "OtherDataset.increment.56a4daefe1dca449.cache", [2, 3, 4],
            OtherDataset.increment, [1, 2, 3]
        )

    def test_08_invalidation_time(self):
        filename = "g.5270d670cd06f7c9.cache"
        self.assertEqual(len(os.listdir(self.cache_dir)), self.__class__.files_countrer)

        self.check_that_new_file_created(
            filename, 320,
            reproducible_call(cache_path=CACHE_DIR, verbose=VERBOSE)(g), 10, 20, c=30, d=4
        )

        self.check_that_cache_exists_and_used(
            filename, 320,
            reproducible_call(cache_path=CACHE_DIR, verbose=VERBOSE, invalidation_period=100)(g), 10, 20, c=30, d=4
        )

        timestamp = os.path.getmtime(os.path.join(self.cache_dir, filename))
        time.sleep(1)

        self.assertEqual(
            reproducible_call(cache_path=CACHE_DIR, verbose=VERBOSE, invalidation_period=0.01)(g)(10, 20, c=30, d=4),
            320
        )

        self.assertEqual(len(os.listdir(self.cache_dir)), self.__class__.files_countrer)
        self.assertNotEqual(timestamp, os.path.getmtime(os.path.join(self.cache_dir, filename)))

    def test_09_tricky_arguments(self):
        self.check_that_new_file_created(
            "h.711bf730a2bdfec2.cache", 10,
            h, a=5, f=5
        )
        self.check_that_cache_exists_and_used(
            "h.711bf730a2bdfec2.cache", 10,
            h, a=5, f=5
        )

    def test_10_3rd_party_function(self):
        self.check_that_new_file_created(
            "magic.6de8bf082022edab.cache", 10,
            magic, 1, 10, c=0, d=0
        )
        self.check_that_cache_exists_and_used(
            "magic.6de8bf082022edab.cache", 10,
            magic, 1, 10, c=0, d=0
        )
