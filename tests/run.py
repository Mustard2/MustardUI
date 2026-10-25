# Run inside Blender, with the add-on linked as extension user_default/MustardUI, like ctest:
# blender --background --factory-startup --python tests/run.py -- [-R regex] [-E regex] [-j [N]]
import argparse
import ctypes
import json
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
import unittest

import addon_utils
import bpy

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TESTS_DIR)

from helpers import ADDON  # noqa: E402

# Prefix of the result lines the workers print, among the Blender output
RESULT = "MustardUI test result: "
libc = ctypes.CDLL(None)


def discover():
    """Tests by id, in the order they are numbered"""
    tests, stack = {}, [unittest.defaultTestLoader.discover(TESTS_DIR, top_level_dir=TESTS_DIR)]
    while stack:
        item = stack.pop()
        if isinstance(item, unittest.TestSuite):
            stack.extend(reversed(list(item)))
        else:
            tests[item.id()] = item
    return tests


def run(test):
    """Status, time and output of the test, also the one printed by Blender itself"""
    result = unittest.TestResult()
    with tempfile.TemporaryFile("w+") as output:
        sys.stdout.flush()
        sys.stderr.flush()
        libc.fflush(None)
        saved = os.dup(1), os.dup(2)
        os.dup2(output.fileno(), 1)
        os.dup2(output.fileno(), 2)
        start = time.perf_counter()
        try:
            test(result)
        finally:
            elapsed = time.perf_counter() - start
            sys.stdout.flush()
            sys.stderr.flush()
            libc.fflush(None)
            for fd, copy in zip((1, 2), saved, strict=True):
                os.dup2(copy, fd)
                os.close(copy)
        output.seek(0)
        text = output.read()
    errors = result.failures + result.errors
    text += "".join(err for _, err in errors) + "".join(
        f"Skipped: {r}\n" for _, r in result.skipped
    )
    status = "Failed" if errors else "Skipped" if result.skipped else "Passed"
    return {"status": status, "time": elapsed, "output": text}


def worker():
    """Run the test ids read from stdin, printing a result line for each"""
    tests = discover()
    for line in sys.stdin:
        print(RESULT + json.dumps(run(tests[line.strip()])), flush=True)


def parallel(ids, jobs):
    """Results of the tests run by Blender processes, in the order they end"""
    todo, results = queue.Queue(), queue.Queue()
    for test_id in ids:
        todo.put(test_id)
    command = [bpy.app.binary_path, "--background", "--factory-startup", "--quiet"]
    command += ["--python", __file__, "--", "--worker"]

    def drive():
        pipes = {"stdin": subprocess.PIPE, "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT}
        with subprocess.Popen(command, text=True, **pipes) as process:
            while True:
                try:
                    test_id = todo.get_nowait()
                except queue.Empty:
                    break
                process.stdin.write(test_id + "\n")
                process.stdin.flush()
                output = []
                for line in process.stdout:
                    if line.startswith(RESULT):
                        result = json.loads(line[len(RESULT) :])
                        result["output"] = "".join(output) + result["output"]
                        break
                    output.append(line)
                else:
                    # Blender crashed, its other tests left to the other processes
                    output.append(f"Blender exited with code {process.wait()}\n")
                    results.put(
                        (test_id, {"status": "Failed", "time": 0.0, "output": "".join(output)})
                    )
                    return
                results.put((test_id, result))
            process.stdin.close()

    threads = [threading.Thread(target=drive) for _ in range(min(jobs, len(ids)))]
    for thread in threads:
        thread.start()
    while any(t.is_alive() for t in threads) or not results.empty():
        try:
            yield results.get(timeout=0.1)
        except queue.Empty:
            pass


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(
        prog="tests/run_blender.sh BLENDER", description="MustardUI tests"
    )
    parser.add_argument("-R", metavar="REGEX", help="run the tests matching the regex")
    parser.add_argument("-E", metavar="REGEX", help="exclude the tests matching the regex")
    parser.add_argument(
        "-j",
        metavar="N",
        type=int,
        nargs="?",
        const=os.cpu_count(),
        default=1,
        help="run N tests in parallel, as many as the CPUs without N",
    )
    parser.add_argument("-N", action="store_true", help="list the tests without running them")
    parser.add_argument("-V", action="store_true", help="print the output of all the tests")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if addon_utils.enable(ADDON, default_set=True, handle_error=None) is None:
        raise RuntimeError(f"Could not enable {ADDON}")
    if args.worker:
        return worker()

    tests = discover()
    numbers = {test_id: n for n, test_id in enumerate(tests, 1)}
    ids = [
        x
        for x in tests
        if (not args.R or re.search(args.R, x)) and not (args.E and re.search(args.E, x))
    ]
    if args.N:
        for test_id in ids:
            print(f"  Test #{numbers[test_id]}: {test_id}")
        print(f"\nTotal Tests: {len(ids)}")
        return

    # After the Blender banner, buffered when piped
    libc.fflush(None)
    print(f"Test project {os.path.dirname(TESTS_DIR)}")
    start = time.perf_counter()
    results = parallel(ids, args.j) if args.j > 1 else ((x, run(tests[x])) for x in ids)
    width = max(map(len, ids), default=0) + 3
    statuses = {}
    for count, (test_id, result) in enumerate(results, 1):
        statuses[test_id] = status = result["status"]
        n = numbers[test_id]
        print(
            f"{count:>{len(str(len(ids)))}}/{len(ids)} Test {f'#{n}':>{len(str(len(tests))) + 1}}: "
            f"{test_id} {'.' * (width - len(test_id))} "
            f"{'   ' if status == 'Passed' else '***'}{status:<8}{result['time']:7.2f} sec",
            flush=True,
        )
        if result["output"] and (status == "Failed" or args.V):
            print(result["output"].rstrip("\n"), flush=True)

    failed = sorted(
        (x for x in ids if statuses.get(x, "Not Run") in ("Failed", "Not Run")), key=numbers.get
    )
    print(
        f"\n{100 * (len(ids) - len(failed)) // max(len(ids), 1)}% tests passed, "
        f"{len(failed)} tests failed out of {len(ids)}"
    )
    print(f"\nTotal Test time (real) = {time.perf_counter() - start:7.2f} sec")
    for title, names in (
        ("did not run", [x for x in ids if statuses.get(x) == "Skipped"]),
        ("FAILED", failed),
    ):
        if names:
            print(f"\nThe following tests {title}:")
            for test_id in names:
                print(f"\t{numbers[test_id]:>4} - {test_id} ({statuses.get(test_id, 'Not Run')})")

    if not ids or failed:
        raise SystemExit(1)


main()
