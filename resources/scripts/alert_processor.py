import pickle
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Millipede Scanner')
    parser.add_argument('-e', '--event', help='Event file to process')
    args = parser.parse_args()

    with open(args.event, 'rb') as event_file:
        event = pickle.load(event_file)

    print(event)
