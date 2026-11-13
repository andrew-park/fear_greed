import unittest

import numpy as np
import pandas as pd

from fear_greed import calculate_fear_greed, sentiment_label


class FearGreedTests(unittest.TestCase):
    def test_scores_are_bounded_and_composite_is_mean(self):
        index = pd.bdate_range("2018-01-01", periods=1500)
        rng = np.random.default_rng(42)
        returns = rng.normal(0.0003, 0.012, len(index))
        close = pd.Series(100 * np.exp(np.cumsum(returns)), index=index)

        result = calculate_fear_greed(close)
        scored = result.dropna(subset=["fear_greed"])
        score_columns = [
            "trend_score",
            "momentum_score",
            "range_score",
            "drawdown_score",
            "volatility_score",
        ]

        self.assertGreater(len(scored), 0)
        self.assertTrue(((scored[score_columns] >= 0) & (scored[score_columns] <= 100)).all().all())
        expected = scored[score_columns].mean(axis=1)
        np.testing.assert_allclose(scored["fear_greed"], expected)

    def test_label_boundaries(self):
        self.assertEqual(sentiment_label(0), "Extreme Fear")
        self.assertEqual(sentiment_label(25), "Extreme Fear")
        self.assertEqual(sentiment_label(25.01), "Fear")
        self.assertEqual(sentiment_label(50), "Neutral")
        self.assertEqual(sentiment_label(75), "Greed")
        self.assertEqual(sentiment_label(75.01), "Extreme Greed")

    def test_rejects_non_positive_prices(self):
        close = pd.Series([100.0, 99.0, 0.0])
        with self.assertRaises(ValueError):
            calculate_fear_greed(close)


if __name__ == "__main__":
    unittest.main()
