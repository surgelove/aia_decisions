
import argparse
import json
import uuid
import requests
import aia_utilities as au

REDIS_HOST = "localhost"
REDIS_PORT = 6379
PREFIX_INPUT = "algos"
PREFIX_OUTPUT = "decisions"
DEBUG = True


class DecisionProcessor:
    """Processes trading signals and manages decision state."""
    
    def __init__(self):
        self.seen_keys = set()
        self.prices = []
        self.file = []
        self.takes = []
        self.id = 0
    
    def notify(self, message):
        """Send notification via ntfy.sh"""
        endpoint = "aia"
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        requests.post(f'http://ntfy.sh/{endpoint}', headers=headers, data=message, timeout=2)
        # print(f"NOTIFY: {message}")
    
    def pipize(self, price):
        """Convert price to pip value"""
        return price / 100_000
    
    def process(self, input_dict):
        """Process a single input dictionary and generate trading decisions"""
        if DEBUG:
            print(input_dict['instrument'], input_dict['timestamp'], 
                  input_dict['price'], input_dict.get('base_signal'), 
                  input_dict.get('peak_signal'))

        # Make sure we only process each timestamp + instrument once
        key = f"{input_dict['timestamp']}_{input_dict['instrument']}"
        if key in self.seen_keys:
            return  # Already seen this key, skip it
        self.seen_keys.add(key)

        # Put data in variables
        timestamp = input_dict['timestamp']
        instrument = input_dict['instrument']
        price = input_dict['price']
        base_signal = input_dict.get('base_signal')
        peak_signal = input_dict.get('peak_signal')
        
        if base_signal:
            print(f"Base signal detected: {base_signal} at {timestamp} for {instrument} at price {price}")

        # Calculate minimum distance
        pip = self.pipize(input_dict['price'])
        distance = 2 * pip

        # Default price, added to prices dictionary
        price_data = {
            'id': 0,
            'timestamp': input_dict['timestamp'],
            'instrument': input_dict['instrument'],
            'price': input_dict['price'],
        }
        self.prices.append(price_data)
        
        # If adjustments, do it here
        
        # For each take in discrete takes
        for take in self.takes:
            try:
                # Skip takes that have already been filled
                if take['order'] is None:
                    continue
                    
                take['timestamp'] = input_dict['timestamp']
                if take['direction'] > 0 and input_dict['price'] >= take['order']:
                    take['take'] = input_dict['price']
                    take['order'] = None
                elif take['direction'] < 0 and input_dict['price'] <= take['order']:
                    take['take'] = input_dict['price']
                    take['order'] = None
                self.file.append(take.copy())
            except Exception as e:        
                print(f"Error processing take: {e}")

        # If signal to take, create a new take and append to takes
        if 'base_signal' in input_dict:
            if input_dict['base_signal'] is not None:
                self.id += 1
                if input_dict['base_direction'] > 0:
                    order = input_dict['price'] + distance
                elif input_dict['base_direction'] < 0:
                    order = input_dict['price'] - distance
                self.takes.append({
                    'id': self.id,
                    'timestamp': input_dict['timestamp'],
                    'instrument': input_dict['instrument'],
                    'direction': input_dict['base_direction'],
                    'order': order,
                    'take': None
                })
                print('new take')

        # Write file to disk
        with open('decisions.json', 'w') as f:
            json.dump(self.file, f, indent=4)

def main():
    print("Starting listener...")

    # Create processor instance
    processor = DecisionProcessor()

    r = au.RedisUtilities(host=REDIS_HOST, port=REDIS_PORT, db=0)
    prefix_input = f"{PREFIX_INPUT}"
    prefix_output = f"{PREFIX_OUTPUT}"

    r.delete('decisions')

    entries = r.read_all(prefix_input)

    for input_dict in entries:
        processor.process(input_dict)

    print("waiting for new keys... (Ctrl-C to exit)")
    
    for input_dict in r.read_each(prefix_input):
        processor.process(input_dict)


if __name__ == "__main__":

    main()
