from __future__ import annotations

from src.macro_data_pipeline import DEFAULT_MACRO_EXPORT_PATH, MacroDataPipeline


def main() -> None:
    pipeline = MacroDataPipeline()
    result = pipeline.run(export_path=DEFAULT_MACRO_EXPORT_PATH)

    print("=== MACRO DATA PIPELINE ===")
    print(f"Series no catalogo: {len(result.loads)}")
    print(f"Series carregadas: {len(result.succeeded)}")
    print(f"Series com falha: {len(result.failed)}")
    print(f"Series ignoradas: {len(result.skipped)}")
    print(f"Linhas consolidadas: {len(result.data)}")

    if result.export_path is not None:
        print(f"Arquivo gerado: {result.export_path}")

    if result.succeeded:
        print("\nSeries carregadas:")
        for record in result.succeeded:
            print(f"- {record.series_code} ({record.source}): {record.row_count} linhas")

    if result.failed:
        print("\nFalhas:")
        for record in result.failed:
            print(f"- {record.series_code} ({record.source}): {record.error}")


if __name__ == "__main__":
    main()
