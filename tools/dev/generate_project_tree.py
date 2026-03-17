import os


def get_top_level_dirs(root_path, ignore_dirs):
    """Возвращает список директорий верхнего уровня, исключая игнорируемые."""
    return sorted(
        [d for d in os.listdir(root_path) if os.path.isdir(os.path.join(root_path, d)) and d not in ignore_dirs]
    )


def generate_tree(root_path, target_dir, ignore_dirs, ignore_extensions, output_file):
    """Генерирует дерево для указанной целевой директории (или всего проекта)."""

    # Если target_dir это корень проекта, начинаем с него, иначе с подпапки
    start_path = os.path.join(root_path, target_dir) if target_dir else root_path

    with open(output_file, "w", encoding="utf-8") as f:
        title = f"Project Structure: {target_dir if target_dir else 'Full Project'}"
        f.write(f"{title}\n{'=' * len(title)}\n\n")

        for current_root, dirs, files in os.walk(start_path, topdown=True):
            # Фильтрация папок на лету
            dirs[:] = [d for d in dirs if d not in ignore_dirs]

            # Вычисляем уровень вложенности относительно start_path
            rel_path = os.path.relpath(current_root, start_path)
            if rel_path == ".":
                level = 0
                display_name = os.path.basename(start_path)
            else:
                level = rel_path.count(os.sep) + 1
                display_name = os.path.basename(current_root)

            indent = "    " * level
            f.write(f"{indent}📂 {display_name}/\n")

            sub_indent = "    " * (level + 1)
            for file in sorted(files):
                if not any(file.endswith(ext) for ext in ignore_extensions):
                    f.write(f"{sub_indent}📄 {file}\n")


def main():
    # Настройки
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Идем на два уровня вверх: tools/dev -> tools -> lily_website
    project_root = os.path.dirname(os.path.dirname(current_dir))
    output_filename = os.path.normpath(os.path.join(project_root, "project_structure.txt"))

    ignore_dirs = {
        ".git",
        ".github",
        "venv",
        ".venv",
        "__pycache__",
        ".idea",
        ".vscode",
        "data",
        "logs",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".gemini",
        "node_modules",
        "site-packages",
    }
    ignore_files_extensions = {
        ".pyc",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".db",
        ".sqlite3",
        ".ico",
        ".woff",
        ".woff2",
    }

    # 1. Сканируем верхний уровень
    top_dirs = get_top_level_dirs(project_root, ignore_dirs)

    # 2. Меню выбора
    print(f"\n🔍 Сканирование проекта: {project_root}")
    print("Выберите область для генерации структуры:\n")
    print("   0. 🌳 ВЕСЬ ПРОЕКТ (Full Structure)")

    for idx, folder in enumerate(top_dirs, 1):
        print(f"   {idx}. 📁 {folder}/")

    # 3. Ввод пользователя
    while True:
        try:
            choice = input(f"\nВведите номер (0-{len(top_dirs)}): ").strip()
            if not choice.isdigit():
                raise ValueError
            choice_idx = int(choice)

            if 0 <= choice_idx <= len(top_dirs):
                break
            print("❌ Неверный номер. Попробуйте еще раз.")
        except ValueError:
            print("❌ Введите число.")

    # 4. Определение цели
    target_folder = None  # None означает весь проект
    if choice_idx > 0:
        target_folder = top_dirs[choice_idx - 1]

    # 5. Генерация
    print(f"\n⚙️ Генерирую структуру для: {target_folder if target_folder else 'Весь проект'}...")
    generate_tree(project_root, target_folder, ignore_dirs, ignore_files_extensions, output_filename)

    print(f"✅ Готово! Результат сохранен в: {output_filename}")


if __name__ == "__main__":
    main()
