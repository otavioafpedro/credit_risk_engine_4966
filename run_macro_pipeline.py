from __future__ import annotations

from src.macro_data_pipeline import (
    DEFAULT_MACRO_EXPORT_PATH,
    DEFAULT_MACRO_WIDE_EXPORT_PATH,
    MacroDataPipeline,
)


def main() -> None:
    pipeline = MacroDataPipeline()
    result = pipeline.run(
        export_path=DEFAULT_MACRO_EXPORT_PATH,
        wide_export_path=DEFAULT_MACRO_WIDE_EXPORT_PATH,
    )

    print("=== MACRO DATA PIPELINE ===")
    print(f"Series no catalogo: {len(result.loads)}")
    print(f"Series carregadas: {len(result.succeeded)}")
    print(f"Series com falha: {len(result.failed)}")
    print(f"Series ignoradas: {len(result.skipped)}")
    print(f"Linhas consolidadas: {len(result.data)}")

    if result.export_path is not None:
        print(f"Arquivo raw gerado: {result.export_path}")
    if result.wide_export_path is not None:
        print(f"Arquivo wide gerado: {result.wide_export_path}")

    source_summary = result.summarize_by_source()
    if not source_summary.empty:
        print("\nResumo por fonte:")
        for row in source_summary.to_dict(orient="records"):
            print(
                "- "
                f"{row['source']}: "
                f"{row['series_loaded']} series carregadas, "
                f"{row['series_failed']} falhas, "
                f"{row['series_skipped']} ignoradas, "
                f"{row['row_count']} linhas"
            )

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
