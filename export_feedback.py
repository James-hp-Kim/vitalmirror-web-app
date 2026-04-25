from server import export_feedback_csv, init_db


def main() -> None:
    init_db()
    export_path = export_feedback_csv()
    print(export_path)


if __name__ == "__main__":
    main()
