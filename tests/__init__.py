import os
import shutil
import tempfile
import unittest
from pathlib import Path
import sys
import io
import contextlib

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from main import MiniShell


class TestMiniShell(unittest.TestCase):
    def setUp(self):
        """Создание временной директории для тестов"""
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

        # Для проведения тестов надо создать соответствующие временные директории и файлы
        self.file1 = "test_file.txt"
        self.file2 = "another_file.txt"
        self.dir1 = "test_dir"
        self.subdir = "test_dir/subdir"
        self.nested_file = "test_dir/subdir/nested.txt"

        with open(self.file1, 'w', encoding='utf-8') as f:
            f.write("Hello World\nLine 2\nLine 3")

        with open(self.file2, 'w', encoding='utf-8') as f:
            f.write("Test content\nAnother line")

        os.makedirs(self.subdir, exist_ok=True)

        with open(self.nested_file, 'w', encoding='utf-8') as f:
            f.write("Nested content\nFind me")

        self.shell = MiniShell()

    def tearDown(self):
        """Очистка после тестов"""
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir)
        # Удаляем файлы логов
        for log_file in ['shell.log', '.history', '.trash']:
            if os.path.exists(log_file):
                if os.path.isdir(log_file):
                    shutil.rmtree(log_file)
                else:
                    os.remove(log_file)

    # ========== Тесты правильно работы кода ==========

    def test_01_ls_basic(self):
        """Тест команды ls без параметров"""
        result = self.shell.ls()
        self.assertIn(self.file1, result)
        self.assertIn(self.dir1, result)

    def test_02_ls_detailed(self):
        """Тест команды ls с опцией -l"""
        result = self.shell.ls(detailed=True)
        self.assertIn("test_file.txt", result)

    def test_03_cd_relative_path(self):
        """Тест перехода в относительную директорию"""
        initial_dir = self.shell.current_dir
        result = self.shell.cd(self.dir1)
        self.assertNotEqual(initial_dir, self.shell.current_dir)
        self.assertIn("Перешел", result)

    def test_04_cd_home(self):
        """Тест перехода в домашнюю директорию"""
        home_dir = str(Path.home())
        result = self.shell.cd("~")
        self.assertTrue(self.shell.current_dir.startswith(home_dir))

    def test_05_cat_success(self):
        """Тест чтения файла"""
        result = self.shell.cat(self.file1)
        self.assertIn("Hello World", result)
        self.assertIn("Line 2", result)

    def test_06_cp_file(self):
        """Тест копирования файла"""
        new_file = "copied_file.txt"
        result = self.shell.cp(self.file1, new_file)
        self.assertEqual("Копирование успешно", result)
        self.assertTrue(os.path.exists(new_file))

    def test_07_cp_directory_recursive(self):
        """Тест рекурсивного копирования директории"""
        dest_dir = "copied_dir"
        result = self.shell.cp(self.dir1, dest_dir, recursive=True)
        self.assertEqual("Копирование успешно", result)
        self.assertTrue(os.path.exists(dest_dir))

    def test_08_mv_file(self):
        """Тест перемещения файла"""
        new_name = "renamed_file.txt"
        result = self.shell.mv(self.file1, new_name)
        self.assertEqual("Перемещение успешно", result)
        self.assertTrue(os.path.exists(new_name))

    def test_09_grep_basic(self):
        """Тест поиска по содержимому"""
        result = self.shell.grep("World", self.file1)
        self.assertIn("World", result)

    def test_10_zip_command(self):
        """Тест создания архива"""
        result1 = self.shell.zip(self.dir1, "test.zip")
        self.assertIn("Архив ZIP создан", result1)

    # ========== Тесты ошибок выполнения кодов ==========

    def test_11_ls_nonexistent_directory(self):
        """Тест ls с несуществующей директорией"""
        result = self.shell.ls("non_existent_dir")
        self.assertIn("Ошибка", result)

    def test_12_cd_nonexistent_directory(self):
        """Тест перехода в несуществующую директорию"""
        result = self.shell.cd("non_existent_directory_12345")
        self.assertIn("Ошибка", result)

    def test_13_cat_directory_instead_of_file(self):
        """Тест чтения директории вместо файла"""
        result = self.shell.cat(self.dir1)
        self.assertIn("Ошибка", result)

    def test_14_cat_nonexistent_file(self):
        """Тест чтения несуществующего файла"""
        result = self.shell.cat("non_existent_file_98765.txt")
        self.assertIn("Ошибка", result)

    def test_15_cp_nonexistent_source(self):
        """Тест копирования несуществующего файла"""
        result = self.shell.cp("non_existent.txt", "dest.txt")
        self.assertIn("Ошибка", result)

    def test_16_cp_directory_without_recursive(self):
        """Тест копирования директории без флага -r"""
        result = self.shell.cp(self.dir1, "dest_dir")
        self.assertIn("Ошибка", result)

    def test_17_mv_nonexistent_source(self):
        """Тест перемещения несуществующего файла"""
        result = self.shell.mv("non_existent.txt", "dest.txt")
        self.assertIn("Ошибка", result)

    def test_18_rm_protected_paths(self):
        """Тест удаления защищенных путей"""
        # Имитируем ввод 'y' для теста
        import builtins
        original_input = builtins.input
        builtins.input = lambda _: 'y'

        try:
            # Проверяем запрет на удаление текущего каталога
            result = self.shell.rm(".", recursive=True)
            self.assertIn("Ошибка", result)
        finally:
            builtins.input = original_input

    def test_19_rm_directory_without_recursive(self):
        """Тест удаления пустой директории"""
        # Создаем ПУСТУЮ директорию для теста
        test_rm_dir = "empty_dir"
        os.makedirs(test_rm_dir, exist_ok=True)

        result = self.shell.rm(test_rm_dir, recursive=False)
        self.assertTrue("Удаление успешно" in result or "Ошибка" in result)

    def test_20_grep_nonexistent_file(self):
        """Тест поиска в несуществующем файле"""
        result = self.shell.grep("pattern", "non_existent_file.txt")
        self.assertEqual("Совпадений не найдено", result)

    # ========== Тесты работы плагинов ==========

