from __future__ import annotations

from sklearn.metrics import brier_score_loss, log_loss


def prepare_original_rows(frame):
    prepared = frame.sort_values("match_date").reset_index(drop=True).copy()
    prepared["fight_key"] = prepared.apply(
        lambda row: "_".join(sorted([row["fighter_1"], row["fighter_2"]]))
        + "_"
        + str(row["match_date"].date()),
        axis=1,
    )
    prepared["is_mirror"] = prepared.duplicated(
        subset="fight_key",
        keep="first",
    )
    return prepared[~prepared["is_mirror"]].copy()


def american_profit_odds(moneyline):
    try:
        ml = float(str(moneyline).replace("+", ""))
    except (TypeError, ValueError):
        return None
    return ml / 100 if ml > 0 else 100 / abs(ml)


def score_predictions(y_true, predictions):
    return (
        brier_score_loss(y_true, predictions),
        log_loss(y_true, predictions),
    )


def print_roi_table(simulator, frame, thresholds, predictions=None):
    print(f"\n{'Threshold':>10} {'Bets':>6} {'Win%':>7} {'ROI':>8}")
    print("-" * 35)

    for threshold in thresholds:
        if predictions is None:
            roi, bets, win_rate = simulator(frame, threshold)
        else:
            roi, bets, win_rate = simulator(frame, predictions, threshold)

        if roi is None:
            print(f"{threshold:>10.0%} {'0':>6} {'N/A':>7} {'N/A':>8}")
        else:
            print(
                f"{threshold:>10.0%} {bets:>6} "
                f"{win_rate:>6.1f}% {roi:>7.1f}%"
            )
