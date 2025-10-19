
import argparse
import json
import uuid
import requests
import aia_utilities as au
from datetime import datetime, timedelta

REDIS_HOST = "localhost"
REDIS_PORT = 6379
PREFIX_INPUT = "algos"
PREFIX_OUTPUT = "decisions"
DEBUG = False


class DecisionProcessor:
    """Processes trading signals and manages decision state."""
    
    def __init__(self):
        self.seen_keys = set()
        self.prices = []
        self.file = []
        self.takes = []
        self.id = 0
        self.last_price_timestamp = None
        self.append_price = 0
    
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
        base_signal = input_dict.get('base_signal')         # 1, -1, or None, happens on signal once
        base_direction = input_dict.get('base_direction')   # 1 or -1 or None, continues until opposite signal
        peak_signal = input_dict.get('peak_signal')         # 1, -1, or None, happens on signal once
        peak_direction = input_dict.get('peak_direction')   # 1 or -1 or None, continues until opposite signal

        

        # Calculate minimum distance
        pip = self.pipize(input_dict['price'])
        distance = 2 * pip

        # Default price, added to prices dictionary
        price_data = {
            'id': 'all',
            'timestamp': timestamp,
            'instrument': instrument,
            'price': price,
        }
        self.prices.append(price_data)
        
        # If adjustments, do it here
        
        # For each take in discrete takes
        for take in self.takes:
            # try:
            if take['instrument'] == instrument:
                take['timestamp'] = timestamp
                if take['order']:
                    if take['direction'] > 0 and price >= take['order']:
                        take['take'] = price
                        take['order'] = None
                        self.file.append(take.copy())
                        self.append_price = 2
                    elif take['direction'] < 0 and price <= take['order']:
                        take['take'] = price
                        take['order'] = None
                        self.file.append(take.copy())
                        self.append_price = 2

                # self.file.append(take.copy())
                # except Exception as e:        
                    # print(f"Error processing take: {e}")

        if base_signal:
            print(f"Base signal detected: {base_signal} at {timestamp} for {instrument} at price {price}")

            self.id += 1
            if base_direction > 0:
                order = price + distance
            elif base_direction < 0:
                order = price - distance
            take = {
                'id': f"{instrument}_{self.id}",
                'timestamp': timestamp,
                'instrument': instrument,
                'direction': base_direction,
                'order': order,
                'take': None
            }
            print(take)
            self.takes.append(take.copy())
            self.file.append(take.copy())
            self.append_price = 2

        # Add price data to self.file only if timestamp from last price timestamp is >= 1 minute
        if self.append_price == 2:
            self.append_price = 0
            # append previous price data
            if len(self.prices) > 0:
                self.file.append(self.prices[-1])
            
            self.file.append(price_data)
            print(f'{timestamp} take hit, appending price data')
        else:
            if self.last_price_timestamp is not None:
                fmt = "%Y-%m-%d %H:%M:%S.%f"
                last_time = datetime.strptime(self.last_price_timestamp, fmt)
                current_time = datetime.strptime(timestamp, fmt)
                if current_time - last_time >= timedelta(minutes=1):
                    self.file.append(price_data)
                    self.last_price_timestamp = timestamp
                    print(f'{timestamp} been a minute, appending price data')
                else:
                    print(f'{timestamp} not been a minute, not appending price data')
            else:
                self.file.append(price_data)
                self.last_price_timestamp = timestamp
                print(f'{timestamp} first price data, appending')

    
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
