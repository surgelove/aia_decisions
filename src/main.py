
import argparse
import json
import uuid
import requests
import aia_utilities as au

REDIS_HOST = "localhost"
REDIS_PORT = 6379
PREFIX_INPUT = "algos"
PREFIX_OUTPUT = "decisions"

def notify(message):
    endpoint = "aia"
    headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
            }
    requests.post(f'http://ntfy.sh/{endpoint}', headers=headers, data=message, timeout=2)
    # print(f"NOTIFY: {message}")

def main():
    print("Starting listener...")
    parser = argparse.ArgumentParser(
        description="Listen to Redis price stream or per-key price messages and process with TimeBasedStreamingMA."
    )
    parser.add_argument('--instrument', '--i', type=str, default=None, help="Instrument to listen to (e.g. USD_CAD)")
    parser.add_argument("--db", type=int, default=0, help="Redis DB number")
    parser.add_argument("--ttl", type=int, default=120, help="TTL in seconds for signals keys (optional)")
    args = parser.parse_args()

    instrument = args.instrument
    ttl = args.ttl


    r = au.RedisUtilities(host=REDIS_HOST, port=REDIS_PORT, db=args.db)
    prefix_input = f"{PREFIX_INPUT}"
    prefix_output = f"{PREFIX_OUTPUT}"

    r.delete('decisions')

    seen_keys = set()
    # in-memory store of fake positions keyed by generated position id
    positions = {}
    takes = []
    file = []
    id = 0


    entries = r.read_all(prefix_input)
    for input_dict in entries:
        # for datum in entry:
        #     print(datum)
        if 'timestamp' in input_dict and 'instrument' in input_dict:
            # Create a unique identifier from timestamp + instrument
            seen_keys.add(f"{input_dict['timestamp']}_{input_dict['instrument']}")
        
        if 'base_signal' in input_dict and 'peak_signal' in input_dict:
            # simulate entering a fake position when a base_signal appears
            if input_dict['base_signal'] is not None:
                # create a human-readable message
                message = f"{input_dict['timestamp']}\n{input_dict['instrument']}: {input_dict['price']}\nBase: {input_dict['base_signal']}, Peak: {input_dict['peak_signal']}\nDecision Up: {input_dict.get('decision_up', '')}, Decision Down: {input_dict.get('decision_dn', '')}\n{input_dict.get('message', '')}"

    print("waiting for new keys... (Ctrl-C to exit)")
    for input_dict in r.read_each(prefix_input):
        if 'base_signal' in input_dict and 'peak_signal' in input_dict:
            if f"{input_dict['timestamp']}_{input_dict['instrument']}" not in seen_keys:
                seen_keys.add(f"{input_dict['timestamp']}_{input_dict['instrument']}")
            else:
                continue # already seen this key, skip it
            # print(input_dict)
            # when new input arrives, if there's a base_signal then fake-enter a position
            # if input_dict.get('base_signal') is not None:
        # Kepp only fields timestamp, insturment, price and put into decision_data
        pip = pipize(input_dict['price'])
        distance = 2*pip
        decision_data = {
            'id': 0,
            'timestamp': input_dict['timestamp'],
            'instrument': input_dict['instrument'],
            'price': input_dict['price'],
            'base_cross_price': input_dict['base_cross_price']
            }
        
        if 'base_signal' in input_dict:
            if input_dict['base_signal'] is not None:
                id += 1
                if input_dict['base_direction'] > 0:
                    order = input_dict['price'] + distance
                elif input_dict['base_direction'] < 0:
                    order = input_dict['price'] - distance
                takes.append({
                    'id': id,
                    'timestamp': input_dict['timestamp'],
                    'instrument': input_dict['instrument'],
                    'direction': input_dict['base_direction'],
                    'order': order,
                    'take': None
                })
                print('new take')

        
        for take in takes:
            try:
                take['timestamp'] = input_dict['timestamp']
                if take['direction'] > 0 and input_dict['price'] >= take['order']:
                    take['take'] = input_dict['price']
                    take['order'] = None
                elif take['direction'] < 0 and input_dict['price'] <= take['order']:
                    take['take'] = input_dict['price']
                    take['order'] = None
                # take['price'] = input_dict['price']
                file.append(take.copy())
            except Exception as e:
                ...
        
            # print(take)
            # r.write('decisions', take, maxlen=100000)

        # r.write('decisions', decision_data, maxlen=100000)
        file.append(decision_data.copy())

        #write file to disk
        # print('writing to disk...')
        with open('decisions.json', 'w') as f:
            json.dump(file, f, indent=4)

def pipize(price):
    return price / 100_000


if __name__ == "__main__":

    main()
