
import numpy as np
import pytest
from fiscal_model.long_run.solow_growth import SolowGrowthModel

def test_solow_growth_model_initialization():
    model = SolowGrowthModel()
    assert model.alpha == 0.35
    assert model.crowding_out_pct == 0.33
    assert model.initial_k == 84000.0

def test_solow_growth_simulation_no_deficit():
    model = SolowGrowthModel()
    # Zero deficits
    deficits = np.zeros(10)
    res = model.run_simulation(deficits, horizon=10)
    
    # With no deficits and steady state initial conditions (roughly), 
    # growth should be driven by TFP and population.
    # Check that capital stock is growing
    assert res.capital_stock[-1] > res.capital_stock[0]
    
    # GDP should be growing
    assert res.gdp[-1] > res.gdp[0]

def test_solow_growth_crowding_out_impact():
    # Case 1: 100% Crowding Out
    model_closed = SolowGrowthModel(crowding_out_pct=1.0)
    deficits = np.array([1000.0] * 10) # Large deficit
    res_closed = model_closed.run_simulation(deficits, horizon=10)
    
    # Case 2: 0% Crowding Out (Open Economy)
    model_open = SolowGrowthModel(crowding_out_pct=0.0)
    res_open = model_open.run_simulation(deficits, horizon=10)
    
    # Capital stock should be higher in open economy (no crowding out)
    assert res_open.capital_stock[-1] > res_closed.capital_stock[-1]
    
    # GDP should be higher in open economy
    assert res_open.gdp[-1] > res_closed.gdp[-1]

def test_solow_growth_horizon_extension():
    model = SolowGrowthModel()
    deficits = np.array([100.0])
    res = model.run_simulation(deficits, horizon=5)
    
    assert len(res.years) == 5
    assert len(res.gdp) == 5
