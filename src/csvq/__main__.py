"""支持 ``python -m csvq`` 直接运行。"""

import sys

from csvq.cli import main

if __name__ == "__main__":
    sys.exit(main())
