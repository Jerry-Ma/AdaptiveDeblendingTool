#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Create Date    :  2015-03-15 22:43
# Python Version :  %PYVER%
# Git Repo       :  https://github.com/Jerry-Ma
# Email Address  :  jerry.ma.nk@gmail.com
"""
utils.py
"""

import string

def radius_str_to_degree(s):
    if not isinstance(s, str):
        return float(s)
    if s[-1] in map(str, range(10)):
        return float(s)
    elif s[-1] == "'":
        return float(s[:-1]) / 60.
    elif s[-1] == '"':
        return float(s[:-1]) / 3600.
    else:
        print '[!] radius string {0:s} not recognized'.format(s)
        return float(s)


def get_dtype_code(s):
    try:
        int(s)
        return 'i'
    except ValueError:
        try:
            float(s)
            return 'f'
        except ValueError:
            if len(s) < 127:
                return '|S127'
            else:
                return '|S{0:d}'.format(len(s * 2))  # to make it safer


def get_ascii_table_header(fn):
    with open(fn, 'r') as fo:
        header = []
        while True:
            ln = fo.next()
            if ln.strip().startswith('#'):
                header.append(ln.strip().lstrip('#').split())
            else:
                template = ln.strip().split()
                break
        if header == []:
            header = template[:]
            template = fo.next().strip().split()
            if map(get_dtype_code, header) == map(get_dtype_code, template):
                header = ['col{0:d}'.format(i) for i
                          in range(1, len(template))]
        elif len(header) == 1:
            header = header[0]
        else:
            # sextractor header
            header = [h[1] for h in header]
        return header, map(get_dtype_code, template)


def parse_ds9xclipboard(content):

    content = content.replace('{}', ' ')
    entry = content.lstrip('{').rstrip('}').split('} {')
    if entry[0] == content:
        table = []
    else:
        table = [tuple(i.split()) for i in entry]
    return table


def parse_inputfile(infile):
    in_braket = False
    pardict = {}
    with open(infile, 'r') as fo:
        for ln in fo.readlines():
            # remove comment
            ln = ln.strip().split("#")[0]
            # remove blank line
            if ln == "":
                continue
            if not in_braket:
                key, value = map(string.strip, ln.split('=', 1))
                if value[0] == "[" and value[-1] != "]":
                    value_tbd = value[1:]
                    in_braket = True
                elif value[0] == "[" and value[-1] == "]":
                    if value[1:-1] == "":
                        pardict[key] = []
                        continue
                    else:
                        value_list = map(string.strip, value[1:-1].split(','))
                        pardict[key] = map(string_remove_quote, value_list)
                else:
                    if '_list' in key:
                        # the string should be a file
                        value_list = []
                        with open(string_remove_quote(value), 'r') as fo2:
                            for ln2 in fo2.readlines():
                                ln2 = ln2.strip().split("#")[0]
                                if ln2 == "":
                                    continue
                                value_list.append(ln2.strip())
                            pardict[key] = map(string_remove_quote, value_list)
                    else:
                        pardict[key] = string_remove_quote(value)
            else:
                value = ln.strip()
                if value[-1] == "]":
                    value_tbd += value[:-1]
                    if value_tbd == "":
                        pardict[key] = []
                        continue
                    else:
                        value_list = map(string.strip, value_tbd.split(','))
                        pardict[key] = map(string_remove_quote, value_list)
                    in_braket = False
                else:
                    value_tbd += value
    # do a sanity check: lenth of the all the lists should be the same
    try:
        assert len(set(map(len,
                       [v for k, v in pardict.items() if '_list' in k]))) == 1
    except AssertionError:
        print ("[!] Fail load inputfile:"
            "the number of elements in the lists is not consistent")
        raise
    return pardict


def string_remove_quote(s):
    if (s.startswith("'") and s.endswith("'")
        ) or (s.startswith('"') and s.endswith('"')) :
        s = s[1:-1]
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return s



if __name__ == '__main__':
    # test parse inputfile
    print parse_inputfile("./default.input")
