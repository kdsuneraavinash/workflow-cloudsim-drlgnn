import dataclasses
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import tyro


@dataclasses.dataclass
class Args:
    import_csv: str
    """file to import the CSV"""


def main(args: Args):
    fig, axes = plt.subplots(1, 2, figsize=(18, 9), sharey=False)

    df = pd.read_csv(args.import_csv)
    sns.boxplot(data=df, x="Algorithm", y="Makespan", ax=axes[0], palette="Set2")
    axes[0].set_title(f"Distribution of Makespan")
    axes[0].set_ylabel("Makespan (s)")
    axes[0].set_xlabel("Algorithm")
    axes[0].tick_params(axis="x", rotation=45)

    sns.boxplot(data=df, x="Algorithm", y="EnergyJ", ax=axes[1], palette="Set2")
    axes[1].set_title(f"Distribution of Energy Consumption")
    axes[1].set_ylabel("Energy Consumption (J)")
    axes[1].set_xlabel("Algorithm")
    axes[1].tick_params(axis="x", rotation=45)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main(tyro.cli(Args))