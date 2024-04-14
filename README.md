# Compare autopkgtest results

This script compares the autopkgtest results until a given date and the latest
run for a set of packages. Once can run the script with the command below:

```
$ python3 diff_autopkgtest_results.py 2024-02-28
```

A file named `packages` must exist with a list of packages to be analyzed. 

The reference date passed to the script must follow this format: `YYYY-MM-DD`.

As result, 3 files containing the output of the analysis:

* `no_news_YYYY-MM-DD.json`: packages that did not change the status. The package was
  passing before the reference date and now it keeps passing. Or the package
  was failing and now it keeps failing.
* `good_news_YYYY-MM-DD.json`: packages that tests were failing before the reference date
  and now they are passing.
* `bad_news_YYYY-MM-DD.json`: packages that tests were passing before the reference date
  and now they are failing.

Some packages might not have data to be analyzed, maybe there is no data in the
SQLite database file, or no test run before or after the reference date.