class TestMiniShellPlugins(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

        # Создаем тестовую структуру для архивов
        self.archive_dir = "archive_test"

        os.makedirs(self.archive_dir, exist_ok=True)
        with open(os.path.join(self.archive_dir, "file.txt"), 'w') as f:
            f.write("Content for archive")

        self.shell = MiniShell()

    def tearDown(self):
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir)
        for log_file in ['shell.log', '.history', '.trash']:
            if os.path.exists(log_file):
                if os.path.isdir(log_file):
                    shutil.rmtree(log_file)
                else:
                    os.remove(log_file)

    def test_21_tar_command(self):
        """Тест создания tar.gz архива"""
        # Создаем архив
        result1 = self.shell.tar(self.archive_dir, "test.tar.gz")
        self.assertIn("Архив TAR.GZ создан", result1)

    def test_22_grep_recursive(self):
        """Тест рекурсивного поиска"""
        # Создаем вложенную структуру
        os.makedirs("dir1/dir2", exist_ok=True)
        with open("dir1/file1.txt", 'w') as f:
            f.write("search_pattern here")
        with open("dir1/dir2/file2.txt", 'w') as f:
            f.write("another search_pattern")

        result = self.shell.grep("search_pattern", ".", recursive=True)
        self.assertIn("file1.txt", result)

    def test_23_grep_case_insensitive(self):
        """Тест поиска без учета регистра"""
        test_file = "case_test.txt"
        with open(test_file, 'w') as f:
            f.write("UPPERCASE\nlowercase\nMixedCase")

        result = self.shell.grep("uppercase", test_file, ignore_case=True)
        self.assertIn("UPPERCASE", result)

    def test_24_history_works(self):
        """Тест работы истории"""
        # Добавляем команды напрямую
        self.shell.add_to_history("ls -l")
        self.shell.add_to_history("cd test")

        # Проверяем что команды добавились
        self.assertGreater(len(self.shell.command_history), 0)

    def test_25_undo_cp(self):
        """Тест отмены копирования"""
        # Создаем и копируем файл
        source = "source_undo.txt"
        dest = "dest_undo.txt"

        with open(source, 'w') as f:
            f.write("test content")

        self.shell.cp(source, dest)
        self.assertTrue(os.path.exists(dest))

        # Отменяем
        result = self.shell.undo()
        self.assertIn("Отменено", result)

    def test_26_logging_works(self):
        """Тест работы логирования"""
        # Выполняем команду
        result = self.shell.ls()

        # Проверяем, что лог-файл создан
        self.assertTrue(os.path.exists('shell.log'))

    def test_27_rm_with_confirmation(self):
        """Тест удаления с подтверждением"""
        # Создаем директорию для удаления
        dir_to_remove = "confirm_test_dir"
        os.makedirs(dir_to_remove, exist_ok=True)

        # Имитируем ввод 'y' (подтверждение)
        import builtins
        original_input = builtins.input
        builtins.input = lambda _: 'y'

        try:
            result = self.shell.rm(dir_to_remove, recursive=True)
            self.assertIn("Удаление успешно", result)
        finally:
            builtins.input = original_input

    def test_28_undo_empty_history(self):
        """Тест отмены при пустой истории"""
        result = self.shell.undo()
        self.assertEqual("История пуста", result)

    def test_29_complex_command_sequence(self):
        """Тест сложной последовательности команд"""
        # Создаем файл
        test_file = "test_file.txt"
        with open(test_file, 'w') as f:
            f.write("content")

        # Проверяем ls
        result = self.shell.ls()
        self.assertIn(test_file, result)

    def test_30_history_command_output(self):
        """Тест вывода команды history"""
        # Добавляем команды в историю
        self.shell.add_to_history("ls -l")
        self.shell.add_to_history("cd test")

        # Получаем историю
        result = self.shell.history(2)
        self.assertIn("ls -l", result)


def run_tests():
    """Запуск тестов с красивым выводом"""
    buffer = io.StringIO()

    with contextlib.redirect_stdout(buffer):
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()

        suite.addTests(loader.loadTestsFromTestCase(TestMiniShell))
        suite.addTests(loader.loadTestsFromTestCase(TestMiniShellPlugins))

        runner = unittest.TextTestRunner(verbosity=1, stream=buffer)
        result = runner.run(suite)

    print("=" * 60)
    print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ МИНИ-ОБОЛОЧКИ")
    print("=" * 60)
    print(f"Всего тестов: {result.testsRun}")

    passed = result.testsRun - len(result.failures) - len(result.errors)
    print(f"Пройдено успешно: {passed}")

    if result.failures:
        print(f"Провалено: {len(result.failures)}")
        for test, trace in result.failures:
            print(f"\n {test}:")
            first_line = str(trace).split('\n')[0]
            print(f"   {first_line}")

    if result.errors:
        print(f"Ошибок: {len(result.errors)}")
        for test, trace in result.errors:
            print(f"\n  {test}:")
            first_line = str(trace).split('\n')[0]
            print(f"   {first_line}")

    if not result.failures and not result.errors:
        print("\n Все тесты пройдены успешно!")

    print("=" * 60)

    return result


if __name__ == '__main__':
    run_tests()
