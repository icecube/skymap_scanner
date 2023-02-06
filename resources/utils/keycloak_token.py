import argparse

from rest_tools.client import ClientCredentialsAuth


def get_token(address, client_id, client_secret):
    cc = ClientCredentialsAuth('', token_url=address, client_id=client_id, client_secret=client_secret)
    return cc.make_access_token()

def main():
    parser = argparse.ArgumentParser(description='Get an OAuth2 token via client credentials')
    parser.add_argument('--address', default='https://keycloak.icecube.wisc.edu/auth/realms/IceCube', help='OAuth2 server address')
    parser.add_argument('client_id', help='client id')
    parser.add_argument('client_secret', help='client secret')

    args = parser.parse_args()
    kwargs = vars(args)
    print('access token:', get_token(**kwargs))

if __name__ == '__main__':
    main()
