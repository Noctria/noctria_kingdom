# tests/test_path_config.py

import unittest
import os
from core import path_config


class TestPathConfig(unittest.TestCase):
    """core/path_config.py に定義されたパスが実在するかを確認"""

    def test_path_variables_exist(self):
        # path_config 内の変数をすべて取得
        for var_name in dir(path_config):
            if var_name.isupper() and (var_name.endswith("_DIR") or var_name.endswith("_LOG")):
                path = getattr(path_config, var_name)

                with self.subTest(path_name=var_name):
                    self.assertTrue(
                        os.path.exists(path),
                        f"{var_name} → パスが存在しません: {path}"
                    )


if __name__ == "__main__":
    unittest.main()
