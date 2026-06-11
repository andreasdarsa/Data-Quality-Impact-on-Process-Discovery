from pathlib import Path
import argparse
import pandas as pd


def add_reconstructed_fitness(input_path: str, output_path: str | None = None) -> None:
    input_path = Path(input_path)

    if output_path is None:
        output_path = input_path.with_name(input_path.stem + "_with_fitness.csv")
    else:
        output_path = Path(output_path)

    df = pd.read_csv(input_path)

    required_cols = [
        "average_score",
        "precision",
        "generalization",
        "simplicity",
    ]

    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    for col in required_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["fitness_reconstructed"] = (
        4 * df["average_score"]
        - df["precision"]
        - df["generalization"]
        - df["simplicity"]
    )

    # Προστασία από μικρά floating point artifacts, π.χ. 1.0000000002
    df["fitness_reconstructed"] = df["fitness_reconstructed"].clip(lower=0, upper=1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    print(f"Saved updated CSV to: {output_path}")
    print(df[["miner", "dimension", "degradation_level", "fitness_reconstructed"]].head())


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        required=True,
        help="Input discovery results CSV.",
    )

    parser.add_argument(
        "--output",
        default=None,
        help="Output CSV path. If omitted, creates *_with_fitness.csv.",
    )

    args = parser.parse_args()

    add_reconstructed_fitness(
        input_path=args.input,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
