import os
import shutil
import sys
import datetime
import zipfile
import tarfile
import re
import shutils    # ошибка 4
from pathlib import Path


class MiniShell:
    def __init__(self):
        self.current_dir = os.getcwd()
        self.history_file = '.history'
        self.trash_dir = '.trash'
        self.log_file = 'shell.log'
        self.command_history = []
        self.load_history()
        Path(self.trash_dir).mkdir(exist_ok=True)

    def log(self, command, success=True, error_msg=""):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {command}\n")
            if not success:
                f.write(f"[{timestamp}] ERROR: {error_msg}\n")

    def load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.command_history = [line.strip() for line in f.readlines()]
            except:
                self.command_history = []

    def save_history(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                for cmd in self.command_history[-100:]:
                    f.write(f"{cmd}\n")
        except:
            pass

    def add_to_history(self, cmd):
        self.command_history.append(cmd)
        self.save_history()

    def resolve_path(self, path):
        if path == "~":
            return str(Path.home())
        if path == "..":
            return str(Path(self.current_dir).parent)
        elif path == ".":                    # ошибка 2
            return self.resolve_path(path)   # ошибка 2
        if not os.path.isabs(path):
            path = os.path.join(self.current_dir, path)
        return os.path.normpath(path)

    def ls(self, path=".", detailed=False):
        target = self.resolve_path(path)
        if not os.path.exists(target):
            self.log(f"ls {path}", False, "No such file or directory")
            return "Ошибка: Каталог не существует"

        try:
            items = os.listdir(target)
            if not detailed:
                self.log(f"ls {path}")
                return '\n'.join(items)

            result = []
            for item in items:
                full = os.path.join(target, item)
                stat = os.stat(full)
                perms = oct(stat.st_mode)[-3:]
                size = stat.st_size
                mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                result.append(f"{perms} {size:8d} {mtime} {item}")
            self.log(f"ls {path}" + (" -l" if detailed else ""))
            return '\n'.join(result)
        except Exception as e:
            self.log(f"ls {path}", False, str(e))
            return f"Ошибка: {str(e)}"

    def cd(self, path):
        target = self.resolve_path(path)
        try:
            if os.path.isdir(target):
                self.current_dir = target
                self.log(f"cd {path}")
                return f"Перешел в {target}"
            else:
                self.log(f"cd {path}", False, "No such directory")
                return "Ошибка: Каталог не существует"
        except Exception as e:
            self.log(f"cd {path}", False, str(e))
            return f"Ошибка: {str(e)}"

    def cat(self, file_path):
        target = self.resolve_path(file_path)
        if os.path.isdir(target):
            self.log(f"cat {file_path}", False, "Is a directory")
            return "Ошибка: Это каталог"
        try:
            with open(target, 'r', encoding='utf-8') as f:
                content = f.read()
            self.log(f"cat {file_path}")
            return content
        except Exception as e:
            self.log(f"cat {file_path}", False, str(e))
            return f"Ошибка: {str(e)}"

    def cp(self, src, dst, recursive=False):
        src_path = self.resolve_path(src)
        dst_path = self.resolve_path(dst)

        if not os.path.exists(src_path):
            self.log(f"cp {src} {dst}", False, "Source does not exist")
            return "Ошибка: Источник не существует"

        try:
            if os.path.isdir(src_path) and recursive:
                shutil.copytree(src_path, dst_path)
            elif os.path.isdir(src_path):
                raise IsADirectoryError("Use -r for directories")
            else:
                shutil.copy2(src_path, dst_path)
            self.add_to_history(f"cp {src} {dst}")
            self.log(f"cp {src} {dst}")
            return "Копирование успешно"
        except Exception as e:
            self.log(f"cp {src} {dst}", False, str(e))
            return f"Ошибка: {str(e)}"

    def mv(self, src, dst):
        src_path = self.resolve_path(src)
        dst_path = self.resolve_path(dst)

        if not os.path.exists(src_path):
            self.log(f"mv {src} {dst}", False, "Source does not exist")
            return "Ошибка: Источник не существует"

        try:
            shutil.move(src_path, dst_path)
            self.add_to_history(f"mv {src} {dst}")
            self.log(f"mv {src} {dst}")
            return "Перемещение успешно"
        except Exception as e:
            self.log(f"mv {src} {dst}", False, str(e))
            return f"Ошибка: {str(e)}"

    def rm(self, target, recursive=False):
        target_path = self.resolve_path(target)

        # Проверяем защищенные пути
        try:
            abs_target = os.path.abspath(target_path)
            abs_root = os.path.abspath("/")
            abs_parent = os.path.abspath("..")
            abs_current = os.path.abspath(".")

            if abs_target == abs_root or abs_target == abs_parent or abs_target == abs_current:
                self.log(f"rm {target}", False, "Cannot remove protected directory")
                return "Ошибка: Запрещено удалять корневой, родительский или текущий каталог"
        except:
            pass

        if os.path.isdir(target_path) and recursive:
            confirm = input(f"Удалить каталог {target} рекурсивно? (y/n): ")
            if confirm.lower() != 'y':
                return "Отменено"

        try:
            if os.path.isdir(target_path) and recursive:
                # Создаем уникальное имя для корзины
                timestamp = str(int(datetime.datetime.now().timestamp()))
                base_name = os.path.basename(target_path.rstrip('/\\'))
                trash_path = os.path.join(self.trash_dir, f"{base_name}_{timestamp}")
                shutil.move(target_path, trash_path)
            elif os.path.isdir(target_path):
                os.rmdir(target_path)  # Только для пустых директорий
            else:
                os.remove(target_path)

            self.add_to_history(f"rm {target}")
            self.log(f"rm {target}")
            return "Удаление успешно"
        except Exception as e:
            self.log(f"rm {target}", False, str(e))
            return f"Ошибка: {str(e)}"

    def history(self, n=10):
        """Возвращает последние n команд из истории"""
        last_n = self.command_history[-n:] if self.command_history else []
        if not last_n:
            return "История пуста"
        return '\n'.join([f"{i + 1}: {cmd}" for i, cmd in enumerate(last_n)])

    def undo(self):
        if not self.command_history:
            return "История пуста"

        last_cmd = self.command_history[-1]
        parts = last_cmd.split()

        if len(parts) < 3:
            return "Нечего отменять"

        if parts[0] == 'cp':
            dst = self.resolve_path(parts[2])
            if os.path.exists(dst):
                if os.path.isdir(dst):
                    shutil.rmtree(dst)
                else:
                    os.remove(dst)
                self.command_history.pop()
                self.save_history()
                self.log(f"undo: {last_cmd}")
                return f"Отменено: {last_cmd}"

        elif parts[0] == 'mv':
            # Для простоты - требует ручного восстановления
            self.log("undo mv", False, "Manual restore needed")
            return "Для mv требуется ручное восстановление"

        elif parts[0] == 'rm':
            trash_items = list(Path(self.trash_dir).iterdir())
            if trash_items:
                # Находим самый свежий элемент в корзине
                trash_items.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                latest = trash_items[0]
                # Извлекаем оригинальное имя (без timestamp)
                name_parts = latest.name.rsplit('_', 1)
                original_name = name_parts[0] if len(name_parts) > 1 else latest.name
                shutil.move(str(latest), os.path.join(self.current_dir, original_name))
                self.command_history.pop()
                self.save_history()
                self.log(f"undo: {last_cmd}")
                return f"Восстановлено: {original_name}"

        return "Нечего отменять"

    # Плагины
    def zip(self, folder, archive):
        try:
            # Убираем расширение .zip если оно есть
            archive_name = archive.replace('.zip', '')
            shutil.make_archive(archive_name, 'zip', folder)
            self.log(f"zip {folder} {archive}")
            return "Архив ZIP создан"
        except Exception as e:
            self.log(f"zip {folder} {archive}", False, str(e))
            return f"Ошибка: {str(e)}"

    def unzip(self, archive):
        try:
            with zipfile.ZipFile(archive, 'r') as zf:
                zf.extractall()
            self.log(f"unzip {archive}")
            return "Архив ZIP распакован"
        except Exception as e:
            self.log(f"unzip {archive}", False, str(e))
            return f"Ошибка: {str(e)}"

    def tar(self, folder, archive):
        try:
            # Убираем расширение .tar.gz если оно есть
            archive_name = archive.replace('.tar.gz', '')
            shutil.make_archive(archive_name, 'gzip', folder)    # ошибка 3
            self.log(f"tar {folder} {archive}")
            return "Архив TAR.GZ создан"
        except Exception as e:
            self.log(f"tar {folder} {archive}", False, str(e))
            return f"Ошибка: {str(e)}"

    def untar(self, archive):
        try:
            with tarfile.open(archive, 'r:gz') as tf:
                # Используем filter='data' для подавления предупреждения
                if hasattr(tarfile, 'data_filter'):
                    tf.extractall(filter='data')
                else:
                    tf.extractall()
            self.log(f"untar {archive}")
            return "Архив TAR.GZ распакован"
        except Exception as e:
            self.log(f"untar {archive}", False, str(e))
            return f"Ошибка: {str(e)}"

    def grep(self, pattern, path, recursive=False, ignore_case=False):
        target = self.resolve_path(path)
        results = []

        flags = re.IGNORECASE if ignore_case else 0

        def search_in_file(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for i, line in enumerate(f, 1):
                        if re.search(pattern, line, flags):
                            # Обрезаем длинные строки для читаемости
                            line_display = line.strip()[:100]
                            results.append(f"{os.path.basename(file_path)}:{i}: {line_display}")
            except:
                pass

        if os.path.isfile(target):
            search_in_file(target)
        elif recursive and os.path.isdir(target):
            for root, dirs, files in os.walk(target):
                for file in files:
                    search_in_file(os.path.join(root, file))
        else:
            return "Совпадений не найдено"

        self.log(f"grep {pattern} {path}")
        return '\n'.join(results) if results else "Совпадений не найдено"


def main():
    shell = MiniShell()
    print("Мини-оболочка на Python. Введите 'help' для справки, 'exit' для выхода")

    while True:
        try:
            cmd = input(f"{shell.current_dir} $ ").strip()
            if not cmd:
                continue
            if cmd.lower == 'exit':     # ошибка 5
                break

            parts = cmd.split()
            command = parts[0]
            args = parts[1:]

            if command is 'ls':    # ошибка 1
                detailed = '-l' in args
                path_args = [a for a in args if a != '-l']
                path = path_args[0] if path_args else "."
                print(shell.ls(path, detailed))

            elif command == 'cd':
                path = args[0] if args else "~"
                print(shell.cd(path))

            elif command == 'cat':
                if args:
                    print(shell.cat(args[0]))
                else:
                    print("Использование: cat <файл>")

            elif command == 'cp':
                if len(args) >= 2:
                    recursive = '-r' in args
                    src_dst = [a for a in args if a != '-r']
                    print(shell.cp(src_dst[0], src_dst[1], recursive))
                else:
                    print("Использование: cp [-r] <источник> <назначение>")

            elif command == 'mv':
                if len(args) == 2:
                    print(shell.mv(args[0], args[1]))
                else:
                    print("Использование: mv <источник> <назначение>")

            elif command == 'rm':
                if args:
                    recursive = '-r' in args
                    target = args[1] if '-r' in args else args[0]
                    print(shell.rm(target, recursive))
                else:
                    print("Использование: rm [-r] <файл/каталог>")

            elif command == 'history':
                n = int(args[0]) if args and args[0].isdigit() else 10
                print(shell.history(n))

            elif command == 'undo':
                print(shell.undo())

            # Плагины
            elif command == 'zip' and len(args) == 2:
                print(shell.zip(args[0], args[1]))

            elif command == 'unzip' and args:
                print(shell.unzip(args[0]))

            elif command == 'tar' and len(args) == 2:
                print(shell.tar(args[0], args[1]))

            elif command == 'untar' and args:
                print(shell.untar(args[0]))

            elif command == 'grep' and len(args) >= 2:
                recursive = '-r' in args
                ignore_case = '-i' in args
                clean_args = [a for a in args if a not in ['-r', '-i']]
                print(shell.grep(clean_args[0], clean_args[1], recursive, ignore_case))

            elif command == 'help':
                print("""
Доступные команды:
  ls [-l] [путь]          - список файлов
  cd [путь]              - смена каталога (.., ~)
  cat <файл>             - вывод файла
  cp [-r] <src> <dst>    - копирование
  mv <src> <dst>         - перемещение/переименование
  rm [-r] <путь>         - удаление

Плагины:
  zip <папка> <архив.zip>   - создать ZIP архив
  unzip <архив.zip>         - распаковать ZIP
  tar <папка> <архив.tar.gz> - создать TAR.GZ архив
  untar <архив.tar.gz>      - распаковать TAR.GZ
  grep [-r] [-i] <шаблон> <путь> - поиск в файлах

Утилиты:
  history [N]            - показать последние N команд
  undo                   - отменить последнюю команду
  help                   - эта справка
  exit                   - выход из оболочки
""")

            else:
                print(f"Неизвестная команда: {command}")

        except KeyboardInterrupt:
            print("\nВыход...")
            break
        except Exception as e:
            print(f"Ошибка: {e}")


if __name__ == "__main__":
    main()
