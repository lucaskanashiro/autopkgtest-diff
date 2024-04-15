import json
import os.path
import sqlite3
import sys
import urllib.request
from datetime import datetime

URL_DATABASE = 'https://autopkgtest.ubuntu.com/static/autopkgtest.db'


def get_sqlite_file(autopkgtest_db):
    if(not os.path.isfile(autopkgtest_db)):
        urllib.request.urlretrieve(URL_DATABASE, autopkgtest_db)


def read_input():
    with open('packages', 'r') as input_file:
        pkgs = [pkg.rstrip('\n') for pkg in input_file]
    return pkgs


def connect_db(database_file):
    try:
        con = sqlite3.connect(database_file)
        cursor = con.cursor()
        return cursor
    except sqlite3.Error as error:
        print("Failed to connect to the database.", error)
        if con:
            con.close()
        return None


def query_pkg(pkg, arch, cursor):
    try:
        query = "SELECT distinct(result.run_id), result.exitcode, package, \
            test.arch, result.triggers FROM test, result WHERE package='% s' \
            AND arch='% s' AND release='noble' AND id = result.test_id \
            ORDER BY package;" % (pkg, arch)

        cursor.execute(query)
        data = cursor.fetchall()
        return data
    except sqlite3.Error as error:
        print("Failed to execute the query", error)
        raise Exception("SQL query failed!")


def process_pkg(diff, pkg, arch, reference_datetime, cursor):
    test_runs_before_reference = {}
    test_runs_after_reference = {}

    data = query_pkg(pkg, arch, cursor)

    if(data is None or data == []):
        diff[pkg][arch] = None
        return None

    for test_run in data:
        # id example: 20240329_175621_aafd4@
        split_id = test_run[0].split('_')

        date_string = split_id[0] + split_id[1]
        date_format = "%Y%m%d%H%M%S"

        test_run_datetime = datetime.strptime(date_string, date_format)

        if(test_run_datetime < reference_datetime):
            test_runs_before_reference[test_run_datetime] = test_run
        else:
            test_runs_after_reference[test_run_datetime] = test_run

    if(test_runs_before_reference == {} or test_runs_after_reference == {}):
        diff[pkg][arch] = None
        return None

    latest_run_before_reference = \
        test_runs_before_reference[max(test_runs_before_reference.keys())]
    latest_run_after_reference = \
        test_runs_after_reference[max(test_runs_after_reference.keys())]

    return [latest_run_before_reference, latest_run_after_reference]


def fill_data(data, arch, pkg, diff):
    data[pkg] = {}
    data[pkg][arch] = {}
    data[pkg][arch]['before'] = {}
    data[pkg][arch]['after'] = {}

    data[pkg][arch]['before']['exit_code'] = diff[pkg][arch][0][1]
    data[pkg][arch]['before']['test_run_id'] = diff[pkg][arch][0][0]
    data[pkg][arch]['before']['triggers'] = diff[pkg][arch][0][4]

    data[pkg][arch]['after']['exit_code'] = diff[pkg][arch][1][1]
    data[pkg][arch]['after']['test_run_id'] = diff[pkg][arch][1][0]
    data[pkg][arch]['after']['triggers'] = diff[pkg][arch][1][4]

    return data


def process_diff(diff):
    no_news = {}
    good_news = {}
    bad_news = {}

    for pkg in diff.keys():
        for arch in diff[pkg].keys():
            if(diff[pkg][arch] is not None):
                exit_code_test_run_before_reference = diff[pkg][arch][0][1]
                exit_code_test_run_after_reference = diff[pkg][arch][1][1]

                if(exit_code_test_run_before_reference == 0 and
                        exit_code_test_run_after_reference != 0):
                    bad_news = fill_data(bad_news, arch, pkg, diff)
                elif(exit_code_test_run_before_reference != 0 and
                        exit_code_test_run_after_reference == 0):
                    good_news = fill_data(good_news, arch, pkg, diff)
                else:
                    # both exit codes are non zero or both are zero, so no news
                    no_news = fill_data(no_news, arch, pkg, diff)

    return [no_news, good_news, bad_news]


def output_data(filename, data):
    output = open(filename, 'w')

    formatted_json = json.dumps(data, indent=4)
    output.write(formatted_json)

    output.close()


def main():
    # Get reference date from CLI
    reference_date = sys.argv[1]

    datetime_format = '%Y-%m-%d'
    reference_datetime = datetime.strptime(reference_date, datetime_format)

    autopkgtest_db = 'autopkgtest.db'
    get_sqlite_file(autopkgtest_db)
    pkgs = read_input()

    cursor = connect_db(autopkgtest_db)
    if(cursor is None):
        exit(1)

    diff = {}
    arches = ['amd64', 'arm64', 'ppc64el', 's390x']

    for pkg in pkgs:
        diff[pkg] = {}
        for arch in arches:
            data = process_pkg(diff, pkg, arch, reference_datetime, cursor)

            if(data is None):
                continue

            diff[pkg][arch] = [data[0], data[1]]

    [no_news, good_news, bad_news] = process_diff(diff)

    output_data("no_news_{}.json".format(reference_date), no_news)
    output_data("good_news_{}.json".format(reference_date), good_news)
    output_data("bad_news_{}.json".format(reference_date), bad_news)


if __name__ == "__main__":
    main()
