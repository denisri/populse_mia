import os

os.chdir(os.path.dirname(os.path.realpath(__file__)))

from src.modules.Database.Database import Database

def test_database_creation():
    pass
    # raise Exception("test")

total_tests = 0
failed_tests = []

try:
    total_tests += 1
    test_database_creation()
except Exception:
    failed_tests.append("database_creation")

if len(failed_tests) > 0:
    errorMessage = "Some tests failed.\n"
    errorMessage += str(len(failed_tests)) + "/" + str(total_tests)  + " tests failed.\n"
    errorMessage += "Here is a list of the tests that failed:\n"
    for failed in failed_tests:
        errorMessage += "\t" + failed + "\n"
    raise Exception(errorMessage)