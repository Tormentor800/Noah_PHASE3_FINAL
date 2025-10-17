from __future__ import annotations
from datetime import datetime, timedelta

from src.risk.types import BetPosition
from src.risk.guards import is_kill_switch_enabled, should_block_by_correlation

def _mk(ti: int, side: str, stake: float, league='NBA', market='Spread'):
    return BetPosition(
        bet_id=f'b{ti}-{side}',
        ts=datetime(2025,1,1) + timedelta(minutes=ti),
        league=league, market=market, team_or_side=side,
        stake=stake, odds=1.90
    )

def test_kill_switch_true_blocks_all():
    cfg = {'risk': {'kill_switch': True}}
    assert is_kill_switch_enabled(cfg) is True

def test_kill_switch_false_allows():
    cfg = {'risk': {'kill_switch': False}}
    assert is_kill_switch_enabled(cfg) is False

def test_correlation_block_triggers_when_series_is_correlated():
    open_positions = [
        _mk(0,'LAL -3.5',1.0),
        _mk(1,'LAL -3.5',2.0),
        _mk(2,'LAL -3.5',3.0),
        _mk(0,'BOS +3.5',1.2),
        _mk(1,'BOS +3.5',2.3),
        _mk(2,'BOS +3.5',3.1),
    ]
    cfg = {'risk': {'max_corr': 0.7, 'corr_min_series': 3}}
    new_bet = _mk(3,'LAL -3.5',4.0)
    blocked, meta = should_block_by_correlation(new_bet, open_positions, cfg)
    assert blocked is True
    assert meta['reason'] == 'high_correlation'
    assert meta['group'] == 'nba::spread'
    assert meta['threshold'] == 0.7
    assert meta['offenders']

def test_correlation_allows_when_series_insufficient():
    open_positions = [_mk(0,'GSW -2.5',1.0)]
    cfg = {'risk': {'max_corr': 0.7, 'corr_min_series': 5}}
    new_bet = _mk(1,'GSW -2.5',1.0)
    blocked, meta = should_block_by_correlation(new_bet, open_positions, cfg)
    assert blocked is False
    assert meta['reason'] == 'insufficient_series'

def test_correlation_allows_when_low_corr():
    open_positions = [
        _mk(0,'NYK -2.0',1.0),
        _mk(1,'NYK -2.0',0.0),
        _mk(2,'NYK -2.0',1.0),
        _mk(0,'MIA +2.0',0.0),
        _mk(1,'MIA +2.0',1.0),
        _mk(2,'MIA +2.0',0.0),
    ]
    cfg = {'risk': {'max_corr': 0.5, 'corr_min_series': 3}}
    new_bet = _mk(3,'NYK -2.0',1.0)
    blocked, meta = should_block_by_correlation(new_bet, open_positions, cfg)
    assert blocked is False
    assert meta['reason'] == 'ok'
