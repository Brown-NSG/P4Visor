# -*- coding: utf-8 -*-

# This is just a wrapper script around p4c_bm.__main__.py
# It makes sure that the PYTHONPATH does not need to be adjusted no matter where
# the package in installed.

import sys
sys.path.insert(0, "@pythondir@")

def main():
    import p4c_bm.__main__ as p4c_bm
    p4c_bm.main()

if __name__ == "__main__":
    main()
