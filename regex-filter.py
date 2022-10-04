#!/usr/bin/env python3

import os
import sys
import json
import shutil
import re
import gzip
import zipfile
import tarfile
import tempfile
import string
import random
from argparse import ArgumentParser
from charset_normalizer import from_path


def show_error(message: str):
    print(f"[ERROR]: {message}")


def load_json(path: str):
    try:
        with open(path, "r") as f:
            dictionary = json.load(f)
        return dictionary
    except json.JSONDecodeError:
        show_error("failed to load json file")
        sys.exit(1)
    except FileNotFoundError:
        show_error("json file not found")
        sys.exit(1)


def get_random_string():
    chars = string.ascii_letters + string.digits
    return "".join([random.choice(chars) for _ in range(5)]) + "_"


def handle_zip(path: str, mode: str):
    temp = path.replace(".zip", "")
    os.makedirs(temp)
    try:
        with zipfile.ZipFile(path, "r") as zf:
            zf.extractall(temp)
    except RuntimeError:
        show_error(
            f"failed to extract {path.replace(temp_dir, '').lstrip(os.path.sep)}"
        )
        return
    handle_files(temp, mode)
    os.remove(path)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for zroot, zdirs, zfilenames in os.walk(temp):
            for zfilename in zfilenames:
                zpath = os.path.join(zroot, zfilename)
                zf.write(zpath, arcname=zpath.replace(temp, ""))
    shutil.rmtree(temp)
    if mode == "rename":
        rename_a_file(path)


def handle_tar(path: str, mode: str):
    if path.endswith("gz"):
        temp = path.replace(".tar.gz", "")
        temp = temp.replace(".tgz", "")
        arctype = ":gz"
    else:
        temp = path.replace(".tar", "")
        arctype = ""
    os.makedirs(temp)
    try:
        with tarfile.open(path, "r" + arctype) as tf:
            tf.extractall(temp)
    except tarfile.ExtractError:
        show_error(
            f"failed to extract {path.replace(temp_dir, '').lstrip(os.path.sep)}"
        )
        return
    handle_files(temp, mode)
    os.remove(path)
    with tarfile.open(path, "w" + arctype) as tf:
        for troot, tdirs, tfilenames in os.walk(temp):
            for tfilename in tfilenames:
                tpath = os.path.join(troot, tfilename)
                tf.add(tpath, arcname=tpath.replace(temp, ""))
    shutil.rmtree(temp)
    if mode == "rename":
        rename_a_file(path)


def handle_gzip(path: str):
    temp = path.replace(".gz", "")
    try:
        with gzip.open(path, "rb") as gzf:
            with open(temp, "wb") as f:
                f.write(gzf.read())
    except gzip.BadGzipFile:
        show_error(f"failed to extract {path.replace(temp_dir, '')}")
        return

    modify_a_file(temp)

    with open(temp, "rb") as f:
        with gzip.open(path, "wb") as gzf:
            gzf.write(f.read())

    os.remove(temp)


def modify_a_file(path: str):
    count = 0
    try:
        enc_type = from_path(path).best().encoding
        with open(path, "r", encoding=enc_type) as f:
            text = f.read()
    except Exception:
        show_error(f"failed to read {path.replace(temp_dir, '').lstrip(os.path.sep)}")
        return

    for regex, substitute in filter_list.items():
        count += len(re.findall(regex, text, flags=re.IGNORECASE))
        text = re.sub(regex, substitute, text, flags=re.IGNORECASE)

    if count:
        with open(path, "w", encoding=enc_type) as f:
            f.write(text)
        print(f"[MODIFIED {count}]: {path.replace(temp_dir, '').lstrip(os.path.sep)}")
    else:
        print(f"[NOT MODIFIED]: {path.replace(temp_dir, '').lstrip(os.path.sep)}")


def rename_a_file(path: str):
    new_name = name = os.path.basename(path)
    for regex, substitute in filter_list.items():
        new_name = re.sub(regex, substitute, new_name, flags=re.IGNORECASE)

    if new_name != name:
        new_path = os.path.join(os.path.dirname(path), new_name)
        if os.path.exists(new_path):
            new_name = get_random_string() + new_name
            new_path = os.path.join(os.path.dirname(path), new_name)
        os.rename(path, new_path)
        print(
            f"[RENAMED]: {path.replace(temp_dir, '').lstrip(os.path.sep)} => {new_path.replace(temp_dir, '').lstrip(os.path.sep)}"
        )
    else:
        print(f"[NOT RENAMED]: {path.replace(temp_dir, '').lstrip(os.path.sep)}")


def handle_files(dir: str, mode: str):
    for path in [os.path.join(dir, item) for item in os.listdir(dir)]:

        if os.path.isdir(path):
            if mode == "modify":
                handle_files(path, "modify")
            else:
                handle_files(path, "rename")
                rename_a_file(path)
            continue

        if zipfile.is_zipfile(path):
            handle_zip(path, mode)
            continue

        if tarfile.is_tarfile(path):
            handle_tar(path, mode)
            continue

        if path.endswith(".gz") and mode == "modify":
            handle_gzip(path)
            continue

        if mode == "modify":
            modify_a_file(path)
        else:
            rename_a_file(path)


def parse_arguments():
    parser = ArgumentParser(
        description="Replace matched strings in file content and filenames with specified substitute using regular expressions",
        add_help=False,
    )
    required = parser.add_argument_group("required")
    modifiers = parser.add_argument_group("modifiers")
    optional = parser.add_argument_group("optional")
    required.add_argument(
        "-i",
        "--input",
        type=str,
        nargs="+",
        help="path to files or directories containing files",
        required=True,
    )
    required.add_argument(
        "-f",
        "--filter",
        type=str,
        help="path to a json file in REGEX:WORD format",
        required=True,
    )
    required.add_argument(
        "-o",
        "--output",
        type=str,
        help="path to output directory",
        required=True,
    )
    modifiers.add_argument(
        "-m",
        "--modify",
        action="store_true",
        help="use filter to modify content of files",
    )
    modifiers.add_argument(
        "-r", "--rename", action="store_true", help="use filter to rename files"
    )
    optional.add_argument(
        "-h", "--help", action="help", help="show this help message and exit"
    )
    return parser.parse_args()


def main():
    try:
        args = parse_arguments()

        if not (args.modify or args.rename):
            show_error("use -m and/or -r modifiers")
            sys.exit(1)

        global filter_list
        filter_list = load_json(args.filter)

        global temp_dir
        temp_dir = tempfile.mkdtemp()

        for item in args.input:
            if not os.path.exists(item):
                show_error(f"{item} not found")
                continue

            if os.path.isdir(item):
                item = item.rstrip(os.path.sep)
                shutil.copytree(item, os.path.join(temp_dir, os.path.basename(item)))
            else:
                shutil.copyfile(item, os.path.join(temp_dir, os.path.basename(item)))

        if args.modify:
            handle_files(temp_dir, "modify")

        if args.modify and args.rename:
            print("-" * os.get_terminal_size().columns)

        if args.rename:
            handle_files(temp_dir, "rename")

        out_dir = os.path.join(args.output, "REGEX_FILTER")

        if os.path.exists(out_dir):
            shutil.rmtree(out_dir)
        shutil.move(temp_dir, out_dir)
    except KeyboardInterrupt:
        try:
            shutil.rmtree(temp_dir)
        except NameError:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
