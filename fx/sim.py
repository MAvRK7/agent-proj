import math
import random

def monte_carlo_simulation(current_rate, drift, volatility, days=30, simulations=1000):
    results = []
    for _ in range(simulations):
        price = current_rate
        for _ in range(days):
            shock = random.gauss(drift, volatility)
            price *= math.exp(shock)
        results.append(price)
    return results