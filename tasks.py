import os

from multiprocessing import cpu_count
from os.path import join, dirname, realpath, exists
from shutil import rmtree
from subprocess import run
from copy import copy

from invoke import task


PROJ_ROOT = dirname(realpath(__file__))
THIRD_PARTY_DIR = join(PROJ_ROOT, "third-party")
SYSROOT = "/usr/local/faasm/llvm-sysroot"
SYSROOT_LIBS = join(SYSROOT, "lib", "wasm32-wasi")
HEADERS_DIRS = [join(SYSROOT, "include", "clapack")]

INSTALLED_LIBS = [
    "libcblas",
    "libf2c",
    "libblas",
    "liblapack",
]

N_CPUS = int(cpu_count()) - 1


@task
def uninstall(ctx):
    """
    Removes all installed files
    """
    for headers_dir in HEADERS_DIRS:
        if exists(headers_dir):
            print("Removing headers {}".format(headers_dir))
            rmtree(headers_dir)

    for lib_name in INSTALLED_LIBS:
        static_path = join(SYSROOT_LIBS, "{}.a".format(lib_name))
        shared_path = join(SYSROOT_LIBS, "{}.so".format(lib_name))

        if exists(static_path):
            print("Removing static lib {}".format(static_path))
            os.remove(static_path)

        if exists(shared_path):
            print("Removing shared lib {}".format(shared_path))
            os.remove(shared_path)


@task
def lapacke(ctx, clean=False):
    """
    Builds the LAPACKE interface from LAPACK
    """
    lapacke_dir = join(THIRD_PARTY_DIR, "lapack", "LAPACKE")

    if clean:
        run("make clean", cwd=lapacke_dir, shell=True, check=True)

    run("make -j {}".format(N_CPUS), shell=True, cwd=lapacke_dir, check=True)
    run("make install", shell=True, cwd=lapacke_dir, check=True)


@task
def clapack(ctx, clean=False, shared=False):
    """
    Builds CBLAS, CLAPACK, F2C etc.
    """
    clapack_dir = join(THIRD_PARTY_DIR, "clapack")

    # Build clapack
    if clean:
        run("make clean", cwd=clapack_dir, shell=True, check=True)

    # Set up environment to specify whether we're building static or shared
    env = copy(os.environ)
    env.update({"LIBEXT": ".so" if shared else ".a"})

    # Make libf2c first (needed by others)
    run(
        "make f2clib -j {}".format(N_CPUS),
        shell=True,
        cwd=clapack_dir,
        check=True,
        env=env,
    )

    # Make the rest of CLAPACK
    run(
        "make -j {}".format(N_CPUS),
        shell=True,
        cwd=clapack_dir,
        check=True,
        env=env,
    )
    run("make install", shell=True, cwd=clapack_dir, check=True)
