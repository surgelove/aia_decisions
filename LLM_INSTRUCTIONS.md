This program receives a redis stream as input.
Every input is a dictionary called input_dict that looks like this:

```python
input_dict = {
    "timestamp": "2025-08-24 17:08:49.000000",
    "instrument": "USD_CAD",
    "price": 1.38268,
    "base_signal": None,
    "base_ema": 1.38279,
    "base_tema": 1.38264,
    "base_cross_price": None,
    "base_direction": -1,
    "base_mamplitude": 0.02025,
    "base_pamplitude": 0.04702,
    "base_min_price": 1.38293,
    "base_max_price": 1.38319,
    "peak_signal": None,
    "peak_cross_price": None,
    "peak_direction": -1,
    "peak_pamplitude": 0.0014464453605359821,
    "peak_tamplitude": 0,
    "peak_follower_up": None,
    "peak_follower_dn": 1.3828799999999999,
    "aspr_min_price": 1.38242,
    "aspr_max_price": 1.38316,
    "temp_value_1": None,
    "temp_value_2": 0.03544,
    "temp_value_3": 0.00072,
    "temp_value_4": None,
    "pl": None,
    "base_signal_up": None,
    "base_signal_dn": None,
    "base_mamplitude_threshold": 0.02,
    "base_pamplitude_threshold": 0.03,
    "peak_signal_up": None,
    "peak_signal_dn": None,
    "peak_pamplitude_threshold": 0.04,
    "peak_tamplitude_threshold": 0.02,
    "xtpk_signal_up": None,
    "xtpk_signal_dn": None,
    "decision": None,
    "decision_algo": None,
    "message": None,
    "decision_up": None,
    "decision_dn": None,
}
```

Don't bother with the redis handling, just help the human starting after receiving the input_dict, which happens at line 64 of main:

```python
print(input_dict)
```

Do not bother with RedisUtilities
